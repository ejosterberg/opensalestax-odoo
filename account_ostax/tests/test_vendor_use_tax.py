# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.2.0 — vendor-bill use-tax accrual at the buyer's location.

When ``company.ostax_accrue_use_tax`` is ON, vendor bills route
through the engine using the BUYER's ZIP (resolved from
``ostax_origin_address_id`` or ``company.partner_id``), producing
synthetic purchase-typed taxes that credit the company's
configured Use Tax Payable account.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.release import version_info
from odoo.tests.common import tagged

from .common import OstaxTestCase

_HAS_BATCH_ENGINE = version_info[0] >= 18


def _calc_result_one_jurisdiction():
    """Mock engine result: one $5 jurisdiction at 5% on a $100 line."""
    j = MagicMock()
    j.name = "Minnesota"
    j.type = "state"
    j.rate_pct = 5.0
    j.tax = 5.0

    line = MagicMock()
    line.jurisdictions = [j]
    line.tax = 5.0

    result = MagicMock()
    result.lines = [line]
    return result


@tagged("post_install", "-at_install")
class TestComputeAllUseTaxAccrual(OstaxTestCase):
    """Legacy ``compute_all`` path — purchase-typed taxes engage the
    engine when use-tax accrual is ON, using the buyer's ZIP."""

    def setUp(self) -> None:
        super().setUp()
        self.us_vendor = self.env["res.partner"].create({
            "name": "US Vendor (out-of-state)",
            "country_id": self.us_country.id,
            "zip": "94016",  # San Francisco
        })
        # Buyer location: company nexus is in Minneapolis, MN
        self.buyer_addr = self.env["res.partner"].create({
            "name": "Our Minneapolis warehouse",
            "country_id": self.us_country.id,
            "zip": "55401",
        })
        # Use-tax payable account (cross-version safe)
        self.use_tax_acct = self._ostax_get_or_make_liability_account()
        self.purchase_tax = self.env["account.tax"].create(
            self._ostax_tax_vals(name="Vendor 7% purchase tax", amount=7.0)
        )
        self.purchase_tax.type_tax_use = "purchase"

    def test_accrual_off_bypasses(self) -> None:
        """Default (OFF) — purchase tax falls through to catalog."""
        self.company.ostax_accrue_use_tax = False
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.purchase_tax.compute_all(100.0, partner=self.us_vendor)
        m.assert_not_called()

    def test_accrual_on_no_account_raises(self) -> None:
        """Opted in but no Use Tax Payable account → UserError."""
        self.company.ostax_accrue_use_tax = True
        self.company.ostax_use_tax_payable_account_id = False
        with patch("opensalestax.OpenSalesTaxClient.calculate"):
            with self.assertRaises(UserError) as cm:
                self.purchase_tax.compute_all(100.0, partner=self.us_vendor)
        self.assertIn("Use Tax Payable", str(cm.exception))

    def test_accrual_uses_buyer_zip_not_vendor_zip(self) -> None:
        """When accrual is on, the engine call uses the BUYER's ZIP
        (Minneapolis 55401), not the vendor's ZIP (San Francisco
        94016). Verifies the v0.1.x bug-by-bypass is replaced with
        proper handling."""
        self.company.ostax_accrue_use_tax = True
        self.company.ostax_use_tax_payable_account_id = self.use_tax_acct
        self.company.ostax_origin_address_id = self.buyer_addr
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_calc_result_one_jurisdiction(),
        ) as m:
            self.purchase_tax.compute_all(100.0, partner=self.us_vendor)
        m.assert_called_once()
        call_kwargs = m.call_args.kwargs
        address = call_kwargs["address"]
        self.assertEqual(address.zip5, "55401",
            "Engine should be called with BUYER's ZIP, not vendor's")

    def test_accrual_falls_back_to_company_partner_when_origin_unset(self) -> None:
        """Without ``ostax_origin_address_id`` set, the buyer-location
        falls back to ``company.partner_id``."""
        self.company.ostax_accrue_use_tax = True
        self.company.ostax_use_tax_payable_account_id = self.use_tax_acct
        self.company.ostax_origin_address_id = False
        # Ensure company partner has a US ZIP for the test
        self.company.partner_id.write({
            "country_id": self.us_country.id,
            "zip": "10001",  # NYC
        })
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_calc_result_one_jurisdiction(),
        ) as m:
            self.purchase_tax.compute_all(100.0, partner=self.us_vendor)
        m.assert_called_once()
        self.assertEqual(m.call_args.kwargs["address"].zip5, "10001")

    def test_synthetic_tax_carries_purchase_type_use(self) -> None:
        """The synthetic tax materialized for use-tax accrual should
        be ``type_tax_use='purchase'`` so it doesn't pollute sales-tax
        reporting."""
        self.company.ostax_accrue_use_tax = True
        self.company.ostax_use_tax_payable_account_id = self.use_tax_acct
        self.company.ostax_origin_address_id = self.buyer_addr
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_calc_result_one_jurisdiction(),
        ):
            self.purchase_tax.compute_all(100.0, partner=self.us_vendor)
        # Find the synthetic that was materialized
        synth = self.env["account.tax"].search([
            ("ostax_synthetic", "=", True),
            ("ostax_jurisdiction_name", "=", "Minnesota"),
            ("ostax_jurisdiction_type", "=", "state"),
            ("type_tax_use", "=", "purchase"),
        ], limit=1)
        self.assertTrue(synth, "Purchase-typed synthetic tax should have been created")
        self.assertEqual(synth.type_tax_use, "purchase")
        # Name should carry the "use tax" disambiguation suffix
        self.assertIn("use tax", synth.name)

    def test_sale_and_purchase_synthetics_are_separate_records(self) -> None:
        """Engaging both sales and use-tax for the same jurisdiction
        creates two distinct synthetic records (different
        type_tax_use). This prevents the two flows from polluting
        each other's reporting."""
        self.company.ostax_accrue_use_tax = True
        self.company.ostax_use_tax_payable_account_id = self.use_tax_acct
        self.company.ostax_origin_address_id = self.buyer_addr
        # Sales path: a US customer with the SAME ZIP as our nexus
        customer = self.env["res.partner"].create({
            "name": "MN Customer",
            "country_id": self.us_country.id,
            "zip": "55401",
        })
        sale_tax = self.env["account.tax"].create(
            self._ostax_tax_vals(name="Catalog 0%", amount=0.0)
        )
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_calc_result_one_jurisdiction(),
        ):
            sale_tax.compute_all(100.0, partner=customer)
            self.purchase_tax.compute_all(100.0, partner=self.us_vendor)
        sale_synth = self.env["account.tax"].search([
            ("ostax_synthetic", "=", True),
            ("ostax_jurisdiction_name", "=", "Minnesota"),
            ("type_tax_use", "=", "sale"),
        ], limit=1)
        purchase_synth = self.env["account.tax"].search([
            ("ostax_synthetic", "=", True),
            ("ostax_jurisdiction_name", "=", "Minnesota"),
            ("type_tax_use", "=", "purchase"),
        ], limit=1)
        self.assertTrue(sale_synth)
        self.assertTrue(purchase_synth)
        self.assertNotEqual(sale_synth.id, purchase_synth.id,
            "Sales and use-tax synthetics for the same jurisdiction "
            "must be separate records (different type_tax_use).")


