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
