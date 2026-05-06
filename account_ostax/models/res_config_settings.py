# SPDX-License-Identifier: LGPL-3.0-or-later
"""Settings page wiring — exposes res.company.ostax_* fields under
Settings → Accounting → OpenSalesTax.

Phase 3 will populate this with the actual fields (related to
res.company) and wire the Test Connection button.
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ostax_enabled = fields.Boolean(related="company_id.ostax_enabled", readonly=False)
    ostax_api_url = fields.Char(related="company_id.ostax_api_url", readonly=False)
    ostax_api_key = fields.Char(related="company_id.ostax_api_key", readonly=False)
    ostax_origin_address_id = fields.Many2one(
        related="company_id.ostax_origin_address_id", readonly=False
    )
    ostax_cache_ttl_hours = fields.Integer(
        related="company_id.ostax_cache_ttl_hours", readonly=False
    )
    ostax_fail_soft = fields.Boolean(related="company_id.ostax_fail_soft", readonly=False)
    ostax_pos_live_quote = fields.Boolean(
        related="company_id.ostax_pos_live_quote", readonly=False
    )
    ostax_debug_log_enabled = fields.Boolean(
        related="company_id.ostax_debug_log_enabled", readonly=False
    )