@tagged("post_install", "-at_install")
class TestBatchEngineUseTaxAccrual(OstaxTestCase):
    """Batch-engine (Odoo 18+) path — same opt-in / opt-out semantics
    as compute_all but for the modern tax engine."""

    def setUp(self) -> None:
        super().setUp()
        self.vendor = self.env["res.partner"].create({
            "name": "US Vendor at MN address",
            "country_id": self.us_country.id,
            "zip": "94016",  # vendor's ZIP — should NOT be used
        })
        self.buyer_addr = self.env["res.partner"].create({
            "name": "Our nexus",
            "country_id": self.us_country.id,
            "zip": "55401",
        })
        self.use_tax_acct = self._ostax_get_or_make_liability_account()

    def _make_inbound_base_line(self):
        Tax = self.env["account.tax"]

        class _FakeMove:
            move_type = "in_invoice"
            # Set to "posted" so the post-engagement line-tag-persistence
            # block early-returns (it only writes on draft moves). Our
            # _FakeLine doesn't carry a writable tax_ids field anyway.
            state = "posted"

        class _FakeLine:
            _name = "account.move.line"
            move_id = _FakeMove()

        return {
            "partner_id": self.vendor,
            "currency_id": self.vendor.currency_id or self.env.company.currency_id,
            "price_unit": 100.0,
            "quantity": 1.0,
            "discount": 0.0,
            "product_id": False,
            "tax_ids": Tax,
            "record": _FakeLine(),
        }

    def test_accrual_off_inbound_bypasses(self) -> None:
        if not _HAS_BATCH_ENGINE:
            self.skipTest("Batch tax engine only exists on Odoo 18+")
        self.company.ostax_accrue_use_tax = False
        Tax = self.env["account.tax"]
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            Tax._ostax_inject_into_base_line(
                self._make_inbound_base_line(), self.company
            )
        m.assert_not_called()

    def test_accrual_on_inbound_engages_with_buyer_zip(self) -> None:
        if not _HAS_BATCH_ENGINE:
            self.skipTest("Batch tax engine only exists on Odoo 18+")
        self.company.ostax_accrue_use_tax = True
        self.company.ostax_use_tax_payable_account_id = self.use_tax_acct
        self.company.ostax_origin_address_id = self.buyer_addr
        Tax = self.env["account.tax"]
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_calc_result_one_jurisdiction(),
        ) as m:
            Tax._ostax_inject_into_base_line(
                self._make_inbound_base_line(), self.company
            )
        m.assert_called_once()
        # Engine called with buyer's ZIP, not vendor's
        self.assertEqual(m.call_args.kwargs["address"].zip5, "55401")

    def test_accrual_on_inbound_no_account_raises(self) -> None:
        if not _HAS_BATCH_ENGINE:
            self.skipTest("Batch tax engine only exists on Odoo 18+")
        self.company.ostax_accrue_use_tax = True
        self.company.ostax_use_tax_payable_account_id = False
        self.company.ostax_origin_address_id = self.buyer_addr
        Tax = self.env["account.tax"]
        with patch("opensalestax.OpenSalesTaxClient.calculate"):
            with self.assertRaises(UserError):
                Tax._ostax_inject_into_base_line(
                    self._make_inbound_base_line(), self.company
                )
