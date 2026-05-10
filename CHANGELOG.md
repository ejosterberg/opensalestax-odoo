# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and per-branch versions follow Odoo's manifest convention
`<odoo-major>.<odoo-minor>.<module-major>.<module-minor>.<module-patch>`.

Each branch ships independent tags. Tag format is `<NN.0>-vX.Y.Z`
(e.g. `18.0-v0.1.15`). The notes below cover all four branches
unless a version is branch-specific.

## [v0.3.5] — 2026-05-10

### Added

- **Per-line OST skip override.** New
  ``account.move.line.ostax_skip`` Boolean (default ``False``).
  When set on a specific line, the connector bypasses the engine
  for that line and lets Odoo's standard catalog-rate handling
  apply. Use cases:

  - The engine returns a wrong rate for one specific line (rare
    edge case the engine hasn't been told about yet) and the
    merchant wants to override manually.
  - Bringing in legacy data with pre-computed taxes that
    shouldn't be re-routed through the engine.
  - One-off manual override on a problem invoice without
    disabling OST for the entire move.

  Wired into ``_ostax_inject_into_base_line`` as the first gate
  after the multi-currency check — flagged lines bypass before
  any engine engagement logic runs.

- View extension: ``ostax_skip`` surfaced as an optional column
  on the invoice-lines list inside the move form. Hidden by
  default (``optional="hide"``); power users enable via the
  column-visibility menu so the common case stays clean.

### Tests

- 4 new tests in ``test_line_skip.py`` covering: default ``False``
  field value, skip=True bypasses the batch-engine path,
  skip=False engages normally, field persistence smoke test
  (verifies the field exists and is correctly typed).

## [v0.3.4] — 2026-05-08

### Added

- **Audit tab now displays a readable breakdown table** instead of
  raw JSON only. Non-developer accountants can finally read the
  per-jurisdiction breakdown without parsing
  ``{"jurisdictions":[{"name":...}]}``. The audit notebook tab on
  ``account.move``, ``sale.order``, and ``pos.order`` now shows:

  - **Header summary** — engine version, subtotal, tax total
  - **Per-line breakdown** — each line's amount, category,
    effective rate, tax total, optional note
  - **Per-jurisdiction table** — name / type / rate / tax,
    with right-aligned tabular figures
  - **Raw audit JSON** still preserved below the rendered view
    for debugging / programmatic access

  All values escaped server-side; no XSS risk from tampered
  breakdown data.

- New computed Html field ``ostax_breakdown_pretty`` on each of
  the three audit-bearing models. Lazy-computed from the existing
  ``ostax_breakdown`` Text field; not stored.

- New module ``account_ostax/models/_breakdown_html.py`` with a
  pure ``breakdown_to_html(json_str) -> html_str`` function.
  Independent of Odoo internals; trivially testable.

### Tests

- 7 new tests in ``test_breakdown_html.py`` covering: empty input,
  unparseable JSON fallback, full-breakdown rendering, XSS
  escaping, empty jurisdictions, no-lines case, and end-to-end
  field compute on a real ``account.move``.

## [v0.3.3] — 2026-05-08

### Added

- **Test Connection now reports config readiness** alongside engine
  health. The success notification message gains a multi-line
  config summary:

  - **Nexus** — list of state codes if scoped, else "all 50 states"
  - **Use-tax accrual** — off / on with payable account ✓ /
    on with payable account ✗ NOT SET
  - **Buyer location** — set partner name, else "company main
    address (default)"
  - **Fail-soft** — on / off (strict)
  - **Outage alerts** — N recipient(s) at threshold / no recipients
    configured

  When ``ostax_accrue_use_tax`` is ON but
  ``ostax_use_tax_payable_account_id`` is unset (a hard footgun —
  next vendor-bill post would raise ``UserError``), the notification
  kind escalates from **success** (green) to **warning** (yellow).
  Soft hints (no alert recipients, default buyer-location fallback)
  surface in the message but don't escalate the kind.

- New helper ``ResCompany._ostax_config_summary()`` returns
  ``(summary_text, has_hard_warnings)`` for reuse outside the
  Test Connection action.

### Tests

- 5 new tests in ``test_settings.py`` covering: summary appears in
  the message, missing-payable-account escalates to warning,
  setting the account clears the warning, nexus list is rendered
  with state codes, no-recipients is a soft hint that doesn't
  escalate the kind.

## [v0.3.2] — 2026-05-08

### Changed

Pure documentation update; no code changes. Companion to v0.3.1's
README refresh — extends the audit to the OCA-style
``readme/CONFIGURE.rst`` (rendered into the OCA ``README.rst``
build by setuptools-odoo) and the GitHub-rendered governance
docs.

- ``readme/CONFIGURE.rst`` rewritten end-to-end. The old version
  documented "Origin address" (renamed to "Use-tax address (buyer
  location)" in v0.2.0), missing nexus, vendor-bill, telemetry,
  alert, category-mapping, and bulk-recompute sections, and
  incorrectly claimed the engine applies exemption logic (the
  connector short-circuits client-side; engine never sees exempt
  partners). New structure: minimum config → recommended nexus
  filter → recommended outage alerts → opt-in vendor bills →
  per-product / per-category mapping → exemptions → multi-company
  → other settings → bulk recompute action.
- ``CONTRIBUTING.md`` branch table updated to include 19.0
  (was 16/17/18 only). Added a note that the maintainer typically
  lands patches on 18.0 first then cherry-picks to the other three.
- ``SECURITY.md`` "Affected branch(es)" prompt and "Supported
  versions" list updated to include 19.0. Refreshed the "thin
  override of compute_all" claim — the module now overrides both
  ``compute_all`` (16/17) and ``_add_tax_details_in_base_lines``
  (18+).

## [v0.3.1] — 2026-05-08

### Changed

Pure documentation update; no code changes. The PyPI front-page
description was lagging behind actual capabilities — Status section
still showed v0.2.0 / 58 tests, "What's deferred to v0.3" still
listed POS live-quote (now a v0.4 candidate), and v0.2.1 (operator
telemetry, mail.activity alerts, bulk recompute) and v0.3.0
(per-state nexus filter, sale.order/pos.order audit tabs) weren't
mentioned at all on the page merchants land on after a `pip search`.

README rewrites:

- **What you get** — restructured into four labeled groups
  (Sales-tax pipeline, Configuration & nexus control, Vendor side
  opt-in, Operator experience, Performance & reliability). Adds:
  per-state nexus filter, sale.order/pos.order audit tabs, engine
  telemetry, outage alerts, bulk recompute action.
- **Quick start** — extended from 4 to 7 steps. New steps cover
  states-with-nexus, outage-alert recipients, vendor-bill use-tax
  accrual (with explicit "off by default" guidance).
- **How it works** — fixed stale reference to a "What's deferred to
  v0.2" section that no longer existed (vendor bills shipped in
  v0.2.0). Added engagement-gate list and synthetic-tax
  materialization explainer. Vendor-bill behavior described
  accurately (opt-in, off by default).
