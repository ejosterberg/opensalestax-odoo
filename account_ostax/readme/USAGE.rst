Once configured, the connector engages automatically on outbound
flows when the customer is in the US with a valid 5-digit ZIP:

* **Sales orders** — tax computes on quote / SO confirmation
* **Customer invoices** — tax computes on draft / confirmation
* **Credit notes / refunds** — sign-flips the original per-jurisdiction
  breakdown
* **POS orders** — server-authoritative compute at order close
  (per-line live JS quote is a v0.2 enhancement)

Inbound flows currently bypass the connector:

* **Vendor bills, vendor refunds, purchase orders** — fall through to
  Odoo's standard catalog-rate handling. Use-tax accrual at the
  buyer's location lands in v0.2.

Each transaction stores its per-jurisdiction breakdown in
``ostax_breakdown`` on the parent record (move / SO / POS order).
Open the record's form view and look for the **OpenSalesTax** tab.

Per-product taxability category
================================

For products in special-taxability categories (clothing, groceries,
prescription drugs, prepared food, digital goods), set the category
on:

* The product itself — Inventory → Products → form view → Accounting
  tab → **OST tax category**, OR
* The product's internal category — Inventory → Configuration →
  Product Categories → form view → **OST tax category default**

The lookup precedence is:

#. ``product.product_tmpl_id.ostax_category`` — per-product override
#. closest-ancestor ``product.category.ostax_category`` (walks
   ``parent_id`` until a value is found)
#. fall back to ``"general"``

The engine applies per-state taxability rules based on the chosen
category — Minnesota exempts clothing, New York taxes prepared food
differently than groceries, etc.

Audit trail
============

Posting an invoice writes the engine's per-jurisdiction breakdown
(state / county / city / district amounts, engine version, calc
timestamp) to the move's **OpenSalesTax** notebook tab. The data
also feeds Odoo's standard tax-line records, so reports under
**Accounting → Reporting → Audit Reports → Tax Report** show the
same per-jurisdiction breakdown.

Disclaimer
==========

Tax calculations are provided as-is for convenience. The merchant is
solely responsible for tax-collection accuracy and remittance to the
appropriate jurisdictions. Verify against your state Department of
Revenue before remitting.

This module does NOT file returns, remit collected tax, validate
addresses, or provide legal/tax advice.
