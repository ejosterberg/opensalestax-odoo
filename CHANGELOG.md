# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and per-branch versions follow Odoo's manifest convention
`<odoo-major>.<odoo-minor>.<module-major>.<module-minor>.<module-patch>`.

Each branch has its own release line.

## [Unreleased] — 18.0 branch

### Added

- Initial scaffold for the `account_ostax` module on Odoo 18.0
- LGPL-3 license (constitution §3 carve-out)
- OCA-style file layout (`account_ostax/` with `models/`, `views/`,
  `security/`, `readme/`, `migrations/`, etc.)
- Repo-root scaffolding: README, CONTRIBUTING (DCO), SECURITY, CHANGELOG
- **Phase 3 — Settings page + connection test:** per-company OST
  settings (8 fields), Test Connection button surfacing engine
  version + DB status + RTT. 8 unit tests pass on Odoo 18 + Postgres
  16.
- **Phase 4 — `compute_all` override (the core):** engages the engine
  for US partners with a valid 5-digit ZIP, replaces the catalog rate
  with a per-jurisdiction breakdown, materializes one synthetic
  `account.tax` record per (company × name × type) on first
  encounter, sign-flips on `is_refund=True`. Fail-soft is
  config-driven; 4xx errors always surface as `UserError`. 17 unit
  tests + verified end-to-end against live engine v0.54.1: $100 line
  to ZIP 55401 → 6 jurisdictions, total $9.025.

### Verified end-to-end (Odoo 18.0 / Postgres 16 / VM 910)

- Module installs cleanly (`-i account_ostax --stop-after-init`)
- Settings page renders + Test Connection returns engine v0.54.1
  in 11ms RTT
- $100 line to MSP returns the correct 6-jurisdiction breakdown
  summing to $9.025 (matches Minneapolis 9.025% combined rate)
- Refunds (`is_refund=True`) produce correctly-signed amounts
- Synthetic taxes are idempotent across repeated calls

## [Unreleased] — 17.0 branch

(Backport scheduled after 18.0 v0.1.0 ships.)

## [Unreleased] — 16.0 branch

(Backport scheduled after 17.0 v0.1.0 ships.)
