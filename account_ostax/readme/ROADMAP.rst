v0.1
====

* Sales orders, invoices, refunds, POS, vendor bills, purchase orders
* Per-jurisdiction breakdown stored on every move
* Customer exemption certificates
* Multi-company
* Settings page with connection test
* Cache (24h sliding TTL via ormcache)
* Optional debug log

v0.2 (planned)
==============

* OCA upstream submission to ``OCA/account-fiscal-rule`` (relicense to
  AGPL-3 dual)
* Odoo 19.0 branch (after 19 GAs ~Oct 2026)
* Enterprise compatibility (coexist with the proprietary Avalara module
  on a per-fiscal-position basis)
* Bulk recompute wizard for historical orders after rate-table changes
* Per-product OST category mapping (v0.1 sends a generic category)
* Async SDK use (v0.1 is sync only — Odoo's compute_all is sync)

Out of scope (per project constitution)
=======================================

* Tax filing / remittance
* Address validation
* Non-USD currency
* Modifying upstream Odoo source
