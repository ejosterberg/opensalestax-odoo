# SPDX-License-Identifier: LGPL-3.0-or-later
"""account.move OST breakdown — captured on _post() and surfaced on the form.

Phase 5 hooks ``account.move._post()`` to capture the per-jurisdiction
breakdown as JSON on the move at the moment of posting. The synthetic
per-jurisdiction tax lines (from Phase 4) remain the user-facing
representation; this JSON is **audit metadata** — engine version,
calc timestamp, raw breakdown — frozen at the time of posting.

A "Recompute OST breakdown" button is exposed for ad-hoc refresh on
draft moves.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    ostax_breakdown = fields.Text(
        string="OST jurisdiction breakdown",
        readonly=True,
        copy=False,
        help=(
            "JSON-serialized list of per-jurisdiction tax contributions "
            "captured at the time of posting. Stored on the move "
            "for audit and reconciliation."
        ),
    )
    ostax_engine_version = fields.Char(
        string="OST engine version",
        readonly=True,
        copy=False,
    )
    ostax_calculated_at = fields.Datetime(
        string="OST calculated at",
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Lifecycle hook — capture breakdown on post
    # ------------------------------------------------------------------

    def _post(self, soft: bool = True) -> Any:  # type: ignore[override]
        """Capture OST breakdown on each move that engages OST, then super()."""
        for move in self:
            try:
                if move._ostax_should_capture():
                    move._ostax_capture_breakdown()
            except Exception as e:
                # Capture failures must never block posting. The synthetic
                # per-jurisdiction tax lines (from Phase 4) are already on
                # the move — this is just metadata.
                _logger.warning(
                    "OST breakdown capture failed for %s: %s",
                    move.display_name,
                    e,
                )
        return super()._post(soft=soft)

    def action_ostax_recompute_breakdown(self) -> dict[str, Any]:
        """Manual button: recompute breakdown for this draft move."""
        for move in self:
            if not move._ostax_should_capture():
                raise UserError(
                    _(
                        "OpenSalesTax doesn't apply to this move "
                        "(disabled, non-US partner, or missing ZIP)."
                    )
                )
            move._ostax_capture_breakdown()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Breakdown recomputed"),
                "message": _("OpenSalesTax breakdown captured at %s.") % fields.Datetime.now(),
                "type": "success",
                "sticky": False,
            },
        }

    # ------------------------------------------------------------------
    # Engagement check + capture logic
    # ------------------------------------------------------------------

    def _ostax_should_capture(self) -> bool:
        self.ensure_one()
        company = self.company_id or self.env.company
        partner = self._ostax_capture_partner()
        return self.env["account.tax"]._ostax_should_engage(company, partner)

    def _ostax_capture_partner(self) -> Any:
        """Return the partner used as the destination for tax capture.

        For customer-facing moves (out_invoice / out_refund) — the
        invoice partner. For vendor moves (in_invoice / in_refund) —
        v0.1 doesn't support vendor-side use-tax (deferred to v0.2);
        return False so the engagement check fails.
        """
        self.ensure_one()
        if self.move_type in ("out_invoice", "out_refund"):
            return self.partner_shipping_id or self.partner_id
        return False

    def _ostax_capture_breakdown(self) -> None:
        """Build the engine payload from this move's lines, call OST, persist."""
        self.ensure_one()
        from opensalestax import Address, LineItem

        company = self.company_id or self.env.company
        partner = self._ostax_capture_partner()
        zip_value = (partner.zip or "").strip()
        zip5 = zip_value[:5]
        zip4 = zip_value[5:].lstrip("-").strip() if len(zip_value) > 5 else None
        address = Address(zip5=zip5, zip4=zip4 or None)

        items: list[LineItem] = []
        for line in self.invoice_line_ids:
            if line.display_type:
                continue  # skip section / note lines
            amount = Decimal(str(line.price_subtotal or 0))
            if amount <= 0:
                continue
            items.append(LineItem(amount=amount, category="general"))

        if not items:
            self.write(
                {
                    "ostax_breakdown": False,
                    "ostax_engine_version": False,
                    "ostax_calculated_at": False,
                }
            )
            return

        with company._ostax_client() as client:
            result = client.calculate(address=address, line_items=items)

        breakdown = self._ostax_serialize_result(result)
        self.write(
            {
                "ostax_breakdown": json.dumps(breakdown, sort_keys=True, default=str),
                "ostax_engine_version": breakdown.get("engine_version") or "",
                "ostax_calculated_at": fields.Datetime.now(),
            }
        )

    @staticmethod
    def _ostax_serialize_result(result: Any) -> dict[str, Any]:
        return {
            "subtotal": str(result.subtotal),
            "tax_total": str(result.tax_total),
            "engine_version": getattr(result, "engine_version", "")
            or getattr(result, "version", ""),
            "lines": [
                {
                    "amount": str(line.amount),
                    "category": line.category,
                    "tax": str(line.tax),
                    "rate_pct": str(line.rate_pct),
                    "note": getattr(line, "note", None),
                    "jurisdictions": [
                        {
                            "name": j.name,
                            "type": j.type,
                            "rate_pct": str(j.rate_pct),
                            "tax": str(j.tax) if j.tax is not None else None,
                        }
                        for j in line.jurisdictions
                    ],
                }
                for line in result.lines
            ],
        }
