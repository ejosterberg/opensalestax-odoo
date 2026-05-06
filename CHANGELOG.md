# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and per-branch versions follow Odoo's manifest convention
`<odoo-major>.<odoo-minor>.<module-major>.<module-minor>.<module-patch>`.

Each branch has its own release line.

## [Unreleased] — 18.0 branch

(empty — all work to date shipped under [18.0-v0.1.0].)

## [18.0-v0.1.0] — 2026-05-06

> **Stable.** Closes the architectural gap from alpha.1: invoice tax
> replacement on Odoo 18 now works end-to-end. A merchant deploying
> this gets correct destination-based US sales tax on every customer
> invoice, credit note, and sale order.

### Added

- **Override `AccountTax._add_tax_details_in_base_lines`** — the
  Odoo 18 batch tax engine entry point. For each base line that
  engages OST (US partner with valid 5-digit ZIP, USD currency,
  OST-enabled company, non-exempt partner): replaces
  `base_line['tax_ids']` with per-jurisdiction synthetic taxes and
  populates `base_line['manual_tax_amounts']` with engine-returned
  amounts. Odoo's standard tax engine then uses those amounts
  directly (the official bypass for external tax computation).
- **Multi-currency safety:** non-USD lines fall through to catalog
  rates. The engine is USD-only by design (engine constitution §5).
- **Verified end-to-end on Odoo 18 + Postgres 16 + l10n_generic_coa:**
  $100 invoice to ZIP 55401 produces `amount_tax=9.03`
  (engine-correct) with 6 per-jurisdiction tax lines visible on the
  move. Refunds (`out_refund`) sign-flip via Odoo's standard refund
  flow, preserving the OST breakdown.
- 32 unit tests still pass after the new override.

### Why this matters

Pre-1.0 alpha could only capture audit metadata; the move's
`amount_tax` still reflected whatever catalog rate was on the line.
This release replaces it with the engine result. Merchants now get:

- Correct destination-based tax on every customer invoice
- Per-jurisdiction tax lines visible on the form (state, county, city,
  district splits) — what tax authorities want to see in reporting
- Audit JSON in the OpenSalesTax notebook tab for compliance
- Same gates and fail-soft policy as the legacy `compute_all` path

The legacy `compute_all` override remains in place — it covers
direct programmatic calls (e.g., from custom modules) and is the
primary tax hook on the 16.0 / 17.0 branches.

## [18.0-v0.1.0-alpha.1] — 2026-05-06

> **Alpha scope.** This release ships the full module foundation,
> settings + connection test, audit-trail breakdown capture, and
> direct programmatic OST integration. **Invoice tax replacement on
> Odoo 18 is NOT yet wired** — see "Known limitations" below. Direct
> calls to `account.tax.compute_all(...)` work as expected; the
> breakdown JSON captured on `account.move._post()` reflects what OST
> would compute, even when Odoo applies its catalog rate to the move.
> Production-ready invoice tax replacement targets the v0.1.0 stable
> release.

### Added

- Initial scaffold for the `account_ostax` module on Odoo 18.0
- LGPL-3 license (constitution §3 carve-out)
- OCA-style file layout (`account_ostax/` with `models/`, `views/`,
  `security/`, `readme/`, `migrations/`)
- Repo-root scaffolding: README, CONTRIBUTING (DCO), SECURITY,
  CHANGELOG, SECURITY-REVIEW
- **Phase 3 — Settings page + connection test:** 8 per-company OST
  fields, settings panel under Settings → Accounting, Test
  Connection button surfacing engine version + DB status + RTT
- **Phase 4 — `compute_all` override:** engages the engine for US
  partners with a valid 5-digit ZIP, replaces the catalog rate with
  a per-jurisdiction breakdown, materializes one synthetic
  `account.tax` record per `(company × name × type)` on first
  encounter, sign-flips on `is_refund=True`. Fail-soft is
  config-driven; 4xx errors always surface as `UserError`.
  Works for direct programmatic use (`tax.compute_all(...)`).
- **Phase 5 — Breakdown audit capture:** `account.move._post()`
  hook records per-jurisdiction breakdown JSON + calc timestamp on
  every move that engages OST. Manual "Recompute Breakdown" button
  on draft moves. Form-view notebook tab surfacing the audit data.
- **Phase 7 — Exemption short-circuit:** `res.partner` extension
  with certificate / use-code / expiry. Exempt partners skip the
  engine and produce zero tax (engine API doesn't accept exemption
  fields yet — merchant-tracked).
- **Phase 9 — Opt-in debug log:** `ostax.calc.log` ring-buffer
  (50 entries per company) of engine calls; admin-viewable.

### Tested

- 32 unit tests on Odoo 18 + Postgres 16 in Docker on Proxmox VM 910
  (Phase 3, 4, 7, 9 all green)
- Live integration against engine v0.54.1: $100 line to ZIP 55401
  → 6 jurisdictions, total $9.025; refund flips signs; exempt
  partner short-circuits to zero tax
- Phase 5 capture verified on a real account.move: posting writes
  the full 6-jurisdiction breakdown JSON to `ostax_breakdown`

### Known limitations (v0.1.0-alpha)

- **Invoice tax replacement on Odoo 18 doesn't fire.** Odoo 18
  invoices use the new batch tax engine
  (`AccountTax._add_tax_details_in_base_lines()` driven from
  `account.move._get_rounded_base_and_tax_lines()`), bypassing the
  `compute_all` override. The audit breakdown captures correctly,
  but the move's actual `amount_tax` reflects whatever catalog tax
  was assigned to the line. **Implementing the proper override on
  the new entry point is the v0.1.0 stable release's primary
  task.** Tracked in ROADMAP.
- **Vendor-side use-tax accrual deferred to v0.2.** v0.1 supports
  customer-facing flows only (out_invoice, out_refund).
- **POS live-quote (JS-side round-trip) deferred to v0.2.**
  Server-authoritative compute on POS order close inherits the
  same Phase 4 limitation as invoices on 18.0.
- **No cache.** Engine call on every compute. v0.2 adds
  `tools.ormcache` for the rate stack.
- **Engine version not captured in breakdown JSON** — the SDK's
  `CalculationResult` doesn't expose it (it lives on `health()`).
  Cosmetic; v0.2 adds a separate health-stamp on capture.

### Engine compatibility

Tested against OpenSalesTax engine v0.54.1. Pin in production:
v0.22 minimum (pre-v0.22 had the SD-state-bleed bug).

## [Unreleased] — 17.0 branch

(Backport scheduled after 18.0 v0.1.0 ships.)

## [Unreleased] — 16.0 branch

(Backport scheduled after 17.0 v0.1.0 ships.)
