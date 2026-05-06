# SPDX-License-Identifier: LGPL-3.0-or-later
"""Phase 4 — compute_all override.

Tests cover:

* Engagement gates (US partner with valid ZIP / non-US partner / OST
  disabled / no ZIP / no partner) — all bypass go through super().
* Happy path: 4-jurisdiction breakdown → 4 synthetic taxes created;
  per-jurisdiction tax amounts sum to the line total exactly.
* Refund: ``is_refund=True`` produces sign-flipped amounts.
* Synthetic-tax materialization: idempotent (second call reuses the
  records); per-company scoped.
* Failure modes: network error fail-soft; 5xx fail-soft; 4xx
  UserError; validation error fail-soft; ``fail_soft=False`` raises.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import OstaxTestCase


def _mock_calc_result(
    *,
    subtotal: str = "100.00",
    tax_total: str = "9.0250",
    line_tax: str = "9.0250",
    rate_pct: str = "9.025",
    jurisdictions: list[tuple[str, str, str, str]] | None = None,
) -> MagicMock:
    """Build a mock ``CalculationResult`` matching the SDK's shape.

    ``jurisdictions`` is a list of (name, type, rate_pct, tax) tuples.
    Defaults to a 4-jurisdiction Minneapolis breakdown.
    """
    if jurisdictions is None:
        jurisdictions = [
            ("Minnesota", "state", "6.875", "6.8750"),
            ("Hennepin County", "county", "0.15", "0.1500"),
            ("Minneapolis", "city", "0.50", "0.5000"),
            ("Metro Area Transit", "district", "1.50", "1.5000"),
        ]
    j_mocks = []
    for name, jtype, rate_pct_v, tax_v in jurisdictions:
        m = MagicMock()
        m.name = name
        m.type = jtype
        m.rate_pct = Decimal(rate_pct_v)
        m.tax = Decimal(tax_v)
        j_mocks.append(m)

    line = MagicMock()
    line.amount = Decimal(subtotal)
    line.tax = Decimal(line_tax)
    line.rate_pct = Decimal(rate_pct)
    line.jurisdictions = j_mocks
    line.note = None

    result = MagicMock()
    result.subtotal = Decimal(subtotal)
    result.tax_total = Decimal(tax_total)
    result.lines = [line]
    result.disclaimer = "Calculation only"
    return result


@tagged("post_install", "-at_install")
class TestComputeAllGates(OstaxTestCase):
    """Tests for the engagement gates — when OST does and doesn't engage."""

    def setUp(self) -> None:
        super().setUp()
        self.us_partner = self.env["res.partner"].create(
            {
                "name": "US Test Customer",
                "country_id": self.us_country.id,
                "zip": "55401",
            }
        )
        self.tax = self.env["account.tax"].create(
            {
                "name": "Catalog 0%",
                "amount": 0.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.company.id,
            }
        )

    def test_engages_for_us_partner_with_valid_zip(self) -> None:
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ) as m:
            self.tax.compute_all(100.0, partner=self.us_partner)
        m.assert_called_once()

    def test_bypasses_when_ostax_disabled(self) -> None:
        self.company.ostax_enabled = False
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.tax.compute_all(100.0, partner=self.us_partner)
        m.assert_not_called()

    def test_bypasses_when_no_api_url(self) -> None:
        self.company.ostax_api_url = False
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.tax.compute_all(100.0, partner=self.us_partner)
        m.assert_not_called()

    def test_bypasses_when_no_partner(self) -> None:
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.tax.compute_all(100.0, partner=None)
        m.assert_not_called()

    def test_bypasses_for_non_us_partner(self) -> None:
        ca = self.env.ref("base.ca")
        partner = self.env["res.partner"].create(
            {"name": "CA Test", "country_id": ca.id, "zip": "M5V 3L9"}
        )
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.tax.compute_all(100.0, partner=partner)
        m.assert_not_called()

    def test_bypasses_when_zip_too_short(self) -> None:
        self.us_partner.zip = "123"
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.tax.compute_all(100.0, partner=self.us_partner)
        m.assert_not_called()

    def test_bypasses_when_zip_non_numeric(self) -> None:
        self.us_partner.zip = "ABCDE"
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.tax.compute_all(100.0, partner=self.us_partner)
        m.assert_not_called()


