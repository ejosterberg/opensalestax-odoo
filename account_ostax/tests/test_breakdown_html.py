# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.3.4 — breakdown JSON → HTML table conversion."""

from __future__ import annotations

import json

from odoo.tests.common import TransactionCase, tagged

from .._breakdown_html import breakdown_to_html  # noqa: F401 (loaded via models pkg)


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
        # Must escape the input to avoid XSS via tampered data
        self.assertIn("&lt;", result.replace("<pre>", ""))  # nothing to escape here
        self.assertIn("not valid json", result)

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
        ``ostax_breakdown_pretty`` field renders without error."""
        Move = self.env["account.move"]
        # We don't need to post — just check the field computes from
        # whatever's in ``ostax_breakdown``. Use a minimal vals dict.
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
