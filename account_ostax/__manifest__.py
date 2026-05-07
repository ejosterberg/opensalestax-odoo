# SPDX-License-Identifier: LGPL-3.0-or-later
{
    "name": "OpenSalesTax — US Sales Tax via OST API",
    "summary": (
        "Replace static US sales-tax rates with destination-based "
        "lookups against an OpenSalesTax engine instance."
    ),
    "version": "18.0.0.1.9",
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
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "development_status": "Alpha",
}
