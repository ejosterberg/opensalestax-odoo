Once configured, the connector engages automatically:

* **Sales orders** — tax computes on quote / SO confirmation
* **Customer invoices** — tax computes on draft / confirmation
* **Credit notes / refunds** — preserves the original breakdown
* **Vendor bills** — use-tax accrual based on the configured origin
* **POS orders** — server-authoritative compute at order close
* **Purchase orders** — same hook as vendor bills

Each transaction stores its per-jurisdiction breakdown in
``ostax_breakdown`` on the parent record (move / SO / PO / POS order).
Open the record's form view and look for the **OST breakdown** tab.

Disclaimer
==========

Tax calculations are provided as-is for convenience. The merchant is
solely responsible for tax-collection accuracy and remittance to the
appropriate jurisdictions. Verify against your state Department of
Revenue before remitting.

This module does NOT file returns, remit collected tax, validate
addresses, or provide legal/tax advice.
