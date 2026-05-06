# SPDX-License-Identifier: LGPL-3.0-or-later
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

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
