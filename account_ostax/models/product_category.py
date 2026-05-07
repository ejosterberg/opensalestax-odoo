# SPDX-License-Identifier: LGPL-3.0-or-later
"""Category-level OST tax-category default.

Adds an ``ostax_category`` field to ``product.category`` so a
merchant can mark e.g. the "Apparel" internal category as
``clothing`` once, and every product under it inherits that
default. Per-product overrides on ``product.template.ostax_category``
still win when set.

Field intentionally has no default — an unset category leaves the
decision to the parent category, then to the product, then to the
"general" fallback in ``account.tax._ostax_category_for``.
"""

from __future__ import annotations

from odoo import fields, models

from .product_template import OSTAX_CATEGORY_SELECTION


class ProductCategory(models.Model):
    _inherit = "product.category"

    ostax_category = fields.Selection(
        selection=OSTAX_CATEGORY_SELECTION,
        string="OST tax category default",
        help=(
            "Default OST tax category for products in this category. "
            "Per-product values on the product itself override this. "
            "If unset, the parent category's value is used (walked "
            "up to the root); ultimately falls back to 'General'."
        ),
    )
