# SPDX-License-Identifier: LGPL-3.0-or-later
"""Phase 3 — settings + connection-test action."""

from __future__ import annotations

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import OstaxTestCase


@tagged("post_install", "-at_install")
class TestSettings(OstaxTestCase):
    def test_company_fields_persist(self) -> None:
        self.company.write({"ostax_api_url": "http://example.com:9000"})
        self.assertEqual(self.company.ostax_api_url, "http://example.com:9000")
        self.assertTrue(self.company.ostax_enabled)
        self.assertEqual(self.company.ostax_cache_ttl_hours, 24)

    def test_test_connection_no_url_raises(self) -> None:
        self.company.write({"ostax_api_url": False})
        with self.assertRaises(UserError):
            self.company.action_ostax_test_connection()

    def test_test_connection_happy_path(self) -> None:
        with self._patch_health(status="ok", version="0.54.1"):
            result = self.company.action_ostax_test_connection()
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("0.54.1", result["params"]["message"])
        self.assertIn("OK", result["params"]["message"])

    def test_test_connection_degraded_returns_warning(self) -> None:
        with self._patch_health(status="degraded", version="0.54.1"):
            result = self.company.action_ostax_test_connection()
        self.assertEqual(result["params"]["type"], "warning")

    def test_test_connection_network_error(self) -> None:
        from opensalestax import OpenSalesTaxNetworkError

        with patch(
            "opensalestax.OpenSalesTaxClient.health",
            side_effect=OpenSalesTaxNetworkError("connection refused"),
        ):
            result = self.company.action_ostax_test_connection()
        self.assertEqual(result["params"]["type"], "danger")
        self.assertIn("unreachable", result["params"]["title"].lower())
        self.assertTrue(result["params"]["sticky"])

    def test_test_connection_api_error(self) -> None:
        from opensalestax import OpenSalesTaxAPIError

        with patch(
            "opensalestax.OpenSalesTaxClient.health",
            side_effect=OpenSalesTaxAPIError(status_code=503, message="starting"),
        ):
            result = self.company.action_ostax_test_connection()
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("503", result["params"]["title"])

    def test_test_connection_validation_error(self) -> None:
        from opensalestax import OpenSalesTaxValidationError

        with patch(
            "opensalestax.OpenSalesTaxClient.health",
            side_effect=OpenSalesTaxValidationError("schema mismatch"),
        ):
            result = self.company.action_ostax_test_connection()
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("response shape", result["params"]["title"].lower())

    def test_settings_forwards_to_company(self) -> None:
        settings = self.env["res.config.settings"].create({})
        with self._patch_health():
            result = settings.action_ostax_test_connection()
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "success")

    # ------------------------------------------------------------------
    # v0.3.3 — config-readiness summary on Test Connection
    # ------------------------------------------------------------------

    def test_test_connection_includes_config_summary(self) -> None:
        with self._patch_health():
            result = self.company.action_ostax_test_connection()
        msg = result["params"]["message"]
        # Default fixture: no nexus, no accrue_use_tax, fail-soft on,
        # no alert recipients. All four lines should appear.
        self.assertIn("Nexus:", msg)
        self.assertIn("Use-tax accrual: off", msg)
        self.assertIn("Fail-soft:", msg)
        self.assertIn("Outage alerts:", msg)

    def test_test_connection_warns_when_use_tax_account_missing(self) -> None:
        """Hard footgun: accrue_use_tax on but no payable account →
        next vendor-bill post raises UserError. Surface as warning."""
        self.company.write({
            "ostax_accrue_use_tax": True,
            "ostax_use_tax_payable_account_id": False,
        })
        with self._patch_health():
            result = self.company.action_ostax_test_connection()
        # Still toasts, but kind escalates from success → warning
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("NOT SET", result["params"]["message"])

    def test_test_connection_use_tax_account_set_clears_warning(self) -> None:
        """Config the account → kind goes back to success."""
        self.company.write({
            "ostax_accrue_use_tax": True,
            "ostax_use_tax_payable_account_id":
                self._ostax_get_or_make_liability_account().id,
        })
        with self._patch_health():
            result = self.company.action_ostax_test_connection()
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("Use-tax accrual: ON", result["params"]["message"])

    def test_test_connection_lists_nexus_states(self) -> None:
        us = self.env.ref("base.us")
        State = self.env["res.country.state"]
        mn = State.search(
            [("country_id", "=", us.id), ("code", "=", "MN")], limit=1
        )
        if not mn:
            self.skipTest("MN state not seeded in this Odoo image")
        self.company.ostax_nexus_state_ids = [(6, 0, [mn.id])]
        with self._patch_health():
            result = self.company.action_ostax_test_connection()
        self.assertIn("Nexus: MN", result["params"]["message"])

    def test_test_connection_no_recipients_is_soft_hint(self) -> None:
        """No alert recipients is a soft hint, not a hard warning —
        kind stays at success."""
        self.company.ostax_admin_alert_recipient_ids = [(5, 0, 0)]
        with self._patch_health():
            result = self.company.action_ostax_test_connection()
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("no recipients configured", result["params"]["message"])
