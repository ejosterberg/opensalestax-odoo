# SPDX-License-Identifier: LGPL-3.0-or-later
from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    ostax_breakdown = fields.Text(
        string="OST jurisdiction breakdown",
        readonly=True,
        copy=False,
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
    ostax_offline_calc = fields.Boolean(
        string="OST computed offline",
        readonly=True,
        copy=False,
        help="True if the rate was retrieved from cache while the engine was unreachable.",
    )
    ostax_breakdown_pretty = fields.Html(
        string="OST breakdown (rendered)",
        compute="_compute_ostax_breakdown_pretty",
        sanitize=False,  # server-rendered, all values escaped
    )

    def _compute_ostax_breakdown_pretty(self) -> None:
        from ._breakdown_html import breakdown_to_html
        for rec in self:
            rec.ostax_breakdown_pretty = breakdown_to_html(rec.ostax_breakdown)
