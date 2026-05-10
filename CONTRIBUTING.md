# Contributing to opensalestax-odoo

## Branch model — OCA convention

This repo follows the [OCA](https://github.com/OCA) convention:
**one branch per Odoo major version.** When opening a PR, target the branch
that matches the Odoo version you're patching. Don't open a PR against
`main` — there is no `main`.

| Odoo version | Branch |
|---|---|
| 16.0 | `16.0` |
| 17.0 | `17.0` |
| 18.0 | `18.0` (default — what you see on the GitHub repo home) |
| 19.0 | `19.0` |

Bug fixes that affect multiple Odoo majors should be backported as separate
PRs, one per branch. The maintainer typically lands a patch on `18.0` first,
then cherry-picks to the other three branches.

## Developer Certificate of Origin (DCO)

Every commit must carry a DCO sign-off:

```bash
git commit -s -m "your message"
```

The `-s` flag appends a `Signed-off-by: Your Name <email>` trailer that
asserts you have the right to submit the contribution under the project
license. See [https://developercertificate.org](https://developercertificate.org).

## No AI co-author trailers

Do not add `Co-Authored-By:` trailers attributing AI assistants. Human
authors take responsibility for their contributions.

## License

By contributing, you agree your contribution is **dual-licensed
under your choice of LGPL-3.0-or-later OR AGPL-3.0-or-later**.

The dual license enables two distribution paths from a single
source:

* Self-hosted Odoo deployments embedding the connector typically
  pick **LGPL-3.0-or-later** (more permissive — does not propagate
  to the rest of an Odoo install).
* OCA upstream distribution via
  [`OCA/account-fiscal-rule`](https://github.com/OCA/account-fiscal-rule)
  picks **AGPL-3.0-or-later** (matches OCA's submission policy).

Recipient picks. See [`LICENSE`](LICENSE),
[`LICENSE-LGPL.txt`](LICENSE-LGPL.txt),
[`LICENSE-AGPL.txt`](LICENSE-AGPL.txt), and the SPDX header on
every source file (``LGPL-3.0-or-later OR AGPL-3.0-or-later``).

## Quality gate — before opening a PR

Run the same checks CI runs:

```bash
# Lint + format
ruff check account_ostax
ruff format --check account_ostax

# Per-branch test pipeline (uses OCA's CI image to mirror upstream-Odoo behavior)
docker run --rm -v "$PWD:/repo" \
  -w /repo \
  ghcr.io/oca/oca-ci/py3.11-odoo18.0:latest \
  bash -c 'oca_install_addons && oca_run_tests'
```

(For 16.0 / 17.0 / 19.0 use the matching `oca-ci` image tag.)

## Writing migration scripts

If you change a persisted-data schema (e.g. add or rename a field on
`account.move`), add a corresponding `migrations/<full-version>/` directory
per [OCA's migration convention](https://github.com/OCA/maintainer-tools/blob/master/MIGRATION-RULES.md).

## Reporting security issues

See [`SECURITY.md`](SECURITY.md). Don't open public issues for security
reports.
