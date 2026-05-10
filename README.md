# opensalestax-odoo

[![PyPI](https://img.shields.io/pypi/v/odoo-addon-account-ostax?label=PyPI)](https://pypi.org/project/odoo-addon-account-ostax/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](LICENSE)
[![Odoo 16.0](https://img.shields.io/badge/Odoo-16.0-714B67.svg)](https://github.com/ejosterberg/opensalestax-odoo/tree/16.0)
[![Odoo 17.0](https://img.shields.io/badge/Odoo-17.0-714B67.svg)](https://github.com/ejosterberg/opensalestax-odoo/tree/17.0)
[![Odoo 18.0](https://img.shields.io/badge/Odoo-18.0-714B67.svg)](https://github.com/ejosterberg/opensalestax-odoo/tree/18.0)
[![Odoo 19.0](https://img.shields.io/badge/Odoo-19.0-714B67.svg)](https://github.com/ejosterberg/opensalestax-odoo/tree/19.0)

**Destination-based US sales tax for Odoo Community.** Replaces static tax-rate
configuration with live calculation against an
[OpenSalesTax](https://github.com/ejosterberg/open-sales-tax) engine — your own
self-hosted instance, no per-transaction fees, no SaaS lock-in.

The free, self-hostable answer to Avalara on Odoo Community Edition. Available
on **all four current Odoo major versions** — 16.0, 17.0, 18.0, and 19.0 — same
module, branch-per-version per the OCA convention.

## Branch matrix

Pick the branch matching your Odoo install. Releases are independent per branch.

| Odoo version | Branch | PyPI artifact | Status |
|---|---|---|---|
| 16.0 | [`16.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/16.0) | [`odoo-addon-account-ostax==16.0.*`](https://pypi.org/project/odoo-addon-account-ostax/) | shipping |
| 17.0 | [`17.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/17.0) | [`odoo-addon-account-ostax==17.0.*`](https://pypi.org/project/odoo-addon-account-ostax/) | shipping |
| 18.0 | [`18.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/18.0) | [`odoo-addon-account-ostax==18.0.*`](https://pypi.org/project/odoo-addon-account-ostax/) | shipping |
| 19.0 | [`19.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/19.0) | [`odoo-addon-account-ostax==19.0.*`](https://pypi.org/project/odoo-addon-account-ostax/) | shipping |

## What you get

**Sales-tax pipeline:**

- Sales orders, customer invoices, credit notes/refunds, POS — all with
  destination-based per-jurisdiction US tax
- Per-jurisdiction breakdown stored on every move, sale order, and POS
  order (state / county / city / district), rendered as an
  *OpenSalesTax* notebook tab for full audit trail
- Line-level OST jurisdiction tags persisted on posted invoices
- Refunds (`out_refund`) sign-flip via Odoo's standard refund flow,
  preserving the OST breakdown

**Configuration & nexus control:**

- **Per-state nexus filter** — if you only collect tax in MN and WI,
  set those two states on the company; out-of-state customers fall
  through to catalog rates without an engine call (no nexus list =
  engage in all 50 states, the default)
- **Per-product taxability category** (`product.template.ostax_category`
  — general / clothing / groceries / prescription_drugs / prepared_food
  / digital_goods); engine applies per-state taxability rules (e.g.
  Minnesota exempts clothing, New York taxes prepared food differently
  than groceries)
- **Per-category default with parent-walk inheritance** — mark
  "Apparel" as `clothing` once on `product.category`, every product
  underneath inherits unless overridden. Closest-ancestor wins.
- Customer exemption certificates on `res.partner`
- Fiscal-position interop — non-US partners route through Odoo's
  standard "Export" mapping; the connector only engages for US shipping
  addresses
- Multi-company support — settings scoped per company

**Vendor side (opt-in):**

- **Use-tax accrual on vendor bills** — when enabled, vendor bills
  with US partners route through the engine using the BUYER's ZIP
  (your nexus location), producing synthetic purchase-typed taxes
  that credit your **Use Tax Payable** account. Default OFF; existing
  users see no behavior change on upgrade.

**Operator experience:**

- **Engine telemetry on the settings page** — last successful calc
  timestamp, current failure streak, calls today
- **Outage alerts** — after N consecutive engine failures
  (configurable), a `mail.activity` warning is posted to admin
  recipients. Catches silent fail-soft fallback before it shows up in
  a tax-report reconciliation surprise.
- **Bulk recompute action** — "OpenSalesTax: bulk recompute drafts"
  on the `account.move` list view's Action menu. Useful after an
  engine rate-table change.

**Performance & reliability:**

- **Per-worker engine-response cache** (~1 hour sliding TTL) — repeat
  calculations within the same hour for the same line shape skip the
  engine. Helpful for batch invoicing, recurring orders, multi-line
  carts.
- **Fail-soft policy** — when the engine is unreachable or returns
  5xx, the connector falls back to catalog rates and logs a warning
  (configurable; can also surface as `UserError` for fail-hard)
- Optional admin debug log of recent calculations (50-entry ring
  buffer)
- Optional 90-day archive cron for jurisdictions you've stopped
  shipping to

## Roadmap (v0.4 candidates)

- **OCA upstream submission** to ``OCA/account-fiscal-rule`` (relicense
  to AGPL-3 dual at submission time)
- **Tax-report integration** — pre-built "OST tax accrual" report
  that splits sales/use × per-jurisdiction × month-end totals
- **POS live-quote** — JS-side round-trip on each line-add for
  accurate cashier preview (server-authoritative compute on order
  close already works)
- **i18n** — `.po` skeleton + es_US locale

## Install

The same package serves all four Odoo majors via version-prefix
selectors. Pick the one that matches your Odoo install:

```bash
# 1) The Python SDK (same on every branch):
pip install opensalestax

# 2) The connector (pick ONE matching your Odoo major):
pip install 'odoo-addon-account-ostax>=16.0.0.1.12,<17.0'  # Odoo 16
pip install 'odoo-addon-account-ostax>=17.0,<18.0'         # Odoo 17
pip install 'odoo-addon-account-ostax>=18.0,<19.0'         # Odoo 18
pip install 'odoo-addon-account-ostax>=19.0,<20.0'         # Odoo 19
```

> **Note for Odoo 16 users:** The `16.0.0.1.11` wheel is broken
> (a `tools.ormcache` annotation-stripping bug — see CHANGELOG
> for v0.1.12). Always pin **`>=16.0.0.1.12`**.

Or install from source — replace `<NN.0>` with your major:

```bash
git clone -b <NN.0> https://github.com/ejosterberg/opensalestax-odoo.git
cd opensalestax-odoo
# Symlink or copy account_ostax/ into your Odoo addons-path
```

Then in Odoo: **Apps → search "OpenSalesTax" → Install**, then
**Settings → Accounting → OpenSalesTax** to configure the engine URL.

## Quick start

After install, in **Settings → Accounting → OpenSalesTax**:

1. **Engine URL** — point at your OpenSalesTax engine (e.g.
   `http://10.0.0.50:8080`). Self-hosted; see the engine project at
   <https://github.com/ejosterberg/open-sales-tax> for a
   docker-compose deployment.
2. **API key** — leave blank for unauthenticated engines (default).
3. **Click "Test Connection"** — should report engine version + DB
   status + RTT in milliseconds. If it fails, check the engine is
   reachable from the Odoo host and the URL is correct.
4. **Fail-soft** — recommended ON during initial rollout. The connector
   falls through to catalog rates if the engine is unreachable rather
   than blocking invoice posting. Switch off once you trust
   connectivity.

That's it for sales tax. Create a US customer with a 5-digit ZIP, add
a sale order or invoice, and the connector engages automatically.

**Recommended next steps after the basics work:**

5. **States with nexus** — if you only collect tax in a subset of
   states, list them here. Out-of-state US customers will fall
   through to catalog rates (no engine call). Empty = engage
   everywhere. *Optional; the default works for "we collect
   nationwide" merchants.*
6. **Engine outage alert recipients** — pick the users who should
   get a `mail.activity` warning if the engine fails 5+ consecutive
   times in a row. Catches silent fail-soft before it surfaces in
   tax reporting. *Strongly recommended for production deployments.*
7. **Vendor bills (use-tax accrual)** — turn on if your business has
   nexus in multiple states and accrues use tax on out-of-state
   purchases. Requires picking a *Use Tax Payable* liability
   account. *Off by default — flip on only if you understand use-tax
   filing on your state returns.*

## Configuring per-product / per-category taxability

For most products, leave everything at the defaults — the engine treats
unflagged products as `general` taxable goods.

For products in special-taxability categories (clothing, groceries,
prescription drugs, prepared food, digital goods), set the category on:

- **The product** (Inventory → Products → form view → Accounting tab →
  *OST tax category*), OR
- **The product's internal category** (Inventory → Configuration →
  Product Categories → form view → *OST tax category default*) — every
  descendant product inherits unless overridden.

The lookup precedence is: per-product → product's category → walk up
`parent_id` until a value is found → fall back to `general`.

## How it works

The connector overrides Odoo's tax computation entry points (the new
batch tax engine on 18+, legacy `compute_all` on 16/17). When a US
customer with a valid 5-digit ZIP is on an outbound flow — sale order,
customer invoice, credit note, POS order — Odoo's tax pipeline calls
the OpenSalesTax engine via the [Python
SDK](https://pypi.org/project/opensalestax/) and replaces the static
catalog rate with a per-jurisdiction breakdown.

Synthetic taxes are materialized lazily, one per
`(company × jurisdiction-name × jurisdiction-type × type_tax_use)` —
your chart accumulates new tax records only when the engine reports
new jurisdictions on a real transaction. Sale-side and use-side
synthetics for the same jurisdiction stay in separate records so
they don't pollute each other's tax reports.

**Engagement gates** (all must pass):

- Company has `ostax_enabled` and an engine URL configured
- Customer's `country_id` is the US
- Customer's `zip` is at least 5 numeric digits
- Customer's `state_id` is in the configured nexus list (when set)
- Currency is USD (engine is USD-only by design)

Non-US partners and any of those gates failing → the line falls
through to Odoo's standard catalog-rate handling.

**Vendor bills** route the same way IF the company has opted in to
use-tax accrual; otherwise inbound moves bypass the connector
entirely and use Odoo's catalog-rate handling.

## Engine compatibility

Tested against OpenSalesTax engine **v0.54.1+**. **Minimum: v0.22** —
earlier versions had an SD-state-bleed bug (engine GitHub
[issue #37](https://github.com/ejosterberg/open-sales-tax/issues/37)
— closed in v0.22.0). The connector requires the v1 HTTP API
(`/v1/calculate`, `/v1/health`, `/v1/states`, `/v1/rates`).

Pin the engine in production. The connector is forward-compatible
within the v1 API contract; if a future engine bumps to v2, the
connector will need a corresponding bump.

## Troubleshooting

**"Test Connection" works but invoices don't engage.** Check that the
customer has `country_id = United States` and a 5-digit-or-longer
`zip`. Non-US customers and US customers with malformed ZIPs route to
Odoo's standard fiscal-position handling — not an OST bug. Also
check the **States with nexus** setting: if it's set and the customer
isn't in one of those states, the connector intentionally bypasses.

**Customer has the right state and ZIP but still falls through.**
If you set **States with nexus** but the customer record has no
`state_id` (only a country + ZIP), the connector conservatively
bypasses — it can't verify in-nexus without a state record. Either
populate `state_id` on the customer or unset the nexus list.

**Tax appears as `Tax 15%` (or your chart's default).** You're on
v0.1.2 or earlier, before per-type tax groups landed. Upgrade to
**v0.1.3 or later** — the synthetic taxes now sit under
`OpenSalesTax — State / County / City / District` groups.

**Vendor bills show catalog rates.** That's the v0.1.x default —
vendor bills bypass the connector. To enable use-tax accrual,
upgrade to **v0.2.0+**, set the Use-tax address + Use Tax Payable
account in company settings, and toggle **Accrue use tax on vendor
bills** ON.

**Engine is reachable but calls return errors.** Enable **Debug log**
on the settings page and check **Settings → Technical → OpenSalesTax
Calc Log** for the last ~50 calls per company (status code, RTT,
engine version). If 4xx, the request is malformed (usually a
non-numeric ZIP); if 5xx, the engine itself is failing — pull engine
logs.

**Invoice posts with `amount_tax = 0` despite a US customer.** The
customer probably has an OST exemption certificate set
(`res.partner` → *OST exemption* tab). Exempt partners short-circuit
to zero tax with no engine call.

**Engine looks down but no one notices for days.** Configure
**Engine outage alert recipients** on the settings page and set the
**Alert after N consecutive failures** threshold (default 5). After
N failures in a row, the connector posts a `mail.activity` warning
to each recipient — once per threshold-crossing edge, no spam if the
streak keeps climbing. Also watch the read-only **Last successful
call** timestamp on the settings page; a stale value is the early
warning.

**Need to refresh tax on a batch of drafts after an engine
rate-table update.** Filter `account.move` to `state=Draft`, select
the batch, and run **Action → OpenSalesTax: bulk recompute drafts**.
Skips moves that aren't draft or don't engage OST; reports a
one-line summary.

## Calculation only

> Tax calculations are provided as-is for convenience. The merchant is
> solely responsible for tax-collection accuracy and remittance to the
> appropriate jurisdictions. Verify against your state Department of
> Revenue before remitting.

This module does NOT file returns, remit collected tax, validate addresses,
or provide legal/tax advice.

## License

[LGPL-3](LICENSE) (or-later) per the project's per-platform license carve-out.
Apache-2.0 SDK consumed. DCO sign-off required on every commit; no AI
co-author trailers. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Status

**Production-grade across all four Odoo majors.** v0.3.1 is shipping
on PyPI as `odoo-addon-account-ostax==<branch>.0.3.1` for 16.0,
17.0, 18.0, and 19.0. Per-branch test workflows green on every
branch; 68 unit tests pass on real Odoo + Postgres in Docker.

How it's wired:

- **Odoo 18 + 19** override `account.tax._add_tax_details_in_base_lines`
  using the official `manual_tax_amounts` injection mechanism — same
  hook the proprietary Avalara module uses, no internal-API
  fragility.
- **Odoo 16 + 17** override the legacy `compute_all` method (the new
  batch engine arrived in 18.0).
- Per-version settings xpath: 16 uses `//div[@data-key='account']`;
  17/18/19 use `//app[@name='account']`.

Verified end-to-end on real Odoo + Postgres in Docker against the
live engine, including Odoo's official US chart of accounts
(`l10n_us`): $100 invoice to MSP (ZIP 55401) produces
`amount_tax=9.03` with 6 per-jurisdiction lines.
