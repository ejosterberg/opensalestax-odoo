# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.1.15 — defensive bypass on vendor bills / purchase taxes.

Until v0.2 ships proper use-tax accrual at the buyer's location, the
addon must NOT call the engine on vendor bills (move_type starts
with ``in_``) or with purchase-typed catalog taxes — those produce
nonsensical numbers because the engine call uses the partner's ZIP,
which on a vendor bill is the vendor's address rather than the
buyer's. Falling through to Odoo's standard catalog rates is the
correct behavior until proper use-tax handling lands.
"""

from __future__ import annotations

from datetime import date
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
    through to super() instead of engaging the engine."""

    def setUp(self) -> None:
        super().setUp()
        self.us_partner = self.env["res.partner"].create({
            "name": "US Vendor",
            "country_id": self.us_country.id,
            "zip": "55401",
        })
        self.purchase_tax = self.env["account.tax"].create(
            self._ostax_tax_vals(name="Vendor 7% purchase tax", amount=7.0)
        )
        self.purchase_tax.type_tax_use = "purchase"

    def test_purchase_tax_bypasses_engine(self) -> None:
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
    ``in_refund``) must bypass the engine even when the partner
    happens to be US-located."""

    def setUp(self) -> None:
        super().setUp()
        self.vendor = self.env["res.partner"].create({
            "name": "US Vendor at MN address",
            "country_id": self.us_country.id,
            "zip": "55401",
        })

    def test_inbound_move_does_not_engage_engine(self) -> None:
        if not _HAS_BATCH_ENGINE:
            self.skipTest("Batch tax engine only exists on Odoo 18+")
        Tax = self.env["account.tax"]

        # Build a minimal vendor bill base_line that LOOKS like one —
        # we exercise the gate inside ``_ostax_inject_into_base_line``
        # directly to keep the test focused.
        line_record = self.env["account.move.line"]  # empty recordset is fine
        # Simulate an account.move.line bound to an inbound move by
        # constructing a tiny stand-in object that quacks like one.
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
