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
