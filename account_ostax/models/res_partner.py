# SPDX-License-Identifier: LGPL-3.0-or-later
"""Customer-side exemption certificate fields.

Phase 7 wires these into the calc payload sent to the engine.
"""

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ostax_exemption_certificate = fields.Char(
        string="OST exemption certificate",
        help=(
            "Resale / government / nonprofit / other tax-exemption "
            "certificate number. When set on a customer, the engine "
            "applies the exemption logic associated with the use code."
        ),
    )
    ostax_use_code = fields.Selection(
        selection=[
            ("resale", "Resale"),
            ("government", "Government"),
            ("nonprofit", "Nonprofit"),
            ("other", "Other"),
        ],
        string="OST exemption type",
    )
    ostax_exemption_expiry = fields.Date(
        string="OST exemption expiry",
        help="Optional expiry date. Past expiry, the certificate is ignored.",
    )
