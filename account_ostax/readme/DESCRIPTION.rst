Replace Odoo's static US sales-tax rate tables with destination-based
calculation against an OpenSalesTax engine instance. The connector
hooks Odoo's tax pipeline (the new batch tax engine on 18+, legacy
``compute_all`` on 16/17) to call the engine for US customers with a
valid 5-digit ZIP, returning the per-jurisdiction breakdown (state /
county / city / district) on every sales order, customer invoice,
credit note, and POS order.

The engine is a self-hostable Python service maintained by the same
author. No SaaS, no per-transaction fees, no data leaves your
infrastructure.

This module is the free, self-hostable alternative to Avalara on
Odoo Community Edition. For Enterprise users, it is designed to
coexist with the proprietary Avalara module on a per-fiscal-position
basis.

Vendor bills and other inbound moves currently bypass the connector;
proper use-tax accrual at the buyer's location is v0.2 work.
