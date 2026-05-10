# SPDX-License-Identifier: LGPL-3.0-or-later OR AGPL-3.0-or-later
"""Opt-in admin debug log of recent OST calculations.

Capped at 50 entries per company; oldest pruned on insert. Disabled by
default. Visible under Settings → Technical → OpenSalesTax → Recent
calculations once Phase 9 wires the view.
"""

from odoo import fields, models


class OstaxCalcLog(models.Model):
    _name = "ostax.calc.log"
    _description = "OpenSalesTax calculation log entry"
    _order = "create_date desc"
    _rec_name = "create_date"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    kind = fields.Selection(
        [
            ("engine_call", "Engine call"),
            ("cache_hit", "Cache hit"),
            ("error", "Error"),
        ],
        required=True,
    )
    origin_zip = fields.Char()
    dest_zip = fields.Char()
    total_amount = fields.Monetary(currency_field="company_currency_id")
    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    engine_version = fields.Char()
    response_ms = fields.Integer(string="Response (ms)")
    error_message = fields.Text()
