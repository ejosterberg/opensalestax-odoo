# SPDX-License-Identifier: LGPL-3.0-or-later
"""Per-move OST breakdown storage.

Phase 5 populates ostax_breakdown when compute_all engages the engine.
The form view (Phase 5 too) renders the breakdown as a notebook tab.
"""

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ostax_breakdown = fields.Text(
        string="OST jurisdiction breakdown",
        readonly=True,
        copy=False,
        help=(
            "JSON-serialized list of per-jurisdiction tax contributions "
            "captured at the time of calculation. Stored on the move "
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
