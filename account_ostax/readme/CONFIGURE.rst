After installing, configure per company under
**Settings → Accounting → OpenSalesTax**.

Minimum configuration (sales tax)
=================================

#. Enable **OpenSalesTax**.
#. Set the **Engine URL** (e.g. ``http://10.0.0.5:8080``).
#. (Optional) Set an **API key** if your engine requires Bearer auth.
#. Click **Test Connection**. You should see the engine version and
   DB status with the round-trip time.
#. Save.

That's it for sales tax. Create a US customer with a 5-digit ZIP, add
a sale order or invoice, and the connector engages automatically.

For non-US customers, assign the standard "Export — no US tax" fiscal
position. The connector only engages for partners with a US country
code and a valid 5-digit ZIP; non-US partners route through Odoo's
standard fiscal-position handling.

Recommended: per-state nexus filter
====================================

If you only collect tax in a subset of states, list them in
**States with nexus**. Out-of-state US customers will fall through
to catalog rates without an engine call. Empty (default) = engage
in all 50 states.

* The picker is scoped to ``country_id.code = 'US'``.
* A US customer record with no ``state_id`` is conservatively
  bypassed when nexus is set (the connector can't verify in-nexus
  without a state record). Either populate ``state_id`` or unset
  the nexus list.

Recommended: engine outage alerts
=================================

To catch silent fail-soft fallback before it shows up as a tax-report
reconciliation surprise:

#. **Engine outage alert recipients** — pick the users who should
   receive a ``mail.activity`` warning when the engine fails.
#. **Alert threshold (consecutive failures)** — default 5. After this
   many consecutive engine failures, the connector posts the warning
   activity to each recipient. Posted exactly once per
   threshold-crossing edge — no spam if the streak keeps climbing.

Read-only signals on the same settings block:

* **Last successful call** — timestamp; stale or unset = engine has
  been quiet.
* **Calls today** — count from the debug log (when enabled).
* **Failure streak** — current consecutive-failure counter; resets
  on next success.

Vendor bills (use-tax accrual) — opt-in
========================================

Default: **OFF.** Vendor bills bypass the connector and use Odoo's
catalog rates. Existing v0.1.x → v0.2.x users see no upgrade-day
behavior change.

To enable use-tax accrual at your nexus location:

#. **Use-tax address (buyer location)** — partner whose ZIP is the
   destination for engine calls on vendor bills. Falls back to the
   company's main address if unset.
#. **Use Tax Payable account** — a liability account that
   accumulates use-tax credits. Required when accrual is on; pick or
   create one in your chart that maps to the "Use Tax Payable" line
   on your state returns.
#. Toggle **Accrue use tax on vendor bills** ON.

The next vendor bill posted by a US partner will route through the
engine using your nexus ZIP. The synthetic taxes are
``type_tax_use='purchase'`` (separate from sales-tax synthetics) and
credit the configured Use Tax Payable account via repartition lines.

Per-product / per-category taxability
======================================

For most products, leave everything at the defaults — the engine
treats unflagged products as ``general`` taxable goods.

For products in special-taxability categories (clothing, groceries,
prescription drugs, prepared food, digital goods), set the category
on:

* **The product** — Inventory → Products → form view → Accounting
  tab → *OST tax category*, OR
* **The product's internal category** — Inventory → Configuration →
  Product Categories → form view → *OST tax category default*. Every
  descendant product inherits unless overridden (parent-walk).

Lookup precedence: per-product → product's category → walk up
``parent_id`` until a value is found → ``general``.

Customer exemption certificates
================================

For B2B / resale customers, set the exemption fields on
``res.partner``:

* **OST exemption certificate** — the certificate number from your
  customer
* **OST exemption type** — resale / government / nonprofit / other
* **OST exemption expiry** — optional date; past expiry, the
  certificate is ignored

Exempt partners short-circuit to zero tax in the connector — no
engine call. The certificate stays on the partner record for
audit; the merchant is responsible for keeping it current.

(Note: this short-circuit only applies to outbound flows. Use-tax
accrual on vendor bills doesn't honor a partner-side exemption — a
buyer's exemption certificate doesn't apply to use tax owed on a
purchase, which is a separate concern.)

Multi-company
=============

Each ``res.company`` has its own OpenSalesTax settings. Configure
each company independently — they can point at the same engine or
different engines.

Other settings
==============

* **Fail-soft on engine error** (default ON) — when the engine is
  unreachable or returns 5xx, fall back to the catalog rate and log
  a warning. Switch off once you trust connectivity to surface
  errors as ``UserError`` instead.
* **Debug log** — record the last 50 engine calls per company in a
  ring buffer, visible under Settings → Technical → OpenSalesTax →
  Recent calculations. Required for the "Calls today" telemetry to
  work.
* **Rate cache TTL (hours)** — informational; the actual cache is
  ``tools.ormcache``-backed with a ~1 hour sliding TTL via an
  hourly-bucket key component.

Bulk recompute action
=====================

After an engine rate-table change, refresh draft moves' breakdowns
without opening each one:

#. Filter ``account.move`` to ``state=Draft``.
#. Select the batch.
#. **Action → OpenSalesTax: bulk recompute drafts.**

Reports a one-line summary: "Recomputed: N. Skipped: M (not draft) +
K (OST not applicable)."
