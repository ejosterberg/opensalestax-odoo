# SPDX-License-Identifier: LGPL-3.0-or-later OR AGPL-3.0-or-later
"""Per-product OST tax-category override.

Adds an ``ostax_category`` field to ``product.template`` so a
merchant can mark e.g. apparel as ``clothing`` or e-books as
``digital_goods``. The engine applies per-state taxability rules
based on the category — Minnesota exempts clothing, New York
taxes prepared food differently than groceries, etc.

The selection mirrors the engine's canonical category list (see
``OpenSalesTax`` engine v1 ``LineItemRequest.category``):

* general          (default)
* clothing
* groceries
* prescription_drugs
* prepared_food
* digital_goods

Lookup precedence in ``account.tax._ostax_category_for``:

1. ``product.product_tmpl_id.ostax_category`` if set
2. fall back to ``"general"``
"""

from __future__ import annotations

from odoo import fields, models


OSTAX_CATEGORY_SELECTION = [
    ("general", "General (default)"),
    ("clothing", "Clothing"),
    ("groceries", "Groceries"),
    ("prescription_drugs", "Prescription drugs"),
    ("prepared_food", "Prepared food"),
    ("digital_goods", "Digital goods"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ostax_category = fields.Selection(
        selection=OSTAX_CATEGORY_SELECTION,
        string="OST tax category",
        default="general",
        help=(
            "Per-state taxability category sent to the OpenSalesTax "
            "engine for this product. Choose 'Clothing', 'Groceries', "
            "etc. when the product is one of the engine's special "
            "categories — taxability rules vary by destination state. "
            "Leave at 'General' for ordinary tangible goods."
        ),
    )
