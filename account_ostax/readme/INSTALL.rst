Prerequisites
=============

* Odoo 16.0, 17.0, 18.0, or 19.0 (Community or Enterprise)
* PostgreSQL — Odoo's standard for your major (15 for 16/17,
  16 for 18/19)
* Python 3.9+ (3.10+ recommended)
* A running OpenSalesTax engine reachable from the Odoo server.
  Self-host via Docker — see
  https://github.com/ejosterberg/open-sales-tax. Minimum engine
  version: **v0.22**; tested against v0.54.1+.

Install
=======

The same package serves all four Odoo majors via version-prefix
selectors. Pick the one matching your Odoo install:

::

    # The Python SDK (same on every branch):
    pip install opensalestax

    # The connector — pick ONE matching your Odoo major:
    pip install 'odoo-addon-account-ostax>=16.0.0.1.12,<17.0'  # Odoo 16
    pip install 'odoo-addon-account-ostax>=17.0,<18.0'         # Odoo 17
    pip install 'odoo-addon-account-ostax>=18.0,<19.0'         # Odoo 18
    pip install 'odoo-addon-account-ostax>=19.0,<20.0'         # Odoo 19

.. note::

   Odoo 16 users — the ``16.0.0.1.11`` wheel is broken (a
   ``tools.ormcache`` annotation-stripping bug, fixed in v0.1.12).
   Always pin ``>=16.0.0.1.12``.

Or from source — replace ``<NN.0>`` with your major:

::

    git clone -b <NN.0> https://github.com/ejosterberg/opensalestax-odoo.git
    # symlink or copy account_ostax/ into your addons-path

Then in Odoo: **Apps → search "OpenSalesTax" → Install**.
