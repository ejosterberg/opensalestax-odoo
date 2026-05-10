# SPDX-License-Identifier: LGPL-3.0-or-later OR AGPL-3.0-or-later
{
    "name": "OpenSalesTax — US Sales Tax via OST API",
    "summary": (
        "Replace static US sales-tax rates with destination-based "
        "lookups against an OpenSalesTax engine instance."
    ),
    "version": "16.0.0.4.1",
    "category": "Accounting/Localizations",
    "website": "https://github.com/ejosterberg/opensalestax-odoo",
    "author": "Eric Osterberg",
    "maintainers": ["ejosterberg"],
    "license": "LGPL-3",
    "depends": [
        "account",
        "sale",
        "purchase",
        "point_of_sale",
    ],
    "external_dependencies": {
        "python": ["opensalestax"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/ostax_cron.xml",
        "data/ostax_actions.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/pos_order_views.xml",
        "views/product_category_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    # v0.4.0 — promoted from Alpha to Beta. The connector has been
    # shipping in production-grade shape for ~weeks across all four
    # Odoo majors (84 unit tests; 23 releases on PyPI; live UX
    # validated). Beta = production-ready, but the API surface may
    # still evolve based on OCA review feedback.
    "development_status": "Beta",
}
