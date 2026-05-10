# SPDX-License-Identifier: LGPL-3.0-or-later
"""Per-company OpenSalesTax settings + engine-client helper.

Settings live on res.company so multi-company Odoo deployments can
configure per-company engines (or disable OST per company without
disabling globally).

Phase 3 (this file) populates the engine-client helper and the
Test Connection action. Phase 9 wires the cache TTL into ormcache.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    ostax_enabled = fields.Boolean(
        string="OpenSalesTax enabled",
        default=False,
        help=(
            "When enabled, US tax calculations on sales orders, invoices, "
            "POS orders, vendor bills, and refunds are computed by the "
            "configured OpenSalesTax engine instead of the catalog's "
            "static rates."
        ),
    )
    ostax_api_url = fields.Char(
        string="OpenSalesTax engine URL",
        help="Base URL of your OpenSalesTax engine (e.g. http://10.0.0.5:8080).",
    )
    ostax_api_key = fields.Char(
        string="OpenSalesTax API key",
        help="Optional Bearer token forwarded to the engine.",
    )
    ostax_origin_address_id = fields.Many2one(
        "res.partner",
        string="Use-tax address (buyer location)",
        help=(
            "Partner whose ZIP is used as the destination for use-tax "
            "accrual on vendor bills (since vendor bills don't carry the "
            "buyer's address; the bill's partner_id is the vendor). "
            "Falls back to the company's main address if unset. Sales "
            "tax always uses the customer's shipping address; this "
            "field only matters when ``ostax_accrue_use_tax`` is on."
        ),
    )
    ostax_accrue_use_tax = fields.Boolean(
        string="Accrue use tax on vendor bills",
        default=False,
        help=(
            "Off by default. When on, vendor bills with US partners "
            "and a 5-digit-ZIP buyer location route through the engine "
            "with the BUYER's ZIP (your nexus location, configured via "
            "the Use-tax address field above), producing a synthetic "
            "purchase-tax stack that credits your Use Tax Payable "
            "account. Off → vendor bills bypass the connector and use "
            "Odoo's standard catalog-rate handling (the v0.1.x "
            "behavior)."
        ),
    )
    ostax_use_tax_payable_account_id = fields.Many2one(
        "account.account",
        string="Use Tax Payable account",
        # No domain — account.account.company_id was renamed to
        # company_ids (Many2many) in Odoo 18, so a static
        # company-scoping domain breaks cross-version. The UI is
        # already scoped to the company being edited; multi-company
        # leakage is theoretical and a Many2one anyway can only
        # hold one record.
        help=(
            "Liability account credited by use-tax synthetic taxes "
            "on vendor bills. Required when ``Accrue use tax on "
            "vendor bills`` is on. Sales tax credits a separate "
            "Sales Tax Payable; keeping these distinct simplifies "
            "state-by-state reporting (use tax is filed alongside "
            "sales tax but reported as a separate line on most "
            "state returns)."
        ),
    )
    ostax_cache_ttl_hours = fields.Integer(
        string="Rate cache TTL (hours)",
        default=24,
        help="How long to cache ZIP→rate-stack lookups in worker memory.",
    )
    ostax_fail_soft = fields.Boolean(
        string="Fail soft on engine error",
        default=True,
        help=(
            "When the engine is unreachable or returns 5xx, fall back "
            "to the catalog rate and log a warning. When off, surface "
            "the error to the user."
        ),
    )
    ostax_pos_live_quote = fields.Boolean(
        string="POS live quote",
        default=False,
        help=(
            "When enabled, the POS frontend calls the engine on every "
            "line-add for an accurate cashier preview. Adds 150-300ms "
            "of latency per line over LAN. When disabled, the cashier "
            "preview uses the catalog rate; the receipt shows the "
            "OST-computed rate."
        ),
    )
    ostax_debug_log_enabled = fields.Boolean(
        string="OpenSalesTax debug log",
        default=False,
        help=(
            "When enabled, recent calculations are recorded in a "
            "ring-buffer log visible under Settings → Technical → "
            "OpenSalesTax → Recent calculations."
        ),
    )

    # ------------------------------------------------------------------
    # Operator-experience telemetry (v0.2.1)
    # ------------------------------------------------------------------

    ostax_last_successful_calc_at = fields.Datetime(
        string="Last successful engine call",
        readonly=True,
        copy=False,
        help=(
            "Timestamp of the most recent successful engine call for "
            "this company. Updated whenever the connector talks to "
            "the engine and gets a usable response. A stale value "
            "(or unset) means the engine hasn't been talking to this "
            "company recently — useful when fail-soft is silently "
            "falling back to catalog rates."
        ),
    )
    ostax_failure_streak = fields.Integer(
        string="Engine failure streak",
        default=0,
        readonly=True,
        copy=False,
        help=(
            "Consecutive engine failures since the last success. "
            "Resets to zero on next successful call. When this "
            "crosses ``ostax_failure_streak_threshold``, the connector "
            "posts a mail.activity to "
            "``ostax_admin_alert_recipient_ids`` so silent fail-soft "
            "doesn't go unnoticed."
        ),
    )
    ostax_failure_streak_threshold = fields.Integer(
        string="Alert threshold (consecutive failures)",
        default=5,
        help=(
            "Post a mail.activity warning to admins after this many "
            "consecutive engine failures. Default 5 catches genuine "
            "outages without alerting on transient blips."
        ),
    )
    ostax_admin_alert_recipient_ids = fields.Many2many(
        "res.users",
        relation="res_company_ostax_alert_recipients_rel",
        column1="company_id",
        column2="user_id",
        string="Engine outage alert recipients",
        help=(
            "Users who receive a mail.activity warning when the "
            "engine-failure streak crosses the threshold. Leave empty "
            "to disable activity-based alerting (failures still "
            "increment the streak counter and surface in the debug "
            "log)."
        ),
    )
    ostax_calc_count_today = fields.Integer(
        string="Engine calls today",
        compute="_compute_ostax_calc_count_today",
        help=(
            "Engine calls recorded in the debug log since midnight "
            "(server timezone). Only populated when debug log is on; "
            "0 otherwise."
        ),
    )

    # ------------------------------------------------------------------
    # Per-state nexus filter (v0.3.0)
    # ------------------------------------------------------------------

    ostax_nexus_state_ids = fields.Many2many(
        "res.country.state",
        relation="res_company_ostax_nexus_states_rel",
        column1="company_id",
        column2="state_id",
        string="States with nexus",
        help=(
            "If set, the connector ONLY engages the engine for "
            "customers shipping to one of these states. Out-of-state "
            "US customers fall through to Odoo's standard catalog "
            "rates (typically zero — fiscal positions can refine "
            "this). Leave empty to engage for all US customers "
            "(the default). Use this to match your actual sales-tax "
            "nexus footprint — small merchants typically collect in "
            "only a handful of states."
        ),
    )

    def _ostax_record_engine_success(self) -> None:
        """Reset the failure streak and stamp the last-success time.

        Called from the engine call site after a successful response.
        Idempotent on the timestamp side; the streak reset only writes
        when the value is non-zero, to avoid superfluous DB churn on
        the common path.
        """
        self.ensure_one()
        vals = {"ostax_last_successful_calc_at": fields.Datetime.now()}
        if self.ostax_failure_streak:
            vals["ostax_failure_streak"] = 0
        self.sudo().write(vals)

    def _ostax_record_engine_failure(self) -> None:
        """Increment the failure streak; post an activity if threshold crossed.

        Best-effort: if posting the activity fails (no admin
        recipients configured, mail thread unavailable, etc.), log a
        warning and continue. We never let telemetry-failure break the
        calling tax-compute flow.
        """
        self.ensure_one()
        new_streak = (self.ostax_failure_streak or 0) + 1
        self.sudo().write({"ostax_failure_streak": new_streak})
        threshold = self.ostax_failure_streak_threshold or 0
        if (
            threshold > 0
            and new_streak == threshold  # post once per threshold-crossing
            and self.ostax_admin_alert_recipient_ids
        ):
            self._ostax_post_outage_activity(new_streak)

    def _ostax_post_outage_activity(self, streak: int) -> None:
        """Post a mail.activity to each alert recipient. Best-effort.

        ``res.company`` doesn't carry ``mail.activity.mixin`` on
        Odoo 16/17/18 (and inheriting it would require a registry
        bump on existing installs), so create activity records
        directly via ``self.env["mail.activity"]``. Same end result;
        no schema impact.
        """
        from datetime import timedelta as _timedelta
        try:
            warning_type = self.env.ref(
                "mail.mail_activity_data_warning", raise_if_not_found=False
            )
            if not warning_type:
                warning_type = self.env["mail.activity.type"].search([], limit=1)
            if not warning_type:
                return
            company_model = self.env["ir.model"].sudo()._get("res.company")
            if not company_model:
                return
            today = fields.Date.context_today(self)
            deadline = today + _timedelta(days=1)
            summary = _("OpenSalesTax engine: %d consecutive failures") % streak
            note = _(
                "The OpenSalesTax engine for company %(co)s has failed "
                "%(n)d consecutive calls (threshold: %(t)d). Tax "
                "computation is currently falling back to catalog "
                "rates (if fail-soft is on) or blocking (if off). "
                "Investigate engine health at %(url)s."
            ) % {
                "co": self.name,
                "n": streak,
                "t": self.ostax_failure_streak_threshold,
                "url": self.ostax_api_url or "(unset)",
            }
            Activity = self.env["mail.activity"].sudo()
            for user in self.ostax_admin_alert_recipient_ids:
                Activity.create({
                    "res_model": "res.company",
                    "res_model_id": company_model.id,
                    "res_id": self.id,
                    "activity_type_id": warning_type.id,
                    "date_deadline": deadline,
                    "summary": summary,
                    "note": note,
                    "user_id": user.id,
                })
        except Exception as e:  # noqa: BLE001
            _logger.warning(
                "OST: failed to post engine-outage activity: %s", e
            )

    def _compute_ostax_calc_count_today(self) -> None:
        from datetime import datetime, time as _dt_time
        Log = self.env["ostax.calc.log"].sudo()
        today = fields.Date.context_today(self)
        midnight = datetime.combine(today, _dt_time.min)
        for rec in self:
            rec.ostax_calc_count_today = Log.search_count([
                ("company_id", "=", rec.id),
                ("create_date", ">=", midnight),
            ])

    def _ostax_client(self) -> Any:
        """Return an OpenSalesTaxClient for this company.

        Lazy-imported so the module installs cleanly even if the
        ``opensalestax`` package isn't on the path yet (the
        ``external_dependencies`` manifest entry blocks install in
        that case, but the import shouldn't run at module-load time).

        Raises :class:`UserError` if the company hasn't configured
        the engine URL.
        """
        self.ensure_one()
        if not self.ostax_api_url:
            raise UserError(
                _("OpenSalesTax engine URL not configured for company %s.") % self.name
            )
        from opensalestax import OpenSalesTaxClient

        return OpenSalesTaxClient(
            base_url=self.ostax_api_url,
            api_key=self.ostax_api_key or None,
            timeout=10.0,
            user_agent=f"opensalestax-odoo/18.0 (Odoo company={self.id})",
        )

    def action_ostax_test_connection(self) -> dict[str, Any]:
        """Settings-page button: ping ``/v1/health`` and surface the result.

        Returns an ``ir.actions.client`` notification action so the
        result toasts inline without leaving the settings page.
        """
        self.ensure_one()
        from opensalestax import (  # noqa: PLC0415 — lazy import per _ostax_client
            OpenSalesTaxAPIError,
            OpenSalesTaxNetworkError,
            OpenSalesTaxValidationError,
        )

        try:
            with self._ostax_client() as client:
                started = time.monotonic()
                health = client.health()
                rtt_ms = int((time.monotonic() - started) * 1000)
        except OpenSalesTaxNetworkError as e:
            return self._ostax_notification(
                _("Engine unreachable"),
                _("%s\n\nCheck the engine URL and network connectivity.") % e,
                "danger",
            )
        except OpenSalesTaxAPIError as e:
            return self._ostax_notification(
                _("Engine returned HTTP %s") % e.status_code,
                str(e),
                "warning",
            )
        except OpenSalesTaxValidationError as e:
            return self._ostax_notification(
                _("Unexpected response shape"),
                _("Engine version mismatch likely. Details: %s") % e,
                "warning",
            )
        except UserError:
            raise
        except Exception as e:  # noqa: BLE001 — final safety net
            _logger.exception("Unexpected error in OST connection test")
            return self._ostax_notification(
                _("Unexpected error"), str(e), "danger"
            )

        engine_line = _(
            "Engine v%(version)s · status=%(status)s · "
            "DB %(db)s · RTT %(rtt)d ms"
        ) % {
            "version": health.version,
            "status": health.status,
            "db": "OK" if health.database_connected else "DOWN",
            "rtt": rtt_ms,
        }
        config_summary, hard_warnings = self._ostax_config_summary()
        message = engine_line + "\n\n" + config_summary
        # Surface as warning (yellow) when the engine itself is OK but
        # config has a hard footgun (e.g. accrue_use_tax on with no
        # payable account configured — next vendor bill will raise
        # UserError). Surface as success (green) when engine is OK and
        # no hard warnings. Soft hints (no alert recipients, default
        # buyer-location fallback) don't escalate.
        kind = "success" if (health.status == "ok" and not hard_warnings) else "warning"
        return self._ostax_notification(_("Connection OK"), message, kind)

    def _ostax_config_summary(self) -> tuple[str, bool]:
        """Return ``(human-readable summary, has_hard_warnings)`` for
        the Test Connection result.

        Surfaces config readiness so merchants catch onboarding
        footguns before they hit the calc path. The ``has_hard_warnings``
        flag is True only for config errors that will *break* future
        calls (e.g. ``accrue_use_tax`` on but no payable account →
        next vendor-bill post raises ``UserError``). Soft hints
        (no alert recipients, default buyer-location fallback) are
        informational and don't escalate the notification kind.
        """
        self.ensure_one()
        lines: list[str] = []
        hard_warnings = False

        # Nexus footprint (informational)
        if self.ostax_nexus_state_ids:
            codes = ", ".join(
                sorted(s.code for s in self.ostax_nexus_state_ids if s.code)
            )
            lines.append(_("Nexus: %s") % codes)
        else:
            lines.append(_("Nexus: all 50 states"))

        # Use-tax accrual readiness — HARD warning if account missing
        if self.ostax_accrue_use_tax:
            if self.ostax_use_tax_payable_account_id:
                acct = self.ostax_use_tax_payable_account_id
                lines.append(
                    _("Use-tax accrual: ON (payable: %s ✓)") % acct.code
                )
            else:
                hard_warnings = True
                lines.append(_(
                    "Use-tax accrual: ON (payable: ✗ NOT SET — "
                    "next vendor bill will raise UserError)"
                ))
            if self.ostax_origin_address_id:
                lines.append(
                    _("  buyer location: %s") % self.ostax_origin_address_id.name
                )
            else:
                lines.append(_(
                    "  buyer location: company main address (default)"
                ))
        else:
            lines.append(_("Use-tax accrual: off"))

        # Fail-soft posture (informational)
        lines.append(
            _("Fail-soft: %s") % (_("on") if self.ostax_fail_soft else _("off (strict)"))
        )

        # Outage alerts — soft hint only (don't escalate the notification)
        n_recipients = len(self.ostax_admin_alert_recipient_ids)
        if n_recipients:
            lines.append(
                _("Outage alerts: %(n)d recipient(s) at %(t)d failures") % {
                    "n": n_recipients,
                    "t": self.ostax_failure_streak_threshold or 0,
                }
            )
        else:
            lines.append(_(
                "Outage alerts: no recipients configured "
                "(recommended for production)"
            ))

        return "\n".join(lines), hard_warnings

    @staticmethod
    def _ostax_notification(title: str, message: str, kind: str) -> dict[str, Any]:
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": kind,
                "sticky": kind != "success",
            },
        }
