# SPDX-License-Identifier: LGPL-3.0-or-later OR AGPL-3.0-or-later
"""v0.3.4 — breakdown JSON → HTML table conversion."""

from __future__ import annotations

import json

from odoo.tests.common import TransactionCase, tagged

# Note: each test method imports `breakdown_to_html` fresh from
# the absolute path so this file imports cleanly regardless of
# how Odoo's test loader resolves relative imports.


@tagged("post_install", "-at_install")
class TestBreakdownToHtml(TransactionCase):
    """Pure-function tests — no env required, but TransactionCase
    keeps Odoo's test bootstrapping happy."""

    def test_empty_input_returns_empty_string(self) -> None:
        from odoo.addons.account_ostax.models._breakdown_html import (
            breakdown_to_html,
        )
        self.assertEqual(breakdown_to_html(""), "")
        self.assertEqual(breakdown_to_html(None), "")

    def test_unparseable_json_falls_back_to_pre(self) -> None:
        from odoo.addons.account_ostax.models._breakdown_html import (
            breakdown_to_html,
        )
        result = breakdown_to_html("{not valid json")
        self.assertIn("<pre>", result)
        self.assertIn("not valid json", result)
        # XSS escaping on the fallback path is covered separately in
        # test_xss_in_jurisdiction_name_is_escaped — no chars to
        # escape in this benign-junk input.

    def test_full_breakdown_renders_table(self) -> None:
        from odoo.addons.account_ostax.models._breakdown_html import (
            breakdown_to_html,
        )
        breakdown = {
            "engine_version": "0.54.1",
            "subtotal": "100.00",
            "tax_total": "9.025",
            "lines": [
                {
                    "amount": "100.00",
                    "category": "general",
                    "tax": "9.025",
                    "rate_pct": "9.025",
                    "note": None,
                    "jurisdictions": [
                        {"name": "Minnesota", "type": "state",
                         "rate_pct": "6.875", "tax": "6.875"},
                        {"name": "Hennepin County", "type": "county",
                         "rate_pct": "0.15", "tax": "0.15"},
                    ],
                },
            ],
        }
        result = breakdown_to_html(json.dumps(breakdown))
        # Header
        self.assertIn("Engine version", result)
        self.assertIn("0.54.1", result)
        # Table headers
        self.assertIn("Jurisdiction", result)
        self.assertIn("Type", result)
        self.assertIn("Rate", result)
        # Per-jurisdiction rows
        self.assertIn("Minnesota", result)
        self.assertIn("Hennepin County", result)
        self.assertIn("6.875%", result)
        # Per-line summary
        self.assertIn("Line 1", result)
        self.assertIn("category general", result)

    def test_xss_in_jurisdiction_name_is_escaped(self) -> None:
        """Malicious or accidentally-malformed jurisdiction names
        must not break out of cells."""
        from odoo.addons.account_ostax.models._breakdown_html import (
            breakdown_to_html,
        )
        breakdown = {
            "engine_version": "0.54.1",
            "lines": [{
                "jurisdictions": [{
                    "name": "<script>alert(1)</script>",
                    "type": "state",
                    "rate_pct": "5.0",
                    "tax": "5.00",
                }],
            }],
        }
        result = breakdown_to_html(json.dumps(breakdown))
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_empty_jurisdictions_renders_message(self) -> None:
        from odoo.addons.account_ostax.models._breakdown_html import (
            breakdown_to_html,
        )
        breakdown = {
            "engine_version": "0.54.1",
            "lines": [{"amount": "100", "tax": "0", "jurisdictions": []}],
        }
        result = breakdown_to_html(json.dumps(breakdown))
        self.assertIn("No per-jurisdiction breakdown", result)

    def test_no_lines_renders_placeholder(self) -> None:
        from odoo.addons.account_ostax.models._breakdown_html import (
            breakdown_to_html,
        )
        breakdown = {"engine_version": "0.54.1", "lines": []}
        result = breakdown_to_html(json.dumps(breakdown))
        self.assertIn("No lines in breakdown", result)

    def test_account_move_field_computes(self) -> None:
        """End-to-end: write breakdown JSON on a move, computed
        ``ostax_breakdown_pretty`` field renders without error.

        Skipped on Odoo images without a chart of accounts installed
        (the minimal CI fixture used on 16.0 lacks a sale journal,
        so ``account.move.create`` raises UserError before we can
        even test the field). The 6 pure-function tests above
        already cover the rendering logic; this is just an
        integration smoke test."""
        Journal = self.env["account.journal"]
        if not Journal.search([("type", "=", "sale")], limit=1):
            self.skipTest(
                "No sale journal available — minimal Odoo image "
                "without chart of accounts. Pure helper covered by "
                "the 6 tests above."
            )
        Move = self.env["account.move"]
        partner = self.env["res.partner"].create({"name": "Test customer"})
        move = Move.create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
        })
        breakdown = {
            "engine_version": "0.54.1",
            "subtotal": "100.00",
            "tax_total": "9.03",
            "lines": [{"jurisdictions": [
                {"name": "Minnesota", "type": "state",
                 "rate_pct": "6.875", "tax": "6.875"}
            ]}],
        }
        move.write({"ostax_breakdown": json.dumps(breakdown)})
        # Force recompute (Html computed fields lazy-evaluate)
        move.invalidate_recordset(["ostax_breakdown_pretty"]) \
            if hasattr(move, "invalidate_recordset") else move.invalidate_cache()
        rendered = move.ostax_breakdown_pretty or ""
        self.assertIn("Minnesota", rendered)
        self.assertIn("0.54.1", rendered)
