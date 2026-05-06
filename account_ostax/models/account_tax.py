# SPDX-License-Identifier: LGPL-3.0-or-later
"""account.tax override — the canonical OpenSalesTax integration point.

The Phase 4 implementation overrides ``compute_all`` to engage the
engine for US partners with a valid 5-digit ZIP, falling back to
the standard catalog calculation otherwise. The Phase 9 cache
wraps the rate lookup in tools.ormcache.

This stub exists so the module installs cleanly through Phases 1-3.
The override body lands in Phase 4.
"""

from odoo import models


class AccountTax(models.Model):
    _inherit = "account.tax"

    # Phase 4 will add:
    #
    #   def compute_all(self, price_unit, currency=None, quantity=1.0,
    #                   product=None, partner=None, is_refund=False, **kw):
    #       company = self.company_id or self.env.company
    #       if not self._ostax_should_engage(company, partner):
    #           return super().compute_all(price_unit, currency=currency,
    #                                       quantity=quantity, product=product,
    #                                       partner=partner, is_refund=is_refund,
    #                                       **kw)
    #       return self._ostax_compute_all(price_unit, currency=currency,
    #                                       quantity=quantity, product=product,
    #                                       partner=partner, is_refund=is_refund,
    #                                       **kw)
