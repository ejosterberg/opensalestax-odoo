# SPDX-License-Identifier: LGPL-3.0-or-later
"""Per-company OpenSalesTax settings.

The settings live on res.company so multi-company Odoo deployments
can configure per-company engines (or disable OST per company
without disabling globally).

Phase 3 (settings + connection test) populates the engine-client
helper and the Test Connection action. Phase 9 wires the cache
TTL into ormcache.
"""

from odoo import fields, models


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
        string="Origin address",
        help=(
            "Nexus / shipping origin partner. Use-tax accrual on vendor "
            "bills uses this address as the destination; sales use the "
            "customer's shipping address."
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
