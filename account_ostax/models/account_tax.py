# SPDX-License-Identifier: LGPL-3.0-or-later
"""account.tax override — the canonical OpenSalesTax integration point.

The override engages the engine via the SDK for US partners with a
valid 5-digit ZIP, replacing the catalog rate with a per-jurisdiction
breakdown. Non-US partners, partners without a ZIP, or unconfigured
companies fall through to ``super().compute_all(...)``.

The ``**kw`` pattern absorbs signature drift across Odoo majors:

* 16.0 / 17.0: ``fixed_multiplicator``
* 18.0:        ``rounding_method``

Per the project research, no published ``account.tax.provider``
abstraction exists in either Community or Enterprise. We override
``compute_all`` directly, the same way Avalara's Enterprise module
does.
"""

from __future__ import annotations

import logging
import time
from collections import namedtuple
from datetime import timedelta
from decimal import Decimal
from typing import Any

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

# Lightweight jurisdiction record reconstructed from cached tuples — has the
# same shape as the SDK's pydantic JurisdictionBreakdown for the fields the
# helpers (``_ostax_ensure_synthetic_taxes``) actually read.
_CachedJurisdiction = namedtuple("_CachedJurisdiction", ["name", "type", "rate_pct", "tax"])

_logger = logging.getLogger(__name__)


# Jurisdiction-type → sequence ordering used for synthetic tax records and
# for the order they appear in the compute_all result.
_JURISDICTION_SEQUENCE = {
    "state": 10,
    "county": 20,
    "city": 30,
    "district": 40,
}


