# SPDX-License-Identifier: LGPL-3.0-or-later OR AGPL-3.0-or-later
"""Settings page wiring — exposes res.company.ostax_* fields under
Settings → Accounting → OpenSalesTax.

The Test Connection button delegates to the underlying res.company
record so the same logic powers both the inline settings UI and
any direct calls (e.g. the eventual debug menu).
"""

from typing import Any

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ostax_enabled = fields.Boolean(related="company_id.ostax_enabled", readonly=False)
    ostax_api_url = fields.Char(related="company_id.ostax_api_url", readonly=False)
    ostax_api_key = fields.Char(related="company_id.ostax_api_key", readonly=False)
    ostax_origin_address_id = fields.Many2one(
        related="company_id.ostax_origin_address_id", readonly=False
    )
    ostax_accrue_use_tax = fields.Boolean(
        related="company_id.ostax_accrue_use_tax", readonly=False
    )
    ostax_use_tax_payable_account_id = fields.Many2one(
        related="company_id.ostax_use_tax_payable_account_id", readonly=False
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
    ostax_last_successful_calc_at = fields.Datetime(
        related="company_id.ostax_last_successful_calc_at", readonly=True
    )
    ostax_failure_streak = fields.Integer(
        related="company_id.ostax_failure_streak", readonly=True
    )
    ostax_failure_streak_threshold = fields.Integer(
        related="company_id.ostax_failure_streak_threshold", readonly=False
    )
    ostax_admin_alert_recipient_ids = fields.Many2many(
        related="company_id.ostax_admin_alert_recipient_ids", readonly=False
    )
    ostax_calc_count_today = fields.Integer(
        related="company_id.ostax_calc_count_today", readonly=True
    )
    ostax_nexus_state_ids = fields.Many2many(
        related="company_id.ostax_nexus_state_ids", readonly=False
    )

    def action_ostax_test_connection(self) -> dict[str, Any]:
        """Forward to the company-level connection test."""
        self.ensure_one()
        return self.company_id.action_ostax_test_connection()