@tagged("post_install", "-at_install")
class TestComputeAllHappy(OstaxTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "MSP Customer",
                "country_id": self.us_country.id,
                "zip": "55401",
            }
        )
        self.tax = self.env["account.tax"].create(
            {
                "name": "Catalog 0%",
                "amount": 0.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.company.id,
            }
        )

    def test_returns_per_jurisdiction_breakdown(self) -> None:
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ):
            result = self.tax.compute_all(100.0, partner=self.partner)

        self.assertEqual(len(result["taxes"]), 4)
        names = {t["name"] for t in result["taxes"]}
        self.assertTrue(any("Minnesota" in n for n in names))
        self.assertTrue(any("Hennepin" in n for n in names))
        self.assertTrue(any("Minneapolis" in n for n in names))
        self.assertEqual(result["total_excluded"], 100.0)
        self.assertAlmostEqual(result["total_included"], 109.025, places=4)

    def test_breakdown_sums_to_line_tax(self) -> None:
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ):
            result = self.tax.compute_all(100.0, partner=self.partner)
        total = sum(t["amount"] for t in result["taxes"])
        self.assertAlmostEqual(total, 9.025, places=4)

    def test_creates_synthetic_taxes(self) -> None:
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ):
            self.tax.compute_all(100.0, partner=self.partner)
        synthetics = self.env["account.tax"].search(
            [
                ("company_id", "=", self.company.id),
                ("ostax_synthetic", "=", True),
            ]
        )
        self.assertEqual(len(synthetics), 4)
        types = {s.ostax_jurisdiction_type for s in synthetics}
        self.assertEqual(types, {"state", "county", "city", "district"})

    def test_synthetic_tax_creation_is_idempotent(self) -> None:
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ):
            self.tax.compute_all(100.0, partner=self.partner)
            self.tax.compute_all(100.0, partner=self.partner)
        synthetics = self.env["account.tax"].search(
            [("company_id", "=", self.company.id), ("ostax_synthetic", "=", True)]
        )
        self.assertEqual(len(synthetics), 4)  # Not 8

    def test_refund_flips_signs(self) -> None:
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ):
            result = self.tax.compute_all(
                100.0, partner=self.partner, is_refund=True
            )
        self.assertAlmostEqual(result["total_excluded"], -100.0, places=4)
        self.assertAlmostEqual(result["total_included"], -109.025, places=4)
        self.assertTrue(all(t["amount"] <= 0 for t in result["taxes"]))


@tagged("post_install", "-at_install")
class TestComputeAllExemption(OstaxTestCase):
    """Phase 7 — exemption short-circuit.

    Partners with a valid (unexpired) exemption certificate skip the
    engine entirely and produce zero tax.
    """

    def setUp(self) -> None:
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "Exempt Reseller",
                "country_id": self.us_country.id,
                "zip": "55401",
                "ostax_exemption_certificate": "MN-RESALE-12345",
                "ostax_use_code": "resale",
            }
        )
        self.tax = self.env["account.tax"].create(
            {
                "name": "Catalog 0%",
                "amount": 0.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.company.id,
            }
        )

    def test_exempt_partner_returns_zero_tax_no_engine_call(self) -> None:
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            result = self.tax.compute_all(100.0, partner=self.partner)
        m.assert_not_called()
        self.assertEqual(result["taxes"], [])
        self.assertEqual(result["total_excluded"], 100.0)
        self.assertEqual(result["total_included"], 100.0)

    def test_exempt_refund_flips_signs_still_zero_tax(self) -> None:
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            result = self.tax.compute_all(
                100.0, partner=self.partner, is_refund=True
            )
        m.assert_not_called()
        self.assertEqual(result["total_excluded"], -100.0)
        self.assertEqual(result["total_included"], -100.0)

    def test_expired_certificate_does_not_apply(self) -> None:
        from datetime import date, timedelta

        self.partner.ostax_exemption_expiry = date.today() - timedelta(days=1)
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ) as m:
            result = self.tax.compute_all(100.0, partner=self.partner)
        m.assert_called_once()
        self.assertEqual(len(result["taxes"]), 4)

    def test_future_expiry_applies(self) -> None:
        from datetime import date, timedelta

        self.partner.ostax_exemption_expiry = date.today() + timedelta(days=30)
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            result = self.tax.compute_all(100.0, partner=self.partner)
        m.assert_not_called()
        self.assertEqual(result["taxes"], [])

    def test_no_certificate_does_not_apply(self) -> None:
        self.partner.ostax_exemption_certificate = False
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ) as m:
            self.tax.compute_all(100.0, partner=self.partner)
        m.assert_called_once()


