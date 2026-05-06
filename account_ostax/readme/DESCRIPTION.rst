Replace Odoo's static US sales-tax rate tables with destination-based
calculation against an OpenSalesTax engine instance. The connector
overrides ``account.tax.compute_all`` to call the engine for US
partners with a valid 5-digit ZIP, returning the per-jurisdiction
breakdown (state / county / city / district) on every sales order,
invoice, POS order, vendor bill, and refund.

The engine is a self-hostable Python service maintained by the same
author. No SaaS, no per-transaction fees, no data leaves your
infrastructure.

This module is the free, self-hostable alternative to Avalara on
Odoo Community Edition. For Enterprise users, it can coexist with
the proprietary Avalara module on a per-fiscal-position basis.
