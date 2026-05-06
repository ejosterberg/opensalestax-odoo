# Security review — v0.1.0-alpha

> Snapshot 2026-05-06. Re-run before each minor release.

## Scope

`account_ostax` Odoo module (LGPL-3) + its dependency on
`opensalestax` (Apache 2.0 SDK).

## Threat model — what we're defending

The module:

- Reads merchant-configured `ostax_api_url` and makes outbound HTTP
  calls
- Optionally forwards a Bearer `ostax_api_key` to the engine
- Captures partner ZIP / invoice totals into a JSON blob
- Materializes synthetic `account.tax` records on first use
- Writes opt-in debug log entries into `ostax.calc.log`

We're defending against: SSRF via merchant-supplied URL, credential
leakage in logs, unauthorized cross-company data access, malformed
engine responses crashing Odoo, and accidental privilege escalation
via tax-rate spoofing.

## Findings

### 1. SSRF surface — accepted, documented

`ostax_api_url` is merchant-supplied and used as the base URL for
HTTP calls from the Odoo server. **No SSRF mitigation is performed
by the module.** Merchants are expected to point the URL at their own
OpenSalesTax engine.

**Mitigation:** documented in [`SECURITY.md`](SECURITY.md). Run the
engine on a private network if your Odoo server has access to
internal services that shouldn't be reachable from the engine's URL.

### 2. API key storage — plaintext in `res.company`

`ostax_api_key` is stored as a `Char` field on `res.company`. Odoo
applies standard DB encryption (whatever the deployment's pgcrypto
config provides) but the field itself is not specially encrypted.

**Mitigation:** for high-stakes deployments, pin the engine to the
Odoo server's IP via firewall rather than relying on the Bearer
header alone. The settings UI uses `password="True"` so the value is
masked in the form.

### 3. TLS — handled by SDK; verify ON by default

The `opensalestax` SDK uses `httpx` with TLS verification enabled by
default. Disabling requires an explicit `verify=False` argument that
emits a `RuntimeWarning`. The Odoo module never disables verification.

### 4. Timeouts — always set

The SDK uses a 10-second default timeout on all requests. The module
doesn't override this. No risk of infinite hangs.

### 5. Multi-company isolation — scoped

All settings (`ostax_api_url`, `ostax_api_key`, etc.) are on
`res.company`. Synthetic tax records are scoped to `company_id`. The
`_ostax_should_engage()` check uses the line's `company_id`, falling
back to `self.env.company` only for empty recordsets. **Verified by
unit tests.**

### 6. Debug log content — no PII captured

`ostax.calc.log` records: timestamp, kind (engine_call/cache_hit/error),
origin_zip, dest_zip, total_amount (USD), engine_version, response_ms,
optional error_message. **No partner names, no line-item details, no
exemption certificate numbers.** Disabled by default; opt-in per
company.

### 7. XSS — breakdown JSON rendered as plain text

The form-view tab renders `ostax_breakdown` via `widget="text"` in a
read-only field. JSON is HTML-escaped by Odoo's standard rendering;
no `widget="html"` anywhere. Engine-supplied jurisdiction names go
through this same path.

### 8. Synthetic tax-record privilege — admin-only

The materialization runs in `sudo()`. The CSV at
`security/ir.model.access.csv` grants only the system admin
group write access to `ostax.calc.log`; standard users can read.
Synthetic `account.tax` records inherit the standard tax model's
ACL — same as any other tax record.

### 9. Calculation correctness vs security

A miscalculated tax amount is a bug, not a vulnerability. Engine
responses are validated against the SDK's pydantic models;
malformed responses raise `OpenSalesTaxValidationError` which the
module catches and either fails-soft (catalog fallback) or surfaces
as `UserError` per company config.

### 10. Dependency posture

| Dependency | Version | Source |
|---|---|---|
| `opensalestax` | `==0.1.0` (pinned via manifest) | PyPI; Apache 2.0 |
| `httpx` (transitive) | `>=0.27` | PyPI; BSD-3 |
| `pydantic` (transitive) | `>=2.5` | PyPI; MIT |

No known CVEs at time of review. Run `pip-audit` periodically.

## Out of scope for v0.1.0-alpha

- Vendor-side use-tax accrual (deferred to v0.1.0 stable / v0.2)
- POS live-quote round-trips (deferred to v0.2)
- Encryption-at-rest for the API key field (relies on standard Odoo
  DB-level encryption)
- Rate-limiting outbound engine calls (engine is presumed
  merchant-owned and trusted)
