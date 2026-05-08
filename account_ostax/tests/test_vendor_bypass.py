# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.1.15 — defensive bypass on vendor bills + purchase taxes (default).

When the company has NOT opted in to use-tax accrual (the v0.2.0
default = off), the addon must NOT call the engine on vendor bills
or purchase-typed catalog taxes; falling through to Odoo's
standard catalog-rate handling is correct.

For the opt-in (use-tax accrual ON) path, see
``test_vendor_use_tax.py``.
"""

from __future__ import annotations

from unittest.mock import patch

from odoo.release import version_info
from odoo.tests.common import tagged

from .common import OstaxTestCase

# Odoo 16/17 don't have the batch tax engine. Our override defensively
# defines ``_add_tax_details_in_base_lines`` on every branch (it
# no-ops via super-getattr), so a hasattr check can't distinguish
# branches; use the Odoo version directly.
_HAS_BATCH_ENGINE = version_info[0] >= 18


@tagged("post_install", "-at_install")
class TestComputeAllPurchaseBypass(OstaxTestCase):
    """Legacy ``compute_all`` path — purchase-typed taxes must fall
    through to super() when use-tax accrual is OFF (the default)."""

    def setUp(self) -> None:
        super().setUp()
        # Defensive: ensure use-tax accrual is OFF for these tests.
        # OstaxTestCase setUpClass leaves it at the default (False),
        # but be explicit so the contract is visible.
        self.company.ostax_accrue_use_tax = False
        self.us_partner = self.env["res.partner"].create({
            "name": "US Vendor",
            "country_id": self.us_country.id,
            "zip": "55401",
        })
        self.purchase_tax = self.env["account.tax"].create(
            self._ostax_tax_vals(name="Vendor 7% purchase tax", amount=7.0)
        )
        self.purchase_tax.type_tax_use = "purchase"

    def test_purchase_tax_bypasses_engine_when_accrual_off(self) -> None:
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.purchase_tax.compute_all(100.0, partner=self.us_partner)
        m.assert_not_called()

    def test_sale_tax_still_engages(self) -> None:
        # Confirm the new check didn't accidentally short-circuit
        # legitimate sales-tax computations.
        sale_tax = self.env["account.tax"].create(
            self._ostax_tax_vals(name="Catalog 0% sale", amount=0.0)
        )
        # type_tax_use defaults to "sale" via _ostax_tax_vals
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
        ) as m:
            m.return_value = _empty_calc_result()
            sale_tax.compute_all(100.0, partner=self.us_partner)
        m.assert_called_once()


@tagged("post_install", "-at_install")
class TestBatchEngineInboundMoveBypass(OstaxTestCase):
    """Batch-engine path (Odoo 18+) — inbound moves (``in_invoice`` /
    ``in_refund``) must bypass the engine when use-tax accrual is OFF
    (the default)."""

    def setUp(self) -> None:
        super().setUp()
        self.company.ostax_accrue_use_tax = False
        self.vendor = self.env["res.partner"].create({
            "name": "US Vendor at MN address",
            "country_id": self.us_country.id,
            "zip": "55401",
        })

    def test_inbound_move_does_not_engage_engine(self) -> None:
        if not _HAS_BATCH_ENGINE:
            self.skipTest("Batch tax engine only exists on Odoo 18+")
        Tax = self.env["account.tax"]

        class _FakeMove:
            move_type = "in_invoice"

        class _FakeLine:
            _name = "account.move.line"
            move_id = _FakeMove()

        base_line = {
            "partner_id": self.vendor,
            "currency_id": self.vendor.currency_id or self.env.company.currency_id,
            "price_unit": 100.0,
            "quantity": 1.0,
            "discount": 0.0,
            "product_id": False,
            "tax_ids": Tax,
            "record": _FakeLine(),
        }
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            Tax._ostax_inject_into_base_line(base_line, self.company)
        m.assert_not_called()

    def test_outbound_move_still_engages(self) -> None:
        """Sanity: an out_invoice with the same shape DOES engage."""
        if not _HAS_BATCH_ENGINE:
            self.skipTest("Batch tax engine only exists on Odoo 18+")
        Tax = self.env["account.tax"]

        class _FakeMove:
            move_type = "out_invoice"

        class _FakeLine:
            _name = "account.move.line"
            move_id = _FakeMove()

        base_line = {
            "partner_id": self.vendor,
            "currency_id": self.vendor.currency_id or self.env.company.currency_id,
            "price_unit": 100.0,
            "quantity": 1.0,
            "discount": 0.0,
            "product_id": False,
            "tax_ids": Tax,
            "record": _FakeLine(),
        }
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_empty_calc_result(),
        ) as m:
            Tax._ostax_inject_into_base_line(base_line, self.company)
        # out_invoice → engine engages
        m.assert_called_once()


def _empty_calc_result():
    """Return a mock calc result with one empty line (no jurisdictions).

    The bypass tests don't care about the response shape — they just
    care whether the engine got called. Using an empty-jurisdiction
    response means even the "engine engaged" path doesn't try to
    materialize synthetic taxes, keeping these tests minimal.
    """
    from unittest.mock import MagicMock
    line = MagicMock()
    line.jurisdictions = []
    line.tax = 0
    result = MagicMock()
    result.lines = [line]
    return result
