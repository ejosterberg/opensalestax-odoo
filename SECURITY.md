# Security Policy

## Reporting a vulnerability

Email **ejosterberg@gmail.com** with subject line starting
`[opensalestax-odoo] security:`. Include:

- Affected branch(es) (16.0 / 17.0 / 18.0 / 19.0)
- Reproduction steps
- Expected vs actual behavior
- Impact (read access? write access? RCE? data exposure?)
- Suggested mitigation if known

Do not open a public GitHub issue for security reports.

## Response time

Best-effort acknowledgement within 7 days. For critical vulnerabilities
affecting tax-calculation correctness or admin access, mark the email
subject with `[critical]` and expect faster turnaround.

## Supported versions

Each branch (16.0, 17.0, 18.0, 19.0) gets security patches independently.
Use the branch matching your Odoo install. There is no `main` branch.

## Security posture

The module is a thin override of Odoo's tax computation entry points
(`account.tax._add_tax_details_in_base_lines` on 18+, `compute_all`
on 16/17) plus settings fields, telemetry, and a few view extensions.
The attack surface is small but real:

- **The settings page accepts a merchant-supplied `ostax_api_url`.** This
  becomes the base URL for HTTP calls from the Odoo server. Merchants are
  expected to point it at their own OpenSalesTax engine — no SSRF
  mitigation is performed by the module. Run your engine on a private
  network if your Odoo box has access to internal services that
  shouldn't be reachable from the engine's URL.
- **Optional Bearer API key is stored in plaintext** in `res.company.ostax_api_key`
  (Odoo's standard `Char` field encryption). For high-stakes deployments,
  pin your engine to the Odoo server's IP via firewall rather than
  relying on the Bearer header alone.
- **The debug log captures request/response metadata** (origin ZIP,
  destination ZIP, total amount, response time). It does NOT capture
  partner names, line-item details, or PII. Disabled by default. Enable
  per-company in the settings if you need it.
- **Per-jurisdiction breakdown stored on `account.move` is not
  encrypted at rest.** Standard Odoo data-protection practice (DB-level
  encryption, restricted access) applies.

## Calculation correctness vs security

A miscalculated tax amount is not a security vulnerability per se — it's a
bug. Report bugs via the issue tracker with the `tax-correctness` label.
Vulnerabilities are: unauthorized read access, unauthorized write access,
authentication bypass, RCE, data exfiltration, or anything that lets an
attacker modify another tenant's tax records in a multi-company instance.
