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
