Inspired by `OCA/account-fiscal-rule/account_avatax_oca
<https://github.com/OCA/account-fiscal-rule/tree/18.0/account_avatax_oca>`_
(AGPL-3) — license-clean reimplementation under LGPL-3-or-later. No
code is copied; only the structural pattern (override
``account.tax.compute_all`` conditionally on a per-company enable
flag) is shared with that module's design.

The OpenSalesTax engine and Python SDK are separate projects by the
same author, both Apache-2.0:

* `ejosterberg/open-sales-tax <https://github.com/ejosterberg/open-sales-tax>`_
* `ejosterberg/opensalestax-python <https://github.com/ejosterberg/opensalestax-python>`_
