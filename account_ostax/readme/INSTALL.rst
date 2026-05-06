Prerequisites
=============

* Odoo 18.0 (Community or Enterprise)
* PostgreSQL 16 (Odoo 18's standard)
* Python 3.10+
* A running OpenSalesTax engine reachable from the Odoo server.
  Self-host via Docker — see https://github.com/ejosterberg/open-sales-tax

Install
=======

::

    pip install odoo-addon-account-ostax==18.0.0.1.0

Or from source:

::

    git clone -b 18.0 https://github.com/ejosterberg/opensalestax-odoo.git
    # symlink or copy account_ostax/ into your addons-path

Then in Odoo: **Apps → search "OpenSalesTax" → Install**.
