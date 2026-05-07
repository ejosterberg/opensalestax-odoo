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
| 18.0 | [`18.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/18.0) | [`odoo-addon-account-ostax==18.0.*`](https://pypi.org/project/odoo-addon-account-ostax/) | shipping (default) |
| 19.0 | [`19.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/19.0) | [`odoo-addon-account-ostax==19.0.*`](https://pypi.org/project/odoo-addon-account-ostax/) | shipping (Odoo 19 GA confirmed) |

## What you get

- Sales orders, customer invoices, credit notes/refunds, POS — all with
  destination-based per-jurisdiction US tax
- Per-jurisdiction breakdown stored on every move (state / county / city /
  district), rendered on the form view for full audit trail
- **Per-product taxability category** (`product.template.ostax_category` —
  general / clothing / groceries / prescription_drugs / prepared_food /
  digital_goods); engine applies per-state taxability rules (e.g. Minnesota
  exempts clothing, New York taxes prepared food differently than
  groceries)
- **Per-category default with parent-walk inheritance** — mark "Apparel"
  as `clothing` once on `product.category`, every product underneath
  inherits unless overridden. Closest-ancestor wins.
- **Per-worker engine-response cache** (~1 hour sliding TTL) — repeat
  calculations within the same hour for the same line shape skip the
  engine. Helpful for batch invoicing, recurring orders, multi-line carts.
- Customer exemption certificates on `res.partner`
- Multi-company support — settings scoped per company
- Fiscal-position interop — non-US partners route through Odoo's standard
  "Export" mapping; the connector only engages for US shipping addresses
- Settings page with engine connection test, fail-soft toggle
- Optional admin debug log of recent calculations
- Optional 90-day archive cron for jurisdictions you've stopped shipping to

## What's deferred to v0.2

- **Vendor bills + use-tax accrual.** Use tax is owed at the buyer's
  location, not the vendor's; v0.1 doesn't yet implement the
  buyer-location code path. Vendor bills (and any purchase-typed
  catalog tax) bypass the connector and fall through to Odoo's standard
  catalog rates — see v0.1.15.
- **POS live-quote.** Server-authoritative compute on order close
  works; per-line live JS-side round-trip on each line-add is a v0.2
  enhancement.

## Install

```bash
# Match the branch to your Odoo major:
pip install opensalestax  # the Python SDK
pip install 'odoo-addon-account-ostax>=19.0.0.1.15,<20.0'  # for Odoo 19
# (use >=16.0.0.1.12,<17.0 / >=17.0.0.1.15,<18.0 / >=18.0.0.1.15,<19.0
# for the other branches)

# Or install from source:
git clone -b 19.0 https://github.com/ejosterberg/opensalestax-odoo.git
cd opensalestax-odoo
# Symlink or copy account_ostax/ into your Odoo addons-path
```

> **Note for Odoo 16 users:** The `16.0.0.1.11` wheel is broken
> (a `tools.ormcache` annotation-stripping bug — see CHANGELOG
> for v0.1.12). Pin **`>=16.0.0.1.12`** or use the latest.

Then in Odoo: **Apps → search "OpenSalesTax" → Install**, then
**Settings → Accounting → OpenSalesTax** to configure the engine URL.

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

The connector overrides `account.tax.compute_all`. When a US partner with a
valid 5-digit ZIP is on a sale order / invoice / POS order / vendor bill,
`compute_all` calls the OpenSalesTax engine via the [Python
SDK](https://pypi.org/project/opensalestax/) and replaces the static
catalog rate with the engine's per-jurisdiction breakdown. Non-US partners
fall through to Odoo's standard fiscal-position handling.

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

**Production-grade across all four Odoo majors.** v0.1.15 is shipping
on PyPI as `odoo-addon-account-ostax==<branch>.0.1.15` for 16.0,
17.0, 18.0, and 19.0. Per-branch test workflows green on every
branch; 49 unit tests pass on real Odoo + Postgres in Docker.

What works on every branch:

- Real destination-based per-jurisdiction US sales tax on every
  customer invoice, sale order, credit note (state / county / city /
  district splits in the totals area)
- Line-level OST jurisdiction tags persisted on posted invoices
- Engine audit JSON captured on `_post()` (engine version, calc
  timestamp, full per-jurisdiction detail)
- Per-product + per-category OST taxability mapping
- Per-worker engine-response cache (~1h sliding TTL)
- Customer exemption certificate handling
- Multi-company isolation
- Settings page + Test Connection action
- Optional admin debug log
- Optional 90-day archive cron for jurisdictions you've stopped
  shipping to

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
