Shipped (v0.1.x line)
=====================

* All four Odoo majors supported (16.0 / 17.0 / 18.0 / 19.0); same
  module, branch-per-version per OCA convention
* Odoo 18+ batch tax engine override
  (``AccountTax._add_tax_details_in_base_lines``) using the official
  ``manual_tax_amounts`` injection mechanism
* Odoo 16/17 legacy ``compute_all`` override (the new batch engine
  arrived in 18.0)
* Per-jurisdiction synthetic ``account.tax`` materialization with
  per-type tax groups (State / County / City / District)
* Line-level OST jurisdiction tags persisted on posted invoices
* Audit-trail breakdown JSON captured on ``account.move._post()``
  with engine version stamp
* Customer exemption certificates (short-circuit to zero tax)
* Per-product taxability category on ``product.template``
* Per-category default with parent-walk inheritance on
  ``product.category``
* Per-worker engine-response cache (~1h sliding TTL via
  ``tools.ormcache``)
* Opt-in admin debug log
* Optional 90-day archive cron for unused synthetic taxes
* Multi-company isolation
* Per-branch CI on every push (Test 16.0 / 17.0 / 18.0 / 19.0)
* PyPI Trusted Publishing (OIDC) on tag push
* DCO sign-off enforcement on PRs
* Defensive bypass on vendor bills + purchase taxes (proper use-tax
  accrual is v0.2)

Roadmap
=======

v0.2.x — Vendor-side + operator UX
----------------------------------

* Vendor-bill use-tax accrual at the BUYER's location (replaces the
  v0.1.15 defensive bypass with a proper code path):

  - Buyer-address resolver (warehouse → company)
  - Settable use-tax payable account
  - Opt-in toggle on the company settings
  - Synthetic taxes marked ``type_tax_use='purchase'`` so they
    don't pollute sale-tax reporting

* Operator-experience polish:

  - Fail-soft notification (``mail.activity`` to admins after N
    consecutive engine failures)
  - "Last successful calc" indicator on the settings page
  - "Calc count today" metric
  - Bulk recompute wizard for historical drafts after rate updates

* POS live-quote — JS-side round-trip on each line-add for accurate
  cashier preview (OWL component + ``/v1/calculate`` fetch)

v0.3.x — Upstream + ecosystem
------------------------------

* OCA upstream submission to ``OCA/account-fiscal-rule`` (relicense
  to AGPL-3 dual at submission time)
* Enterprise compatibility (coexist with the proprietary Avalara
  module on a per-fiscal-position basis)
* i18n / .po translations for non-English locales

Out of scope (per project constitution)
========================================

* Tax filing / remittance (engine constitution §13)
* Address validation (the engine validates the ZIP; full address
  hygiene is a separate concern)
* Non-USD currency (engine constitution §5 — the engine is USD-only
  by design)
* Modifying upstream Odoo source
* Marketplace facilitator handling (e.g., NJ / CA seller-of-record
  exceptions) — too narrow for v0.x
