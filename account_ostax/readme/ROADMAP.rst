v0.1.0-alpha (shipped 2026-05-06)
==================================

* Module installs on Odoo 18 + Postgres 16
* Per-company settings + Test Connection action
* `compute_all` override (works for direct calls; see Known
  Limitations below)
* Per-jurisdiction synthetic `account.tax` materialization
* Audit-trail breakdown JSON captured on `account.move._post()`
* Customer exemption certificates (short-circuit to zero tax)
* Opt-in admin debug log
* Multi-company isolation

v0.1.0 stable (next)
====================

* **Hook the Odoo 18 batch tax engine** so invoice / SO tax
  computation actually uses OST (not just the captured audit
  JSON). Targets ``AccountTax._add_tax_details_in_base_lines``
  driven from ``account.move._get_rounded_base_and_tax_lines``.
* Per-branch CI matrix passes (test-18.0.yml is in place)
* Tag and publish to PyPI as ``odoo-addon-account-ostax``

v0.2
====

* 17.0 and 16.0 branch backports
* OCA upstream submission to ``OCA/account-fiscal-rule`` (relicense
  to AGPL-3 dual)
* Vendor-side use-tax accrual (purchase orders, vendor bills)
* POS live-quote (JS-side round-trip on each line-add for accurate
  cashier preview)
* Cache (24h sliding TTL via ormcache)
* Bulk recompute wizard for historical orders after rate-table
  changes
* Per-product OST category mapping
* Engine version stamp on captured breakdown JSON
* Odoo 19.0 branch (after 19 GAs ~Oct 2026)
* Enterprise compatibility (coexist with the proprietary Avalara
  module on a per-fiscal-position basis)

Out of scope (per project constitution)
=======================================

* Tax filing / remittance (engine constitution §13)
* Address validation
* Non-USD currency (engine constitution §5)
* Modifying upstream Odoo source
