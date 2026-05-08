# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.3.0 — per-state nexus filter on res.company.

When ``ostax_nexus_state_ids`` is set, the connector only engages
the engine for customers whose ``state_id`` is in that set.
Out-of-state US customers fall through to Odoo's standard
catalog-rate handling. Empty (default) = engage in all US states.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from odoo.tests.common import tagged

from .common import OstaxTestCase


def _empty_calc_result():
    line = MagicMock()
    line.jurisdictions = []
    line.tax = 0
    result = MagicMock()
    result.lines = [line]
    return result


@tagged("post_install", "-at_install")
class TestNexusStateFilter(OstaxTestCase):
    """Per-state nexus list controls which US customers engage the engine."""

    def setUp(self) -> None:
        super().setUp()
        Country = self.env["res.country"]
        State = self.env["res.country.state"]
        us = self.env.ref("base.us")
        # MN + WI: pretend our merchant has nexus only here
        self.mn = State.search([
            ("country_id", "=", us.id), ("code", "=", "MN")
        ], limit=1)
        self.wi = State.search([
            ("country_id", "=", us.id), ("code", "=", "WI")
        ], limit=1)
        # CA: out of nexus
        self.ca = State.search([
            ("country_id", "=", us.id), ("code", "=", "CA")
        ], limit=1)
        # Skip if any US state isn't seeded (some minimal images don't have all)
        if not (self.mn and self.wi and self.ca):
            self.skipTest("US states not fully seeded in this Odoo image")

        self.tax = self.env["account.tax"].create(
            self._ostax_tax_vals(name="Catalog 0%", amount=0.0)
        )

    def _make_partner(self, state):
        return self.env["res.partner"].create({
            "name": f"Customer in {state.code}",
            "country_id": self.env.ref("base.us").id,
            "state_id": state.id,
            "zip": "55401" if state.code == "MN" else (
                "53201" if state.code == "WI" else "94016"
            ),
        })

    def test_no_nexus_set_engages_for_all_us_states(self) -> None:
        self.company.ostax_nexus_state_ids = [(5, 0, 0)]
        for state in (self.mn, self.wi, self.ca):
            partner = self._make_partner(state)
            with patch(
                "opensalestax.OpenSalesTaxClient.calculate",
                return_value=_empty_calc_result(),
            ) as m:
                self.tax.compute_all(100.0, partner=partner)
            self.assertEqual(m.call_count, 1,
                f"Empty nexus list should engage in {state.code}")

    def test_in_nexus_state_engages(self) -> None:
        self.company.ostax_nexus_state_ids = [(6, 0, [self.mn.id, self.wi.id])]
        partner_mn = self._make_partner(self.mn)
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_empty_calc_result(),
        ) as m:
            self.tax.compute_all(100.0, partner=partner_mn)
        m.assert_called_once()

    def test_out_of_nexus_state_bypasses(self) -> None:
        self.company.ostax_nexus_state_ids = [(6, 0, [self.mn.id, self.wi.id])]
        partner_ca = self._make_partner(self.ca)
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.tax.compute_all(100.0, partner=partner_ca)
        m.assert_not_called()

    def test_partner_with_no_state_bypasses_when_nexus_set(self) -> None:
        """A US customer with a valid ZIP but no state record. With
        nexus filtering on, we can't confirm the customer is in
        nexus → bypass (conservative)."""
        self.company.ostax_nexus_state_ids = [(6, 0, [self.mn.id])]
        partner = self.env["res.partner"].create({
            "name": "Stateless US customer",
            "country_id": self.env.ref("base.us").id,
            "zip": "55401",
            "state_id": False,
        })
        with patch("opensalestax.OpenSalesTaxClient.calculate") as m:
            self.tax.compute_all(100.0, partner=partner)
        m.assert_not_called()
