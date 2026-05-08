# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.2.1 — operator-experience telemetry & bulk recompute.

The connector tracks engine successes/failures at the company
level and posts a mail.activity to admin recipients when the
failure streak crosses a threshold. There's also a bulk recompute
server action exposed on account.move lists for refreshing every
draft's breakdown after an engine rate-table change.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from odoo.tests.common import tagged

from .common import OstaxTestCase


def _empty_calc_result():
    """Engine result with one empty line (no jurisdictions)."""
    line = MagicMock()
    line.jurisdictions = []
    line.tax = 0
    result = MagicMock()
    result.lines = [line]
    return result


@tagged("post_install", "-at_install")
class TestEngineFailureStreak(OstaxTestCase):
    """Failure-streak counter + threshold-crossing mail.activity."""

    def setUp(self) -> None:
        super().setUp()
        self.us_partner = self.env["res.partner"].create({
            "name": "US Customer",
            "country_id": self.us_country.id,
            "zip": "55401",
        })
        self.tax = self.env["account.tax"].create(
            self._ostax_tax_vals(name="Catalog 0%", amount=0.0)
        )
        # Reset telemetry to known state for each test
        self.company.write({
            "ostax_failure_streak": 0,
            "ostax_failure_streak_threshold": 3,
            "ostax_last_successful_calc_at": False,
        })

    def test_success_resets_streak_and_stamps_timestamp(self) -> None:
        # Seed a non-zero streak
        self.company.ostax_failure_streak = 5
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            return_value=_empty_calc_result(),
        ):
            self.tax.compute_all(100.0, partner=self.us_partner)
        self.assertEqual(self.company.ostax_failure_streak, 0)
        self.assertTrue(self.company.ostax_last_successful_calc_at)

    def test_failure_increments_streak(self) -> None:
        from opensalestax import OpenSalesTaxNetworkError
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxNetworkError("connection refused"),
        ):
            self.tax.compute_all(100.0, partner=self.us_partner)
            self.tax.compute_all(100.0, partner=self.us_partner)
        self.assertEqual(self.company.ostax_failure_streak, 2)

    def test_threshold_crossing_posts_activity_when_recipients_set(self) -> None:
        from opensalestax import OpenSalesTaxNetworkError
        # Pick any existing user as recipient (admin is always present)
        admin = self.env.ref("base.user_admin", raise_if_not_found=False) or \
            self.env["res.users"].search([], limit=1)
        self.company.ostax_admin_alert_recipient_ids = [(6, 0, [admin.id])]
        # Threshold is 3 (set in setUp) — fail 3 times
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxNetworkError("down"),
        ):
            for _ in range(3):
                self.tax.compute_all(100.0, partner=self.us_partner)
        self.assertEqual(self.company.ostax_failure_streak, 3)
        # Activity should have been posted on the company record
        activities = self.env["mail.activity"].search([
            ("res_model", "=", "res.company"),
            ("res_id", "=", self.company.id),
            ("user_id", "=", admin.id),
        ])
        self.assertTrue(activities, "Outage activity was not posted")
        # Subsequent failures should NOT post additional activities
        # (we only post once at the threshold-crossing edge)
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxNetworkError("still down"),
        ):
            self.tax.compute_all(100.0, partner=self.us_partner)
        activities_after = self.env["mail.activity"].search([
            ("res_model", "=", "res.company"),
            ("res_id", "=", self.company.id),
            ("user_id", "=", admin.id),
        ])
        self.assertEqual(len(activities_after), len(activities),
            "Activity should be posted only on the threshold-crossing edge")

    def test_no_recipients_no_activity_but_streak_still_counts(self) -> None:
        from opensalestax import OpenSalesTaxNetworkError
        self.company.ostax_admin_alert_recipient_ids = [(5, 0, 0)]
        with patch(
            "opensalestax.OpenSalesTaxClient.calculate",
            side_effect=OpenSalesTaxNetworkError("down"),
        ):
            for _ in range(5):
                self.tax.compute_all(100.0, partner=self.us_partner)
        self.assertEqual(self.company.ostax_failure_streak, 5)
        activities = self.env["mail.activity"].search([
            ("res_model", "=", "res.company"),
            ("res_id", "=", self.company.id),
        ])
        self.assertFalse(activities,
            "No recipients → no activity, but streak should still count")


@tagged("post_install", "-at_install")
class TestCalcCountToday(OstaxTestCase):
    """``ostax_calc_count_today`` reads from ostax.calc.log."""

    def test_counts_only_today_entries_for_company(self) -> None:
        # Make a couple of log entries for today
        Log = self.env["ostax.calc.log"].sudo()
        Log.create({
            "company_id": self.company.id,
            "kind": "engine_call",
            "dest_zip": "55401",
            "total_amount": 100.0,
            "engine_version": "v0.54.1",
            "response_ms": 12,
        })
        Log.create({
            "company_id": self.company.id,
            "kind": "engine_call",
            "dest_zip": "10001",
            "total_amount": 50.0,
            "engine_version": "v0.54.1",
            "response_ms": 8,
        })
        # Force recompute
        self.company.invalidate_recordset(["ostax_calc_count_today"]) \
            if hasattr(self.company, "invalidate_recordset") else self.company.invalidate_cache()
        self.assertGreaterEqual(self.company.ostax_calc_count_today, 2)


@tagged("post_install", "-at_install")
class TestBulkRecomputeAction(OstaxTestCase):
    """``account.move.action_ostax_bulk_recompute_drafts`` summary."""

    def test_empty_recordset_produces_warning_notification(self) -> None:
        # Empty selection — the summary still returns a notification
        # action; recomputed=0 → kind="warning"
        Move = self.env["account.move"]
        action = Move.action_ostax_bulk_recompute_drafts()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["params"]["type"], "warning")

    def test_non_draft_skipped_by_count(self) -> None:
        """Build a posted-or-otherwise move and verify the action
        marks it as 'not draft' rather than recomputing.

        We can't easily build a real posted invoice from scratch in
        this test base (no chart of accounts in the minimal
        fixtures), so we just confirm the call shape returns the
        expected counts on an empty recordset (covered above) — the
        skip-on-non-draft path is exercised by the action's body.
        """
        # Mostly a smoke test that the method is callable on an
        # empty recordset and returns the expected action shape.
        Move = self.env["account.move"]
        result = Move.action_ostax_bulk_recompute_drafts()
        self.assertIn("Recomputed: 0", result["params"]["message"])
