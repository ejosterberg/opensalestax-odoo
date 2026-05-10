# SPDX-License-Identifier: LGPL-3.0-or-later OR AGPL-3.0-or-later
"""Per-line OST escape hatch (v0.3.5).

Adds an ``ostax_skip`` Boolean to ``account.move.line``. When set
on a line, the OST connector bypasses that specific line and lets
Odoo's standard catalog-rate handling apply.

Use case — rare but real:

* The engine returns a wrong rate for one specific line (e.g. a
  jurisdictional edge case the engine hasn't been told about yet).
* A merchant wants to manually override one line on a one-off
  invoice without disabling OST for the entire move.
* Bringing in legacy data with pre-computed taxes that shouldn't
  be re-routed through the engine.

Default ``False`` (engine engages normally). Existing v0.3.4
users see no behavior change on upgrade.
"""

from __future__ import annotations

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ostax_skip = fields.Boolean(
        string="Skip OpenSalesTax",
        default=False,
        copy=False,
        help=(
            "When checked, the OpenSalesTax connector will bypass "
            "this specific line and let Odoo's standard catalog-rate "
            "handling apply. Use as an escape hatch when the engine "
            "returns a wrong rate for one specific line, or to bring "
            "in legacy data with pre-computed taxes that shouldn't be "
            "re-routed through the engine. Most lines should leave "
            "this off."
        ),
    )
