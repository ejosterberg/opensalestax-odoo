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

        return self._ostax_notification(
            _("Connection OK"),
            _(
                "Engine v%(version)s · status=%(status)s · "
                "DB %(db)s · RTT %(rtt)d ms"
            )
            % {
                "version": health.version,
                "status": health.status,
                "db": "OK" if health.database_connected else "DOWN",
                "rtt": rtt_ms,
            },
            "success" if health.status == "ok" else "warning",
        )

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
