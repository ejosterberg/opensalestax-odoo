# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.1.13 + v0.1.14 — per-product and per-category OST tax-category mapping."""

from __future__ import annotations

from odoo.tests.common import tagged

from .common import OstaxTestCase


@tagged("post_install", "-at_install")
class TestProductCategory(OstaxTestCase):
    """Verify ``product.template.ostax_category`` (v0.1.13) flows
    into the payload sent to the engine."""

    def setUp(self) -> None:
        super().setUp()
        self.Tax = self.env["account.tax"]

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


@tagged("post_install", "-at_install")
class TestProductCategoryInheritance(OstaxTestCase):
    """v0.1.14 — ``product.category.ostax_category`` provides a
    default that products inherit; the lookup walks up
    ``parent_id`` until a value is found, then falls back to
    ``"general"``. Per-product overrides on the template still win."""

    def setUp(self) -> None:
        super().setUp()
        self.Tax = self.env["account.tax"]
        Cat = self.env["product.category"]
        # Build a 3-deep tree:  Apparel(clothing) → Tops(unset) → T-Shirts(unset)
        self.cat_apparel = Cat.create({
            "name": "OST Test Apparel",
            "ostax_category": "clothing",
        })
        self.cat_tops = Cat.create({
            "name": "OST Test Tops",
            "parent_id": self.cat_apparel.id,
        })
        self.cat_tshirts = Cat.create({
            "name": "OST Test T-Shirts",
            "parent_id": self.cat_tops.id,
        })

    def test_category_field_defaults_to_unset(self) -> None:
        cat = self.env["product.category"].create({"name": "Bare"})
        self.assertFalse(cat.ostax_category)

    def test_product_inherits_directly_from_category(self) -> None:
        product = self.env["product.product"].create({
            "name": "Sock",
            "categ_id": self.cat_apparel.id,
        })
        # Template field unset → falls through to category
        product.product_tmpl_id.ostax_category = False
        self.assertEqual(self.Tax._ostax_category_for(product), "clothing")

    def test_product_walks_up_parent_chain(self) -> None:
        product = self.env["product.product"].create({
            "name": "Tee",
            "categ_id": self.cat_tshirts.id,
        })
        # Template, immediate category, AND its parent are all unset —
        # only the grandparent (Apparel) carries "clothing".
        product.product_tmpl_id.ostax_category = False
        self.assertEqual(self.Tax._ostax_category_for(product), "clothing")

    def test_product_template_override_wins_over_category(self) -> None:
        product = self.env["product.product"].create({
            "name": "Premium tee",
            "categ_id": self.cat_apparel.id,
        })
        product.product_tmpl_id.ostax_category = "digital_goods"
        # Per-product override beats the category default
        self.assertEqual(self.Tax._ostax_category_for(product), "digital_goods")

    def test_intermediate_category_value_wins_over_root(self) -> None:
        """If a mid-tree category has a value, it wins over an
        ancestor's value (closest-ancestor-wins)."""
        self.cat_tops.ostax_category = "groceries"  # nonsensical but tests precedence
        product = self.env["product.product"].create({
            "name": "Mid-tree product",
            "categ_id": self.cat_tshirts.id,
        })
        product.product_tmpl_id.ostax_category = False
        self.assertEqual(self.Tax._ostax_category_for(product), "groceries")

    def test_unset_chain_falls_back_to_general(self) -> None:
        cat = self.env["product.category"].create({"name": "All-unset"})
        product = self.env["product.product"].create({
            "name": "Plain product",
            "categ_id": cat.id,
        })
        product.product_tmpl_id.ostax_category = False
        self.assertEqual(self.Tax._ostax_category_for(product), "general")
