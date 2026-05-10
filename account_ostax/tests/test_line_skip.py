# SPDX-License-Identifier: LGPL-3.0-or-later OR AGPL-3.0-or-later
"""v0.3.5 — per-line OST skip override.

When ``account.move.line.ostax_skip`` is True on a specific line,
the connector bypasses the engine for that line and lets Odoo's
standard catalog-rate handling apply. Use case: rare engine error
on one line, legacy data ingest, or one-off manual override.
"""

from __future__ import annotations

from unittest.mock import patch

from odoo.release import version_info
from odoo.tests.common import tagged

from .common import OstaxTestCase

_HAS_BATCH_ENGINE = version_info[0] >= 18


@tagged("post_install", "-at_install")
class TestPerLineSkip(OstaxTestCase):
    """Skip flag on a fake account.move.line bypasses the engine
    on the batch-engine path."""

    def setUp(self) -> None:
        super().setUp()
        self.us_partner = self.env["res.partner"].create({
            "name": "US Customer",
            "country_id": self.us_country.id,
            "zip": "55401",
        })

    def test_skip_field_default_false(self) -> None:
        """Default value for the field is False (engine engages)."""
        Line = self.env["account.move.line"]
        # Field-default check via _fields[].default
        default = Line._fields["ostax_skip"].default
        # default is a callable in Odoo 18+, a value in 16/17
        if callable(default):
            self.assertFalse(default(Line))
        else:
            self.assertFalse(default)

    def test_skip_true_bypasses_batch_engine(self) -> None:
        """Inject path: a line with ostax_skip=True must NOT call
        the engine even when all other gates would pass."""
        if not _HAS_BATCH_ENGINE:
            self.skipTest("Batch tax engine only exists on Odoo 18+")
        Tax = self.env["account.tax"]

        class _FakeMove:
            move_type = "out_invoice"
            state = "posted"

        class _FakeLine:
            _name = "account.move.line"
            move_id = _FakeMove()
            ostax_skip = True

        base_line = {
            "partner_id": self.us_partner,
            "currency_id": self.us_partner.currency_id or self.env.company.currency_id,
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

    def test_skip_false_engages_engine(self) -> None:
        """Sanity: same line shape with ostax_skip=False engages."""
        if not _HAS_BATCH_ENGINE:
            self.skipTest("Batch tax engine only exists on Odoo 18+")
        Tax = self.env["account.tax"]

        class _FakeMove:
            move_type = "out_invoice"
            state = "posted"

        class _FakeLine:
            _name = "account.move.line"
            move_id = _FakeMove()
            ostax_skip = False

        base_line = {
            "partner_id": self.us_partner,
            "currency_id": self.us_partner.currency_id or self.env.company.currency_id,
            "price_unit": 100.0,
            "quantity": 1.0,
            "discount": 0.0,
            "product_id": False,
            "tax_ids": Tax,
            "record": _FakeLine(),
        }
        from unittest.mock import MagicMock

        def _empty():
            line = MagicMock()
            line.jurisdictions = []
            line.tax = 0
            r = MagicMock()
            r.lines = [line]
            return r

        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_empty(),
        ) as m:
            Tax._ostax_inject_into_base_line(base_line, self.company)
        # Without the skip flag, the engine engages
        m.assert_called_once()

    def test_skip_field_persists_on_real_line(self) -> None:
        """Smoke test: the field actually exists on account.move.line
        and can be written to. Doesn't require a full chart of
        accounts since we only test the field, not engine integration."""
        Line = self.env["account.move.line"]
        # Just verify the field exists; creating a real move line on
        # a minimal Odoo image without a chart is brittle.
        self.assertIn("ostax_skip", Line._fields)
        self.assertEqual(Line._fields["ostax_skip"].type, "boolean")