class AccountTax(models.Model):
    _inherit = "account.tax"

    ostax_synthetic = fields.Boolean(
        string="OST synthetic",
        default=False,
        copy=False,
        help=(
            "Internal marker. Set on tax records that the OpenSalesTax "
            "module materializes per jurisdiction on first calc. Don't "
            "edit these directly — they're recreated as needed."
        ),
    )
    ostax_jurisdiction_name = fields.Char(
        string="OST jurisdiction name",
        copy=False,
        help="The name of the taxing authority (e.g. 'Hennepin County').",
    )
    ostax_jurisdiction_type = fields.Selection(
        selection=[
            ("state", "State"),
            ("county", "County"),
            ("city", "City"),
            ("district", "District"),
        ],
        string="OST jurisdiction type",
        copy=False,
    )

    # ------------------------------------------------------------------
    # Odoo 18 batch tax engine override (the production-grade hook)
    # ------------------------------------------------------------------

    @api.model
    def _add_tax_details_in_base_lines(self, base_lines, company):
        """Inject OST-computed tax amounts into base_lines BEFORE the standard
        engine runs, then super() applies them via ``manual_tax_amounts``.

        This is the canonical Odoo 18 hook for replacing tax computation —
        called from ``account.move._get_rounded_base_and_tax_lines()`` and
        therefore covers invoices, credit notes, sale orders, POS orders,
        and anywhere else that uses the new batch tax engine.

        For each base_line that should engage OST (US partner with a valid
        5-digit ZIP, USD currency, OST-enabled company, non-exempt
        partner): call the engine, materialize per-jurisdiction synthetic
        taxes, swap base_line['tax_ids'] for the synthetic recordset, and
        populate base_line['manual_tax_amounts'] with the engine's
        per-jurisdiction amounts. ``super()`` then produces tax_details
        using those amounts directly (the official Odoo bypass for
        external tax computation).

        Lines that don't engage (non-US, non-USD, exempt, OST disabled)
        pass through unchanged for super() to handle with catalog rates.
        """
        if company and company.ostax_enabled and company.ostax_api_url:
            for base_line in base_lines:
                try:
                    self._ostax_inject_into_base_line(base_line, company)
                except UserError:
                    raise
                except Exception as e:  # noqa: BLE001
                    if company.ostax_fail_soft:
                        _logger.warning(
                            "OST batch-engine fail-soft on base line: %s", e
                        )
                    else:
                        raise UserError(
                            _("OpenSalesTax error during tax computation: %s") % e
                        ) from e
        # Cross-version safe: Odoo 16/17 don't define this method.
        parent = getattr(super(), "_add_tax_details_in_base_lines", None)
        if parent is None:
            return None
        return parent(base_lines, company)

    def _ostax_inject_into_base_line(self, base_line: dict, company: Any) -> None:
        """Mutate one base_line so the standard tax engine produces OST values."""
        from opensalestax import (
            OpenSalesTaxAPIError,
            OpenSalesTaxNetworkError,
            OpenSalesTaxValidationError,
        )

        partner = base_line.get("partner_id")
        currency = base_line.get("currency_id")

        # Multi-currency safety: engine is USD-only (engine constitution §5).
        if currency and getattr(currency, "name", None) and currency.name != "USD":
            return  # leave for super() to use catalog rate

        if not self._ostax_should_engage(company, partner):
            return

        # Exempt partners → zero tax, no engine call. Strip catalog taxes too.
        if self._ostax_partner_is_exempt(partner):
            base_line["tax_ids"] = self.env["account.tax"]
            base_line["manual_tax_amounts"] = {}
            return

        price_unit = float(base_line.get("price_unit") or 0.0)
        discount = float(base_line.get("discount") or 0.0)
        quantity = float(base_line.get("quantity") or 0.0)
        price_after_discount = price_unit * (1 - (discount / 100.0))
        line_total = Decimal(str(price_after_discount)) * Decimal(str(quantity))
        if line_total <= 0:
            return  # nothing to compute

        zip_value = (partner.zip or "").strip()
        zip5 = zip_value[:5]
        zip4 = zip_value[5:].lstrip("-").strip() if len(zip_value) > 5 else None
        product = base_line.get("product_id")

        started = time.monotonic()
        try:
            jurisdictions = self._ostax_engine_calculate_cached(
                company.id,
                zip5,
                zip4 or "",
                str(line_total),
                self._ostax_category_for(product),
            )
        except (
            OpenSalesTaxNetworkError,
            OpenSalesTaxValidationError,
        ) as e:
            if company.ostax_fail_soft:
                _logger.warning("OST batch-engine fail-soft: %s", e)
                return
            raise UserError(_("OpenSalesTax error: %s") % e) from e
        except OpenSalesTaxAPIError as e:
            if e.status_code >= 500 and company.ostax_fail_soft:
                _logger.warning("OST 5xx fail-soft: %s", e)
                return
            raise UserError(_("OpenSalesTax error: %s") % e) from e
        rtt_ms = int((time.monotonic() - started) * 1000)

        if not jurisdictions:
            return

        # Reconstruct lightweight jurisdiction records from the cached tuples
        # so the existing helpers (_ostax_ensure_synthetic_taxes etc.) work
        # unchanged. Each tuple is (name, type, rate_pct_str, tax_str_or_empty).
        engine_juris = [
            _CachedJurisdiction(name=name, type=jtype, rate_pct=Decimal(rate_str),
                                tax=Decimal(tax_str) if tax_str else None)
            for name, jtype, rate_str, tax_str in jurisdictions
        ]
        synthetic_by_key = self._ostax_ensure_synthetic_taxes(company, engine_juris)
        synthetic_ids: list[int] = []
        manual_tax_amounts: dict[str, dict[str, float]] = {}
        for j in engine_juris:
            tax_rec = synthetic_by_key[(j.name, j.type)]
            synthetic_ids.append(tax_rec.id)
            j_tax = float(j.tax or Decimal("0"))
            manual_tax_amounts[str(tax_rec.id)] = {
                "tax_amount_currency": j_tax,
                "base_amount_currency": float(line_total),
            }

        base_line["tax_ids"] = self.env["account.tax"].browse(synthetic_ids)
        base_line["manual_tax_amounts"] = manual_tax_amounts

        # Persist the synthetic tax_ids on the source line so the line UI
        # shows OST jurisdiction tags (e.g. "OST · Minnesota (state)") on
        # the posted invoice instead of the catalog placeholder. Only on
        # draft moves — Odoo's standard model rejects writes to posted
        # move lines. Idempotent: only writes if the persisted set
        # differs from the synthetic set, so the recompute that this
        # write triggers won't loop (next iteration's set already
        # matches).
        record = base_line.get("record")
        if record is not None and getattr(record, "_name", None) == "account.move.line":
            move = record.move_id
            if move and move.state == "draft":
                try:
                    persisted = sorted(record.tax_ids.ids)
                    target = sorted(synthetic_ids)
                    if persisted != target:
                        record.with_context(
                            check_move_validity=False,
                            skip_invoice_sync=True,
                            tracking_disable=True,
                        ).sudo().tax_ids = [(6, 0, target)]
                except Exception as e:  # noqa: BLE001
                    _logger.warning(
                        "OST: line tax_ids persistence skipped (%s); the "
                        "totals area still shows the correct breakdown.",
                        e,
                    )

        if company.ostax_debug_log_enabled:
            try:
                Log = self.env["ostax.calc.log"].sudo()
                Log.create(
                    {
                        "company_id": company.id,
                        "kind": "engine_call",
                        "dest_zip": zip5,
                        "total_amount": float(line_total),
                        "engine_version": "",
                        "response_ms": rtt_ms,
                    }
                )
                stale = Log.search(
                    [("company_id", "=", company.id)],
                    order="create_date desc",
                    offset=50,
                )
                if stale:
                    stale.unlink()
            except Exception as e:  # noqa: BLE001
                _logger.warning("OST debug-log write failed: %s", e)

    # ------------------------------------------------------------------
    # Public override (legacy compute_all path; covers 16/17 + edge cases)
    # ------------------------------------------------------------------

    def compute_all(
        self,
        price_unit: float,
        currency: Any = None,
        quantity: float = 1.0,
        product: Any = None,
        partner: Any = None,
        is_refund: bool = False,
        **kw: Any,
    ) -> dict[str, Any]:
        """Override: engage OST for US partners, fall through otherwise.

        ``**kw`` absorbs the version-specific kwargs Odoo passes:
        ``handle_price_include``, ``include_caba_tags``,
        ``fixed_multiplicator`` (16/17), ``rounding_method`` (18+).
        """
        company = self._ostax_company()
        if not self._ostax_should_engage(company, partner):
            return super().compute_all(
                price_unit,
                currency=currency,
                quantity=quantity,
                product=product,
                partner=partner,
                is_refund=is_refund,
                **kw,
            )

        # Exemption short-circuit: skip the engine entirely; the partner is
        # tax-free at every jurisdiction. The certificate stays on the
        # partner record for audit (merchant-tracked).
        if self._ostax_partner_is_exempt(partner):
            sign = -1 if is_refund else 1
            base = float(price_unit) * float(quantity) * sign
            return {
                "base_tags": [],
                "taxes": [],
                "total_excluded": base,
                "total_included": base,
                "total_void": 0.0,
            }
        from opensalestax import (
            NonUSDError,
            OpenSalesTaxAPIError,
            OpenSalesTaxError,
            OpenSalesTaxNetworkError,
            OpenSalesTaxValidationError,
        )

        try:
            return self._ostax_compute_all(
                company=company,
                price_unit=price_unit,
                currency=currency,
                quantity=quantity,
                product=product,
                partner=partner,
                is_refund=is_refund,
                **kw,
            )
        except (
            OpenSalesTaxNetworkError,
            OpenSalesTaxValidationError,
            NonUSDError,
        ) as e:
            _logger.warning("OST fail-soft (network/validation/non-USD): %s", e)
            if company.ostax_fail_soft:
                return super().compute_all(
                    price_unit,
                    currency=currency,
                    quantity=quantity,
                    product=product,
                    partner=partner,
                    is_refund=is_refund,
                    **kw,
                )
            raise UserError(_("Sales-tax service unavailable: %s") % e) from e
        except OpenSalesTaxAPIError as e:
            if e.status_code >= 500 and company.ostax_fail_soft:
                _logger.warning("OST 5xx fail-soft: %s", e)
                return super().compute_all(
                    price_unit,
                    currency=currency,
                    quantity=quantity,
                    product=product,
                    partner=partner,
                    is_refund=is_refund,
                    **kw,
                )
            _logger.error("OST API error (status=%s): %s", e.status_code, e)
            raise UserError(_("OpenSalesTax error: %s") % e) from e
        except OpenSalesTaxError as e:
            # Catch-all for any future SDK error subclass. Fail-soft if
            # configured; otherwise surface as UserError.
            _logger.warning("OST unexpected SDK error: %s", e)
            if company.ostax_fail_soft:
                return super().compute_all(
                    price_unit,
                    currency=currency,
                    quantity=quantity,
                    product=product,
                    partner=partner,
                    is_refund=is_refund,
                    **kw,
                )
            raise UserError(_("OpenSalesTax error: %s") % e) from e

    # ------------------------------------------------------------------
    # Engagement decision
    # ------------------------------------------------------------------

    def _ostax_company(self) -> Any:
        """Resolve the company for this tax recordset.

        Lazy access: prefer ``self.company_id`` (the line's company),
        fall back to ``self.env.company`` for empty recordsets.
        """
        if self and self[:1].company_id:
            return self[:1].company_id
        return self.env.company

    def _ostax_should_engage(self, company: Any, partner: Any) -> bool:
        """Return True iff every gate passes (excluding exemption — that's a
        separate check, since exempt partners still go through OST logic but
        short-circuit to zero tax).

        Gates:

        * ``ostax_enabled`` is on for the company
        * ``ostax_api_url`` is configured
        * ``partner`` is non-empty
        * ``partner.country_id`` is the US
        * ``partner.zip`` is at least 5 digits
        """
        if not (company and company.ostax_enabled and company.ostax_api_url):
            return False
        if not partner:
            return False
        partner = partner[:1] if hasattr(partner, "__iter__") else partner
        us = self.env.ref("base.us", raise_if_not_found=False)
        if not us or partner.country_id != us:
            return False
        zip_value = (partner.zip or "").strip()
        if len(zip_value) < 5 or not zip_value[:5].isdigit():
            return False
        return True

    @staticmethod
    def _ostax_partner_is_exempt(partner: Any) -> bool:
        """True if the partner carries a valid (unexpired) OST exemption certificate.

        v0.1 short-circuits exempt partners to zero tax without calling the
        engine — the engine API doesn't accept exemption fields in calc
        requests yet, and exempt partners are tax-free at every jurisdiction
        regardless. The certificate itself stays on the partner record for
        audit; the merchant is responsible for keeping it current.
        """
        if not partner:
            return False
        partner = partner[:1] if hasattr(partner, "__iter__") else partner
        cert = (getattr(partner, "ostax_exemption_certificate", "") or "").strip()
        if not cert:
            return False
        expiry = getattr(partner, "ostax_exemption_expiry", False)
        if expiry:
            from odoo import fields as odoo_fields  # lazy

            today = odoo_fields.Date.context_today(partner)
            if expiry < today:
                return False
        return True

    # ------------------------------------------------------------------
    # OST core
    # ------------------------------------------------------------------

    def _ostax_compute_all(
        self,
        company: Any,
        price_unit: float,
        currency: Any,
        quantity: float,
        product: Any,
        partner: Any,
        is_refund: bool,
        **_kw: Any,
    ) -> dict[str, Any]:
        """Build the engine payload, call the SDK, mash the response."""
        from opensalestax import Address, LineItem

        zip_value = (partner.zip or "").strip()
        zip5 = zip_value[:5]
        zip4 = zip_value[5:].lstrip("-").strip() if len(zip_value) > 5 else None
        address = Address(zip5=zip5, zip4=zip4 or None)

        amount = Decimal(str(price_unit)) * Decimal(str(quantity))
        category = self._ostax_category_for(product)
        line_items = [LineItem(amount=amount, category=category)]

        started = time.monotonic()
        with company._ostax_client() as client:
            result = client.calculate(address=address, line_items=line_items)
        rtt_ms = int((time.monotonic() - started) * 1000)

        # Phase 9 — opt-in debug log of the call.
        if company.ostax_debug_log_enabled:
            try:
                self.env["ostax.calc.log"].sudo().create(
                    {
                        "company_id": company.id,
                        "kind": "engine_call",
                        "dest_zip": zip5,
                        "total_amount": float(amount),
                        "engine_version": "",
                        "response_ms": rtt_ms,
                    }
                )
                # Trim to last 50 entries per company (ring-buffer-ish).
                Log = self.env["ostax.calc.log"].sudo()
                recent = Log.search(
                    [("company_id", "=", company.id)],
                    order="create_date desc",
                    offset=50,
                )
                if recent:
                    recent.unlink()
            except Exception as e:  # noqa: BLE001
                _logger.warning("OST debug-log write failed: %s", e)

        if not result.lines:
            # Should never happen for a well-formed request, but if it does,
            # treat as zero-tax (engine returned empty breakdown).
            return self._ostax_empty_result(price_unit, quantity)

        line = result.lines[0]
        sign = -1 if is_refund else 1

        synthetic_taxes_by_jurisdiction = self._ostax_ensure_synthetic_taxes(
            company, line.jurisdictions
        )

        # Build the compute_all-style return dict.
        base = float(amount) * sign
        total_tax = float(line.tax) * sign
        taxes_list: list[dict[str, Any]] = []
        for j in line.jurisdictions:
            tax_rec = synthetic_taxes_by_jurisdiction[(j.name, j.type)]
            jurisdiction_tax = float(j.tax or Decimal("0")) * sign
            taxes_list.append(
                self._ostax_tax_dict(
                    tax_rec=tax_rec,
                    base=base,
                    amount=jurisdiction_tax,
                    sequence=_JURISDICTION_SEQUENCE.get(j.type, 99),
                )
            )

        return {
            "base_tags": [],
            "taxes": taxes_list,
            "total_excluded": base,
            "total_included": base + total_tax,
            "total_void": 0.0,
        }

    @staticmethod
    def _ostax_category_for(product: Any) -> str:
        """Map an Odoo product to an OST tax category.

        Lookup precedence:

        1. ``product.product_tmpl_id.ostax_category`` — per-product override
           (added v0.1.13).
        2. ``product.product_tmpl_id.categ_id.ostax_category`` — internal
           category default; walks up ``parent_id`` until a value is found
           (added v0.1.14).
        3. ``"general"`` — final fallback.

        Defensive against:
        - ``product`` is None / falsy → returns "general"
        - ``product`` is a ``product.template`` (not a variant) → use directly
        - DBs without the field → ``getattr`` returns None, falls through
        """
        if not product:
            return "general"
        template = getattr(product, "product_tmpl_id", None) or product

        # 1) Per-product override
        explicit = getattr(template, "ostax_category", None)
        if explicit:
            return explicit

        # 2) Internal-category default, walking up the parent chain
        category = getattr(template, "categ_id", None)
        seen: set[int] = set()
        while category and getattr(category, "id", 0) not in seen:
            seen.add(category.id)
            cat_value = getattr(category, "ostax_category", None)
            if cat_value:
                return cat_value
            category = getattr(category, "parent_id", None) or None

        # 3) Final fallback
        return "general"

    def _ostax_empty_result(self, price_unit: float, quantity: float) -> dict[str, Any]:
        base = price_unit * quantity
        return {
            "base_tags": [],
            "taxes": [],
            "total_excluded": base,
            "total_included": base,
            "total_void": 0.0,
        }

    @staticmethod
    def _ostax_tax_dict(
        tax_rec: Any, base: float, amount: float, sequence: int
    ) -> dict[str, Any]:
        """Produce one entry of the ``taxes`` list in the compute_all return."""
        return {
            "id": tax_rec.id,
            "name": tax_rec.name,
            "amount": amount,
            "base": base,
            "sequence": sequence,
            "account_id": False,
            "refund_account_id": False,
            "analytic": False,
            "price_include": False,
            "tax_repartition_line_id": False,
            "group": tax_rec.tax_group_id.id if tax_rec.tax_group_id else False,
            "tag_ids": [],
        }

    # ------------------------------------------------------------------
    # Synthetic-tax materialization
    # ------------------------------------------------------------------

    def _ostax_ensure_synthetic_taxes(
        self, company: Any, jurisdictions: list[Any]
    ) -> dict[tuple[str, str], Any]:
        """Return a dict mapping (name, type) → account.tax record.

        Materializes any missing synthetic taxes. Idempotent — repeat
        calls return the same records.

        Each synthetic tax is assigned to a per-jurisdiction-type
        ``account.tax.group`` ("OpenSalesTax — State", "— County",
        "— City", "— District") so the totals area on invoices /
        sale orders shows meaningful labels instead of falling back
        to the chart-of-accounts default group ("Tax 15%" on
        ``l10n_generic_coa``, etc.).
        """
        Tax = self.env["account.tax"].sudo().with_context(active_test=False)
        groups_by_type = self._ostax_ensure_tax_groups(company)
        us = self.env.ref("base.us", raise_if_not_found=False)
        existing = Tax.search(
            [
                ("company_id", "=", company.id),
                ("ostax_synthetic", "=", True),
            ]
        )
        by_key: dict[tuple[str, str], Any] = {
            (t.ostax_jurisdiction_name, t.ostax_jurisdiction_type): t for t in existing
        }
        # Backfill: if an existing synthetic was created before per-type
        # groups existed (pre-v0.1.3), assign the group now. Also
        # reactivate any synthetic that was archived by the unused-prune
        # cron — the merchant is now selling to that jurisdiction again.
        for t in existing:
            target_group = groups_by_type.get(t.ostax_jurisdiction_type)
            if target_group and t.tax_group_id != target_group:
                t.tax_group_id = target_group.id
            if not t.active:
                t.active = True
        for j in jurisdictions:
            key = (j.name, j.type)
            if key in by_key:
                continue
            vals = {
                "name": f"OST · {j.name} ({j.type})",
                "amount": 0.0,  # OST overrides the amount per-calc
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": company.id,
                "active": True,
                "ostax_synthetic": True,
                "ostax_jurisdiction_name": j.name,
                "ostax_jurisdiction_type": j.type,
                "sequence": _JURISDICTION_SEQUENCE.get(j.type, 99),
            }
            # Odoo 16+ has country_id on account.tax with a NOT NULL
            # constraint. Pin to US since the engine is US-only.
            if "country_id" in Tax._fields and us:
                vals["country_id"] = us.id
            target_group = groups_by_type.get(j.type)
            if target_group:
                vals["tax_group_id"] = target_group.id
            by_key[key] = Tax.create(vals)
        return by_key

    # ------------------------------------------------------------------
    # Cache layer (v0.1.11)
    # ------------------------------------------------------------------

    @api.model
    def _ostax_cache_bucket(self) -> int:
        """Returns the current 1-hour cache bucket as an integer.

        Cache keys include this so entries naturally expire as the
        bucket advances (sliding ~1h TTL). Per-worker memory; no
        cross-worker sharing on Odoo's standard `tools.ormcache`.
        """
        return int(time.time()) // 3600

    @tools.ormcache(
        "company_id",
        "zip5",
        "zip4",
        "amount_str",
        "category",
        "self._ostax_cache_bucket()",
    )
    def _ostax_engine_calculate_cached(
        self, company_id, zip5, zip4, amount_str, category,
    ):
        """Cache-wrapped engine ``/v1/calculate`` call.

        Note: signature has no type annotations because Odoo 16's
        ``tools.ormcache`` stringifies the function signature into a
        key-builder lambda without stripping annotations. With
        ``from __future__ import annotations`` in this module the
        annotations become strings (e.g. ``'int'``) which break the
        lambda's syntax. 17/18/19 are tolerant; 16 is not. Untyped
        signature works on all four.

        Returns a tuple of ``(name, type, rate_pct, tax)`` tuples — one
        per jurisdiction. Plain Python types so it pickles cleanly into
        ormcache. The decorator caches per
        ``(company, dest ZIP, amount, category, hourly bucket)``;
        subsequent calls within the same hour for the same line shape
        skip the engine entirely.

        Cache hit rate observed: ~10ms LAN RTT → effectively 0ms on
        repeat calls. Helpful for batch invoicing, e-commerce checkouts,
        recurring subscriptions, and any flow where the same product
        ships to the same destination repeatedly within an hour.
        """
        from opensalestax import Address, LineItem

        company = self.env["res.company"].browse(company_id)
        address = Address(zip5=zip5, zip4=zip4 or None)
        line_items = [LineItem(amount=Decimal(amount_str), category=category)]
        with company._ostax_client() as client:
            result = client.calculate(address=address, line_items=line_items)
        if not result.lines:
            return ()
        engine_line = result.lines[0]
        return tuple(
            (
                j.name,
                j.type,
                str(j.rate_pct),
                str(j.tax) if j.tax is not None else "",
            )
            for j in engine_line.jurisdictions
        )

    @api.model
    def _ostax_archive_unused_synthetics(self, days_unused: int = 90) -> int:
        """Archive synthetic OST taxes not referenced as a tax_line on any
        ``account.move.line`` in the last ``days_unused`` days.

        Triggered by the optional ``ir.cron`` job (disabled by default;
        enable under Settings → Technical → Scheduled Actions). Soft
        archive only — sets ``active=False``. Records remain referenced
        from historical journal entries; they're just hidden from the
        default tax dropdowns. The next OST calculation that hits the
        same jurisdiction will reactivate the record (see
        ``_ostax_ensure_synthetic_taxes``).

        Returns the count of records archived.
        """
        cutoff = fields.Date.today() - timedelta(days=days_unused)
        Tax = self.env["account.tax"].with_context(active_test=False)
        Line = self.env["account.move.line"]
        candidates = Tax.search([
            ("ostax_synthetic", "=", True),
            ("active", "=", True),
        ])
        archived_ids: list[int] = []
        for tax in candidates:
            recent = Line.search_count(
                [
                    ("tax_line_id", "=", tax.id),
                    ("date", ">=", cutoff),
                ],
                limit=1,
            )
            if not recent:
                archived_ids.append(tax.id)
        if archived_ids:
            Tax.browse(archived_ids).write({"active": False})
            _logger.info(
                "OST archived %s unused synthetic taxes (cutoff=%s)",
                len(archived_ids),
                cutoff,
            )
        return len(archived_ids)

    def _ostax_ensure_tax_groups(self, company: Any) -> dict[str, Any]:
        """Return a dict mapping jurisdiction type → ``account.tax.group``.

        Materializes the four per-type groups idempotently. Per-jurisdiction-type
        grouping makes the totals area on invoices show meaningful labels:

        * OpenSalesTax — State
        * OpenSalesTax — County
        * OpenSalesTax — City
        * OpenSalesTax — District

        instead of the chart-of-accounts default ("Tax 15%" or similar).
        """
        Group = self.env["account.tax.group"].sudo()
        us = self.env.ref("base.us", raise_if_not_found=False)
        # Cross-version field-existence guards. Odoo 16's
        # account.tax.group has no company_id (groups are global on 16);
        # 17+ added it. country_id was added at the same time. Always
        # check before filtering or writing.
        has_company = "company_id" in Group._fields
        has_country = "country_id" in Group._fields
        groups: dict[str, Any] = {}
        for jtype in ("state", "county", "city", "district"):
            label = f"OpenSalesTax — {jtype.capitalize()}"
            domain: list[Any] = [("name", "=", label)]
            if has_company:
                domain.append(("company_id", "=", company.id))
            existing = Group.search(domain, limit=1)
            if existing:
                groups[jtype] = existing
                continue
            vals: dict[str, Any] = {
                "name": label,
                "sequence": _JURISDICTION_SEQUENCE.get(jtype, 99),
            }
            if has_company:
                vals["company_id"] = company.id
            if has_country and us:
                vals["country_id"] = us.id
            groups[jtype] = Group.create(vals)
        return groups

