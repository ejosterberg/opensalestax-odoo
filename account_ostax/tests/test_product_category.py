# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.1.13 — per-product OST tax-category mapping."""

from __future__ import annotations

from odoo.tests.common import tagged

from .common import OstaxTestCase


@tagged("post_install", "-at_install")
class TestProductCategory(OstaxTestCase):
    """Verify ``product.template.ostax_category`` flows into the
    payload sent to the engine."""

    def setUp(self) -> None:
        super().setUp()
        Tax = self.env["account.tax"]
        self.Tax = Tax

    def test_field_defaults_to_general(self) -> None:
        product = self.env["product.product"].create({"name": "Plain widget"})
        self.assertEqual(product.product_tmpl_id.ostax_category, "general")

    def test_field_can_be_set_to_clothing(self) -> None:
        product = self.env["product.product"].create(
            {"name": "T-shirt"}
        )
        product.product_tmpl_id.ostax_category = "clothing"
        self.assertEqual(product.product_tmpl_id.ostax_category, "clothing")

    def test_helper_reads_template_field(self) -> None:
        product = self.env["product.product"].create(
            {"name": "Apple"}
        )
        product.product_tmpl_id.ostax_category = "groceries"
        self.assertEqual(self.Tax._ostax_category_for(product), "groceries")

    def test_helper_returns_general_for_unset(self) -> None:
        product = self.env["product.product"].create(
            {"name": "Generic"}
        )
        # default is "general", but the helper handles falsy too — clear it
        product.product_tmpl_id.ostax_category = False
        self.assertEqual(self.Tax._ostax_category_for(product), "general")

    def test_helper_returns_general_for_none(self) -> None:
        self.assertEqual(self.Tax._ostax_category_for(None), "general")

    def test_helper_accepts_template_directly(self) -> None:
        # Defensive: callers passing a product.template (not a variant)
        # should still work.
        template = self.env["product.template"].create(
            {"name": "Direct-template-arg"}
        )
        template.ostax_category = "digital_goods"
        self.assertEqual(self.Tax._ostax_category_for(template), "digital_goods")

    def test_selection_options_match_engine(self) -> None:
        """Engine v1 LineItemRequest accepts these category strings.

        If this test starts failing it means the engine added or
        removed a category and the addon needs to follow.
        """
        Template = self.env["product.template"]
        field = Template._fields["ostax_category"]
        keys = {key for key, _label in field.selection}
        expected = {
            "general",
            "clothing",
            "groceries",
            "prescription_drugs",
            "prepared_food",
            "digital_goods",
        }
        self.assertEqual(keys, expected)