- **Roadmap (v0.4 candidates)** — replaces the old "What's deferred
  to v0.3" section. Lists OCA submission, tax-report integration,
  POS live-quote, i18n.
- **Troubleshooting** — added two new entries (nexus-state customer
  with no `state_id`; engine outage alerts setup); refreshed the
  vendor-bills entry; added a bulk-recompute walkthrough.
- **Status** — bumped from v0.2.0 / 58 tests to v0.3.1 / 68 tests.

## [v0.3.0] — 2026-05-08

### Added

- **Per-state nexus filter on res.company.** New
  ``ostax_nexus_state_ids`` Many2many → ``res.country.state``
  (US-scoped via the settings UI domain). When set, the
  connector ONLY engages the engine for customers shipping to
  one of these states; out-of-state US customers fall through
  to Odoo's standard catalog-rate handling. Empty (default) =
  engage in all US states (v0.2.x behavior).

  Solves the small-merchant case ("I only collect in MN and
  WI") which was previously workaroundable only via fiscal
  positions per customer. A US customer in CA on a MN+WI
  nexus list now produces zero tax instead of querying the
  engine and paying for an unnecessary calc.

- **Audit-trail UI on sale.order and pos.order.** The
  per-jurisdiction breakdown previously only rendered on
  ``account.move`` form views. v0.3.0 surfaces the same
  "OpenSalesTax" notebook tab on:

  - ``sale.order`` form — visible at quote time, before the
    invoice exists. Useful for sales reps confirming the tax
    quote with the customer.
  - ``pos.order`` form (back-office) — shows breakdown +
    offline-cache flag for cashier-end audit.

  The fields (``ostax_breakdown``, ``ostax_engine_version``,
  ``ostax_calculated_at``) already existed on both models;
  this release adds the views.

### Tests

- 4 new tests in ``test_nexus_filter.py`` covering: empty
  nexus list engages everywhere, in-nexus state engages,
  out-of-nexus state bypasses, partner with no state record
  bypasses (conservative — can't confirm in-nexus without
  state info).

## [v0.2.1] — 2026-05-08

### Added

- **Operator-experience telemetry & alerts.** When the engine is
  silently fail-soft falling back to catalog rates, merchants
  often don't realize until they reconcile a tax report. v0.2.1
  surfaces the signals:

  - ``ostax_last_successful_calc_at`` (Datetime, readonly) —
    timestamp of the most recent successful engine call. Stale
    or unset means the engine hasn't been talking lately.
  - ``ostax_failure_streak`` (Integer, readonly) — consecutive
    engine failures since the last success. Resets on next
    success.
  - ``ostax_failure_streak_threshold`` (Integer, default 5) —
    when the streak crosses this, the connector posts a
    ``mail.activity`` warning to ``ostax_admin_alert_recipient_ids``.
  - ``ostax_admin_alert_recipient_ids`` (Many2many res.users) —
    who gets the activity. Empty disables alerting (counter
    still works).
  - ``ostax_calc_count_today`` (Integer, computed) — count of
    engine calls logged today (requires debug log on).

  All five surfaced on the settings page under a new "Engine
  telemetry" block.

- **Bulk recompute server action.** Added
  ``account.move.action_ostax_bulk_recompute_drafts`` plus the
  ``ir.actions.server`` registration that exposes it under the
  Action menu on ``account.move`` list views. Useful after a
  rate-table change on the engine side: filter Bills → All →
  state=Draft and run "OpenSalesTax: bulk recompute drafts" to
  refresh every draft's tax breakdown without opening each one.
  Skips moves that aren't draft or don't engage OST; reports a
  one-line summary.

### Changed

- All engine-call sites (batch path + legacy ``compute_all``
  path) now record success/failure into the new telemetry
  fields. Best-effort posting — a notification failure never
  breaks the calling tax-compute flow.

### Tests

- 6 new tests in ``test_operator_ux.py`` covering streak
  increment/reset, threshold-crossing activity post,
  no-recipient handling, calc-count-today, bulk-recompute
  empty-recordset shape.

## [v0.2.0] — 2026-05-08

### Added

- **Vendor-bill use-tax accrual at the buyer's location.**
  Replaces the v0.1.15 defensive bypass with a proper code path.
  When the company has opted in via the new
  ``ostax_accrue_use_tax`` setting (default OFF), vendor bills
  with US partners route through the engine using the BUYER's
  ZIP — not the vendor's — producing synthetic purchase-typed
  taxes that credit the company's configured Use Tax Payable
  account.
- New per-company settings:

  - ``ostax_accrue_use_tax`` (Boolean, default False) — opt-in
    toggle. Off → vendor bills bypass the connector (the v0.1.x
    behavior). On → engage the engine on inbound moves with
    proper buyer-location resolution.
  - ``ostax_use_tax_payable_account_id`` (Many2one to
    ``account.account``) — required when ``accrue_use_tax`` is
    on. Liability account credited by use-tax synthetic taxes
    via repartition lines. Sales tax credits a separate Sales
    Tax Payable account; keeping these distinct simplifies
    state-by-state reporting.
  - ``ostax_origin_address_id`` repurposed (was a stub field
    in v0.1.x) as the buyer-location partner. Falls back to
    ``company.partner_id`` when unset.

- Synthetic taxes now carry distinct ``type_tax_use`` per
  direction: ``"sale"`` for outbound (existing behavior),
  ``"purchase"`` for use-tax. Sales and purchase synthetics
  for the same jurisdiction are SEPARATE records — they don't
  pollute each other's reporting.
- Use-tax synthetics carry a name-suffix disambiguator:
  ``OST · Minnesota (state, use tax)`` vs
  ``OST · Minnesota (state)`` for sales. Visible on line tags
  + tax reports.
- Use-tax synthetics route the tax amount to
  ``ostax_use_tax_payable_account_id`` via repartition lines
  (``invoice_repartition_line_ids`` /
  ``refund_repartition_line_ids``).

### Changed

- ``_ostax_ensure_synthetic_taxes(...)`` takes an optional
  ``use_type`` parameter (default ``"sale"``). Search and
  create are scoped to the requested type so sale/purchase
  records remain disjoint.
- ``_ostax_compute_all(...)`` takes an optional ``use_type``
  parameter; threaded through from ``compute_all`` based on
  the catalog tax's ``type_tax_use``.
- Customer exemption short-circuit now skips on the inbound
  side. A buyer's exemption certificate doesn't apply to
  use tax owed (use tax is the buyer's own liability,
  separate from sales tax exemption logic).

### Migration note

Existing v0.1.x users upgrading to v0.2.0 see no behavior
change unless they opt in via ``Settings → Accounting →
OpenSalesTax → Accrue use tax on vendor bills``. To enable:

1. Set the **Use-tax address (buyer location)** to your
   primary nexus partner (or leave unset to use the company's
   main address).
2. Configure **Use Tax Payable account** — pick or create a
   liability account in your chart for use-tax accrual.
3. Toggle **Accrue use tax on vendor bills** ON.

The next vendor bill posted by a US partner will then route
through the engine and book use tax to the configured account.

### Tests

- 9 new tests in ``test_vendor_use_tax.py`` covering
  legacy + batch paths × off/on/no-account/buyer-zip
  resolution / type_tax_use separation.
- Existing ``test_vendor_bypass.py`` updated to make the
  ``accrue_use_tax = False`` precondition explicit (still
  the default).

## [v0.1.17] — 2026-05-08

### Fixed

- **README "How it works" section was misleading.** It said the
  connector engaged on "sale order / invoice / POS order /
  vendor bill" — but v0.1.15 added a defensive bypass on vendor
  bills, contradicting the "What's deferred to v0.2" section a
  few paragraphs later. Rewrote the section to describe outbound
  flows accurately and call out the v0.2 deferral for inbound.
- README "Status" stamped at v0.1.15; bumped to v0.1.17.
- Branch matrix Status column had inconsistent text per branch
  ("shipping" / "shipping (default)" / "shipping (Odoo 19 GA
  confirmed)"). All four are stable; simplified to "shipping"
  everywhere.

### Added

- **README install snippet is branch-neutral.** Previously each
  branch's wheel showed a single "for Odoo NN" line as the
  primary example, which on PyPI (which displays the latest
  wheel's metadata) made the page look Odoo-19-specific. Now
  the install block lists all four version-prefix selectors so
  the page is useful regardless of which wheel a user lands on.
- **Quick start** section in README — minimum config walkthrough
  (engine URL, API key, Test Connection, fail-soft).
- **Engine compatibility** section in README — minimum engine
  version (v0.22), tested-against version (v0.54.1+), v1 API
  contract.
- **Troubleshooting** section in README covering the five most
  common deployment / behavior questions.
- ``readme/USAGE.rst`` — corrected (used to claim vendor bills
  engage); added per-product / per-category category mapping
  walkthrough.
- ``readme/ROADMAP.rst`` — completely rewritten to reflect what
  actually shipped (v0.1.x line) and what's next (v0.2.x =
  vendor-side + operator UX; v0.3.x = OCA + ecosystem).
- ``readme/DESCRIPTION.rst`` — corrected (used to claim "vendor
  bill" was an engaged flow); now describes outbound-only with
  v0.2 deferral noted.
- ``readme/INSTALL.rst`` — was Odoo-18-only and pinned at
  v0.1.0; now branch-neutral with all four majors and the v0.1.12
  Odoo-16 wheel-pin warning.

No code changes. Pure documentation pass; PyPI front-page and OCA
description rendering both update to reflect the current shape of
the addon.

## [v0.1.16] — 2026-05-07

### Changed

- Documentation pass: `README.md` rewritten to describe the
  v0.1.11 cache layer, v0.1.13 per-product OST tax-category
  field, v0.1.14 per-category default with parent-walk
  inheritance, v0.1.15 vendor-bill bypass, and current test
  count (49 unit tests on each branch).
- `CHANGELOG.md` backfilled with entries for v0.1.1 through
  v0.1.15. The per-branch `[Unreleased]` sections previously
  said "Backport scheduled after 18.0 v0.1.0 ships" even though
  16/17/19 had been shipping for hours; cleaned that up.

No code changes. PyPI description on
<https://pypi.org/project/odoo-addon-account-ostax/> updates
to reflect current capabilities.

## [v0.1.15] — 2026-05-07

### Fixed

- **Vendor bills no longer produce nonsensical tax numbers.**
  v0.1.0–v0.1.14 engaged the engine on any line with a
  US-located partner — including vendor bills, where the partner
  is the *vendor*, not the buyer. The engine call used the
  vendor's ZIP, computing tax at the vendor's location instead
  of the buyer's. Two defensive gates added: `compute_all`
  bypasses when `self.type_tax_use != 'sale'`;
  `_ostax_inject_into_base_line` (Odoo 18+) bypasses when the
  line's `record.move_id.move_type` starts with `in_`. Vendor
  bills now fall through to Odoo's standard catalog rates until
  v0.2 ships proper use-tax accrual at the buyer's location.

### Added

- 4 new tests covering both bypass paths and regression-guards
  confirming sales-tax flows still engage. Total: **49 unit
  tests on each branch.**

## [v0.1.14] — 2026-05-07

### Added

- **Per-category OST tax-category default with parent-walk
  inheritance.** New `product.category.ostax_category` Selection
  field (no default — unset means "inherit from parent"). The
  lookup walks up `parent_id` until it finds a value, then falls
  back to `"general"`. Closest-ancestor wins; cycle-safe (tracks
  seen IDs).
- View extension surfaces the field on `product.category` after
  `parent_id`.
- Eliminates per-product setup for merchants with well-organized
  catalogs: mark "Apparel" as `clothing` once → cascades to every
  product underneath unless an intermediate node sets its own
  value.
- 6 new tests covering inheritance, parent-chain walking,
  override precedence.

### Changed

- `_ostax_category_for(product)` lookup precedence now:
  1. `product.product_tmpl_id.ostax_category` (per-product
     override, v0.1.13)
  2. Closest-ancestor `product.category.ostax_category` (walks
     `parent_id`, v0.1.14)
  3. Fall back to `"general"`

## [v0.1.13] — 2026-05-07

### Added

- **Per-product OST tax-category mapping.** New
  `product.template.ostax_category` Selection field with engine-
  aligned options: `general` (default), `clothing`, `groceries`,
  `prescription_drugs`, `prepared_food`, `digital_goods`. The
  engine applies per-state taxability rules based on the chosen
  category (Minnesota exempts clothing, New York taxes prepared
  food differently than groceries, etc.).
- View extension on the product form's Accounting tab, right
  after the existing Customer Taxes field.
- 7 new tests including a contract-pinning check that fails if
  the engine and addon's category lists drift.

### Changed

- `_ostax_category_for(product)` reads
  `product.product_tmpl_id.ostax_category`; falls back to
  `"general"`. Defensive against `None`, unset, and templates
  passed directly.

## [v0.1.12] — 2026-05-07

### Fixed

- **Odoo 16 module load no longer fails with `SyntaxError`.**
  Odoo 16's `tools.ormcache` builds its key-extraction lambda by
  stringifying the wrapped function's `inspect.signature` without
  stripping annotations. Combined with this module's
  `from __future__ import annotations`, the parameter annotations
  became string literals (e.g. `'int'`), producing a malformed
  lambda. Stripped the annotations from
  `_ostax_engine_calculate_cached`. Odoo 17/18/19 are tolerant
  (their `cache.py` strips annotations first).
- Cross-version `Registry.clear_cache()` (Odoo 17+) /
  `clear_caches()` (Odoo 16) probe in the test base class so the
  same code runs on all four branches.

### Migration note

- The 16.0.0.1.11 wheel on PyPI is broken (won't install on
  Odoo 16). Anyone pinning to that exact version should upgrade
  to **16.0.0.1.12 or later**.

## [v0.1.11] — 2026-05-07

### Added

- **Per-worker engine-response cache (`tools.ormcache`).** Wraps
  the engine `/v1/calculate` call in a cache-decorated helper
  keyed by `(company_id, zip5, zip4, line amount, category,
  hourly bucket)`. Repeat calculations within the same hour for
  the same line shape skip the engine entirely — useful for
  batch invoicing, recurring orders, multi-line carts, and any
  flow that re-prices the same product to the same destination
  repeatedly. ~1 hour sliding TTL via the hourly-bucket key
  component (no manual invalidation).
- Wired into both call paths: batch-engine
  (`_ostax_inject_into_base_line`, used on Odoo 18+) and legacy
  `compute_all` (used on Odoo 16/17).
- Tests clear `env.registry.clear_cache()` in `setUp` so
  `assert_called_once` mocks remain accurate per-test.
- Per-worker memory; multi-worker deployments get one cache per
  worker (acceptable: engine remains the source of truth, cache
  is just a local optimization).

## [v0.1.10] — 2026-05-07

### Fixed

- **CI fix:** `pip install --break-system-packages` fallback
  for older pip on Debian 11/12 (Odoo 16/17 images). Odoo 18+
  Debian images ship a newer pip that requires the flag (PEP
  668); Odoo 16/17 images ship an older pip that doesn't
  recognize it. Shell-level `||` fallback in the install step.

## [v0.1.9] — 2026-05-07

### Added

- **Line-level OST jurisdiction tags persisted on posted
  invoices.** Previously the totals area showed correct
  per-jurisdiction tax amounts, but the line-level tax tag
  still showed the catalog placeholder ("Tax 9.025%" or
  similar). Now the synthetic OST jurisdiction names appear
  directly on the line ("OST · Minnesota (state)", etc.).
- Implementation: writes during the draft phase via
  `base_line['record']` back-reference (posted move lines are
  immutable); idempotent so the recompute it triggers doesn't
  loop.

## [v0.1.8] — 2026-05-07

### Added

- **Per-branch test workflows for 16/17/18/19.** Previously only
  18 had dedicated CI; now each branch has its own
  `Test <NN.0>` workflow on push/PR. Matrix uses Postgres 15 for
  16/17 and Postgres 16 for 18/19.

## [v0.1.7] — 2026-05-07

### Fixed

- **Module install no longer fails on Odoo 18 + 19 due to
  removed cron fields.** `numbercall` and `doall` were dropped
  from `ir.cron` in Odoo 18+. Removed both from
  `data/ostax_cron.xml` (defaults are sensible).

## [v0.1.6] — 2026-05-07

### Added

- README rewritten to mark all 4 branches as shipping (PyPI
  description now reflects 19.0 GA).

### Fixed

- Defensive `account.tax.group.company_id` field guard for
  Odoo 16 (the field doesn't exist there). Cured 10 test
  errors.
- CI install on Odoo 18 image: added `--break-system-packages`
  to the pip command (PEP 668 was rejecting installs on the
  newer Debian).

## [v0.1.5] — 2026-05-07

### Added

- Optional `ir.cron` to soft-archive synthetic OST taxes
  unused for 90+ days (`active=False`; reactivates on next
  calc to that jurisdiction). Off by default — merchants who
  don't want it can leave the cron disabled.
- `engine_version` is now captured via `client.health()` and
  stamped on the breakdown JSON at `_post()` time.

## [v0.1.4] — 2026-05-07

### Changed

- Settings page rewritten to use the modern Odoo 18
  `<setting>` blocks with help text per option. Cross-version
  xpath: 16 uses `//div[@data-key='account']`; 17/18/19 use
  `//app[@name='account']`.

## [v0.1.3] — 2026-05-07

### Fixed

- **"Tax 15%" no longer appears in the totals area.** v0.1.0–
  v0.1.2 created synthetic OST taxes without a `tax_group_id`,
  causing the chart's default "Tax 15%" group to be used as
  the heading. v0.1.3 creates per-type tax groups
  (`OpenSalesTax — State / County / City / District`) on first
  use and assigns the matching group to each synthetic tax.

## [v0.1.2] — 2026-05-06

### Added

- First PyPI release. Initial Trusted-Publishing (OIDC) setup
  via GitHub Actions; `Publish to PyPI` workflow triggered on
  `<NN.0>-v*` tag push.

## [v0.1.0] — 2026-05-06

> **Stable.** Closes the architectural gap from v0.1.0-alpha.1:
> invoice tax replacement on Odoo 18 now works end-to-end.

### Added

- **Override `AccountTax._add_tax_details_in_base_lines`** —
  the Odoo 18 batch tax engine entry point. For each base line
  that engages OST (US partner with valid 5-digit ZIP, USD
  currency, OST-enabled company, non-exempt partner): replaces
  `base_line['tax_ids']` with per-jurisdiction synthetic taxes
  and populates `base_line['manual_tax_amounts']` with engine-
  returned amounts. Odoo's standard tax engine then uses those
  amounts directly (the official bypass for external tax
  computation).
- **Multi-currency safety:** non-USD lines fall through to
  catalog rates. The engine is USD-only by design (engine
  constitution §5).
- **Verified end-to-end on Odoo 18 + Postgres 16 +
  l10n_generic_coa:** $100 invoice to ZIP 55401 produces
  `amount_tax=9.03` (engine-correct) with 6 per-jurisdiction
  tax lines visible on the move. Refunds (`out_refund`)
  sign-flip via Odoo's standard refund flow, preserving the
  OST breakdown.
- 32 unit tests pass.

## [v0.1.0-alpha.1] — 2026-05-06

> **Alpha scope.** This release ships the full module
> foundation, settings + connection test, audit-trail
> breakdown capture, and direct programmatic OST integration.
> **Invoice tax replacement on Odoo 18 is NOT yet wired** —
> see "Known limitations" below.

### Added

- Initial scaffold for the `account_ostax` module on Odoo 18.0
- LGPL-3 license (constitution §3 carve-out)
- OCA-style file layout (`account_ostax/` with `models/`,
  `views/`, `security/`, `readme/`, `migrations/`)
- Repo-root scaffolding: README, CONTRIBUTING (DCO), SECURITY,
  CHANGELOG, SECURITY-REVIEW
- **Phase 3 — Settings page + connection test:** 8 per-company
  OST fields, settings panel under Settings → Accounting,
  Test Connection button surfacing engine version + DB status
  + RTT
- **Phase 4 — `compute_all` override:** engages the engine for
  US partners with a valid 5-digit ZIP, replaces the catalog
  rate with a per-jurisdiction breakdown, materializes one
  synthetic `account.tax` record per `(company × name × type)`
  on first encounter, sign-flips on `is_refund=True`. Fail-soft
  is config-driven; 4xx errors always surface as `UserError`.
- **Phase 5 — Breakdown audit capture:** `account.move._post()`
  hook records per-jurisdiction breakdown JSON + calc timestamp
  on every move that engages OST. Manual "Recompute Breakdown"
  button on draft moves. Form-view notebook tab surfacing the
  audit data.
- **Phase 7 — Exemption short-circuit:** `res.partner` extension
  with certificate / use-code / expiry. Exempt partners skip
  the engine and produce zero tax (engine API doesn't accept
  exemption fields yet — merchant-tracked).
- **Phase 9 — Opt-in debug log:** `ostax.calc.log` ring-buffer
  (50 entries per company) of engine calls; admin-viewable.

### Tested

- 32 unit tests on Odoo 18 + Postgres 16 in Docker
  (Phase 3, 4, 7, 9 all green)
- Live integration against engine v0.54.1: $100 line to ZIP
  55401 → 6 jurisdictions, total $9.025; refund flips signs;
  exempt partner short-circuits to zero tax

### Engine compatibility

Tested against OpenSalesTax engine v0.54.1. Pin in production:
v0.22 minimum (pre-v0.22 had the SD-state-bleed bug).
