After installing, configure per company:

#. Navigate to **Settings → Accounting → OpenSalesTax**.
#. Enable **OpenSalesTax**.
#. Set the **Engine URL** (e.g. ``http://10.0.0.5:8080``).
#. (Optional) Set an **API key** if your engine requires Bearer auth.
#. Set the **Origin address** to your nexus / shipping-origin partner.
#. Click **Test Connection**. You should see the engine version and DB status.
#. Save.

For non-US customers, assign the standard "Export — no US tax"
fiscal position. The connector only engages for partners with a US
country code and a valid 5-digit ZIP; non-US partners route through
Odoo's standard fiscal-position handling.

Multi-company
=============

Each ``res.company`` has its own OpenSalesTax settings. Configure each
company independently — they can point at the same engine or different
engines.

Customer exemption certificates
================================

For B2B / resale customers, set the exemption fields on
``res.partner``:

* **OST exemption certificate** — the certificate number from your
  customer
* **OST exemption type** — resale / government / nonprofit / other
* **OST exemption expiry** — optional date; past expiry, the
  certificate is ignored

The engine applies the exemption logic when these fields are set
on the customer.
