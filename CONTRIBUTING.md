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

Bug fixes that affect multiple Odoo majors should be backported as separate
PRs, one per branch.

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

By contributing, you agree your contribution is licensed under
**LGPL-3-or-later** (the project license; see [LICENSE](LICENSE) and the
SPDX header on every source file).

If this connector is later submitted upstream to OCA, the maintainer
will relicense to AGPL-3 to match OCA's submission requirements. By
contributing under LGPL-3-or-later, you implicitly authorize that
relicensing for OCA submission.

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

(For 17.0 / 16.0 use the matching `oca-ci` image tag.)

## Writing migration scripts

If you change a persisted-data schema (e.g. add or rename a field on
`account.move`), add a corresponding `migrations/<full-version>/` directory
per [OCA's migration convention](https://github.com/OCA/maintainer-tools/blob/master/MIGRATION-RULES.md).

## Reporting security issues

See [`SECURITY.md`](SECURITY.md). Don't open public issues for security
reports.
