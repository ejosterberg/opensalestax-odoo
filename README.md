# opensalestax-odoo

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](LICENSE)
[![Odoo 16.0](https://img.shields.io/badge/Odoo-16.0-714B67.svg)](https://github.com/ejosterberg/opensalestax-odoo/tree/16.0)
[![Odoo 17.0](https://img.shields.io/badge/Odoo-17.0-714B67.svg)](https://github.com/ejosterberg/opensalestax-odoo/tree/17.0)
[![Odoo 18.0](https://img.shields.io/badge/Odoo-18.0-714B67.svg)](https://github.com/ejosterberg/opensalestax-odoo/tree/18.0)

**Destination-based US sales tax for Odoo Community.** Replaces static tax-rate
configuration with live calculation against an
[OpenSalesTax](https://github.com/ejosterberg/open-sales-tax) engine — your own
self-hosted instance, no per-transaction fees, no SaaS lock-in.

The free, self-hostable answer to Avalara on Odoo Community.

## Branch matrix

This repo follows the OCA convention: **one branch per Odoo major version.**
Pick the branch matching your Odoo install. Releases are independent per branch.

| Odoo version | Branch | PyPI artifact |
|---|---|---|
| 16.0 | [`16.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/16.0) | `odoo-addon-account-ostax==16.0.*` |
| 17.0 | [`17.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/17.0) | `odoo-addon-account-ostax==17.0.*` |
| 18.0 | [`18.0`](https://github.com/ejosterberg/opensalestax-odoo/tree/18.0) | `odoo-addon-account-ostax==18.0.*` |
| 19.0 | _planned for v0.2 at GA (~Oct 2026)_ | — |

## What you get

- Sales orders, customer invoices, credit notes/refunds, vendor bills, POS,
  purchase orders — all with destination-based per-jurisdiction US tax
- Per-jurisdiction breakdown stored on every move (state / county / city /
  district), rendered on the form view for full audit trail
- Customer exemption certificates on `res.partner`
- Multi-company support — settings scoped per company
- Fiscal-position interop — non-US partners route through Odoo's standard
  "Export" mapping; the connector only engages for US shipping addresses
- Settings page with engine connection test, cache TTL, fail-soft toggle
- Optional admin debug log of recent calculations

## Install

```bash
# Match the branch to your Odoo major:
pip install opensalestax  # the Python SDK
pip install odoo-addon-account-ostax==18.0.0.1.0  # this connector for Odoo 18

# Or install from source:
git clone -b 18.0 https://github.com/ejosterberg/opensalestax-odoo.git
cd opensalestax-odoo
# Symlink or copy account_ostax/ into your Odoo addons-path
```

Then in Odoo: **Apps → search "OpenSalesTax" → Install**, then
**Settings → Accounting → OpenSalesTax** to configure the engine URL.

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

**18.0 branch — `v0.1.0` shipped 2026-05-06.** Production-grade.

The release closes the alpha gap: invoice tax replacement on Odoo 18
now works end-to-end via the canonical `_add_tax_details_in_base_lines`
hook. A merchant deploying this gets correct destination-based US
sales tax on every customer invoice, credit note, and sale order,
with per-jurisdiction tax lines (state / county / city / district)
visible on the form and engine audit JSON in the OpenSalesTax tab.

Verified end-to-end on Odoo 18 + Postgres 16 + l10n_generic_coa:
$100 invoice to MSP (ZIP 55401) produces `amount_tax=9.03` with
6 jurisdiction lines. Refunds sign-flip correctly. 32 unit tests
pass.

17.0, 16.0, and 19.0 branches follow this same pattern (with
version-appropriate adjustments).

Production use case: the maintainer's own Odoo 16 install (currently
mid-migration to Odoo 19 + PostgreSQL on Debian 13 — see the
sibling project) will run this connector on the matching branch
once migration completes.