@tagged("post_install", "-at_install")
class TestDebugLog(OstaxTestCase):
    """Phase 9 — opt-in debug log of engine calls."""

    def setUp(self) -> None:
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "MSP Customer",
                "country_id": self.us_country.id,
                "zip": "55401",
            }
        )
        self.tax = self.env["account.tax"].create(
            {
                "name": "Catalog 0%",
                "amount": 0.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.company.id,
            }
        )

    def test_log_disabled_by_default(self) -> None:
        self.company.ostax_debug_log_enabled = False
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ):
            self.tax.compute_all(100.0, partner=self.partner)
        logs = self.env["ostax.calc.log"].search(
            [("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(logs), 0)

    def test_log_writes_when_enabled(self) -> None:
        self.company.ostax_debug_log_enabled = True
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_mock_calc_result(),
        ):
            self.tax.compute_all(100.0, partner=self.partner)
        logs = self.env["ostax.calc.log"].search(
            [("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].kind, "engine_call")
        self.assertEqual(logs[0].dest_zip, "55401")
        self.assertGreaterEqual(logs[0].response_ms, 0)


@tagged("post_install", "-at_install")
class TestComputeAllFailures(OstaxTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "MSP Customer",
                "country_id": self.us_country.id,
                "zip": "55401",
            }
        )
        self.tax = self.env["account.tax"].create(
            {
                "name": "Catalog 5%",
                "amount": 5.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.company.id,
            }
        )

    def test_network_error_fail_soft_falls_back_to_super(self) -> None:
        from opensalestax import OpenSalesTaxNetworkError

        self.company.ostax_fail_soft = True
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxNetworkError("connection refused"),
        ):
            result = self.tax.compute_all(100.0, partner=self.partner)
        # Super's catalog rate of 5% should produce one tax entry.
        self.assertEqual(len(result["taxes"]), 1)
        self.assertAlmostEqual(result["taxes"][0]["amount"], 5.0, places=4)

    def test_network_error_no_fail_soft_raises_user_error(self) -> None:
        from opensalestax import OpenSalesTaxNetworkError

        self.company.ostax_fail_soft = False
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxNetworkError("connection refused"),
        ), self.assertRaises(UserError):
            self.tax.compute_all(100.0, partner=self.partner)

    def test_5xx_fail_soft_falls_back(self) -> None:
        from opensalestax import OpenSalesTaxAPIError

        self.company.ostax_fail_soft = True
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxAPIError(status_code=503, message="starting"),
        ):
            result = self.tax.compute_all(100.0, partner=self.partner)
        self.assertEqual(len(result["taxes"]), 1)

    def test_4xx_always_raises_user_error(self) -> None:
        from opensalestax import OpenSalesTaxAPIError

        # Even with fail_soft=True, a 4xx (config / data issue) should
        # surface to the merchant rather than silently succeed.
        self.company.ostax_fail_soft = True
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxAPIError(status_code=422, message="bad zip"),
        ), self.assertRaises(UserError):
            self.tax.compute_all(100.0, partner=self.partner)

    def test_validation_error_fail_soft(self) -> None:
        from opensalestax import OpenSalesTaxValidationError

        self.company.ostax_fail_soft = True
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxValidationError("schema mismatch"),
        ):
            result = self.tax.compute_all(100.0, partner=self.partner)
        self.assertEqual(len(result["taxes"]), 1)
