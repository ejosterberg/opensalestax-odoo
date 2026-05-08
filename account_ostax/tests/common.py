# SPDX-License-Identifier: LGPL-3.0-or-later
"""Shared test fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class OstaxTestCase(TransactionCase):
    """Base class with the company configured for OST + a mocked SDK client."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write(
            {
                "ostax_enabled": True,
                "ostax_api_url": "http://test-engine.local:8080",
                "ostax_api_key": False,
                "ostax_cache_ttl_hours": 24,
                "ostax_fail_soft": True,
            }
        )
        cls.us_country = cls.env.ref("base.us")

    def setUp(self) -> None:
        super().setUp()
        # The engine-response cache (v0.1.11) is keyed by an hourly
        # bucket, so identical fixtures across tests within the same
        # hour would let the second test get a cache hit and break
        # ``assert_called_once`` style mocks. Clear before every test
        # so each one sees a cold cache. ``clear_cache`` (singular)
        # was introduced in Odoo 17; 16 only has ``clear_caches``
        # (plural).
        registry = self.env.registry
        if hasattr(registry, "clear_cache"):
            registry.clear_cache()
        else:
            registry.clear_caches()

    @staticmethod
    def _patch_health(status: str = "ok", version: str = "0.54.1") -> object:
        """Return a context manager that patches OpenSalesTaxClient.health()."""
        return patch(
            "opensalestax.OpenSalesTaxClient.health",
            return_value=MagicMock(
                status=status,
                version=version,
                database_connected=True,
            ),
        )

    def _ostax_get_or_make_liability_account(self):
        """Return a usable liability ``account.account`` for the company.

        Cross-version: Odoo 16 uses ``user_type_id`` (Many2one to
        ``account.account.type``); 17+ uses ``account_type``
        (Selection). Odoo 18+ also dropped ``company_id`` (single
        company) in favor of ``company_ids`` (Many2many shared
        accounts). Search before create to avoid the field-shape
        differences entirely.
        """
        Account = self.env["account.account"]
        # Try Odoo 17+ shape first (account_type selection).
        if "account_type" in Account._fields:
            domain = [
                ("account_type", "in",
                 ["liability_current", "liability_payable", "liability_non_current"]),
            ]
        else:
            # Odoo 16: filter via user_type_id.type
            domain = [("user_type_id.type", "=", "liability")]
        existing = Account.search(domain, limit=1)
        if existing:
            return existing
        # No chart installed → create one with version-appropriate vals.
        # Cross-version-safe vals dict:
        vals = {
            "name": "OST Test Liability",
            "code": "OSTLIAB",
        }
        if "account_type" in Account._fields:
            vals["account_type"] = "liability_current"
        else:
            # Odoo 16 needs user_type_id pointing at any liability type
            uti = self.env["account.account.type"].search(
                [("type", "=", "liability")], limit=1
            )
            if uti:
                vals["user_type_id"] = uti.id
        # company_id (16/17) vs company_ids (18+)
        if "company_id" in Account._fields:
            vals["company_id"] = self.company.id
        elif "company_ids" in Account._fields:
            vals["company_ids"] = [(4, self.company.id)]
        return Account.create(vals)

    def _ostax_tax_vals(self, *, name: str, amount: float) -> dict:
        """Cross-version-safe vals dict for account.tax.create().

        Odoo 16 added a NOT NULL constraint on country_id; later versions
        keep the field optional. We always set it to US (engine is
        US-only) so the same dict works on all four version branches.
        """
        Tax = self.env["account.tax"]
        vals = {
            "name": name,
            "amount": amount,
            "amount_type": "percent",
            "type_tax_use": "sale",
            "company_id": self.company.id,
        }
        if "country_id" in Tax._fields:
            us = self.env.ref("base.us", raise_if_not_found=False)
            if us:
                vals["country_id"] = us.id
        return vals
