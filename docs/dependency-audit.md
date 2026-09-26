# Dependency vulnerability audit

This is the canonical living contract for auditing `forge-template`'s **own
locked dependencies** for known vulnerabilities. [ADR
0075](adr/0075-audit-locked-dependencies-with-uv-audit.md) records the
decision. `scripts/audit_dependencies.py` implements it and
`tests/test_dependency_audit.py` pins it. It is the sibling of the [dependency
update policy](dependency-updates.md), which governs how updates *arrive*, and
of the [Action pinning policy](github-action-pinning.md).

A clean audit is not a claim that the dependencies are secure. It says only that
no advisory in the queried database matches a locked version, at the time of
the query.

## What is audited

The audit reads `uv.lock` and covers two scopes, reported separately:

| Scope | What it is | Packages (2026-09-26) |
| --- | --- | --- |
| `runtime` | `[project.dependencies]` and everything they lock: the graph the published wheel depends on. Findings here are provider-actionable. | 8: `annotated-types`, `jinja2`, `markupsafe`, `packaging`, `pydantic`, `pydantic-core`, `typing-extensions`, `typing-inspection` |
| `full` | The runtime graph plus every dependency group: `lint`, `test`, `typecheck` and `dev`. The additions are CI-only. | 79 |

There are no optional extras. Development-only findings are reported and fail
the audit like any other, but they are labelled `[full]` and carry no
lower-bound hint, because they never reach a consumer.

**Not audited here:** dependencies rendered into generated projects (each
project scans its own), the direct-Copier template, pre-commit hook revisions,
and GitHub Actions (governed by [the pinning policy](github-action-pinning.md)).

## Scanner and coverage

The scanner is `uv audit` (preview), which resolves the lock and queries
[OSV](https://osv.dev). CI pins `UV_VERSION` exactly, so the interface a run
sees is the interface the tests were written against; both uv `0.12.0` (the
pin) and `0.12.5` were verified.

- **Python and platform markers.** `uv.lock` is universal, so the audit covers
  every package the lock can install on any supported Python and platform,
  including marker-gated ones such as `appnope` (macOS only). It does not audit
  a single interpreter's installed environment.
- **Advisory data version.** OSV is queried live and has no snapshot version, so
  a run cannot be reproduced later. Each run therefore records the scanner
  version (`uv --version`), the UTC query time, the service host, the audited
  package counts per scope and, for every finding, the advisory's own `modified`
  timestamp. The job log and step summary are the evidence.
- **No credential-bearing output.** The script never prints the environment,
  and strips `scheme://user:password@` and query strings from everything it
  echoes, including the service host.

### Why the scope is derived and cross-checked

`uv audit --no-default-groups` and `--only-dev` are **silently ineffective**
(verified on uv 0.12.0 and 0.12.5): both still audit all 79 packages. Only
`--no-group <name>` narrows the audit reliably. Trusting those flags would have
produced a "runtime" audit that was really the whole graph.

So the runtime audit passes `--no-group` for every group read from
`[dependency-groups]` in `pyproject.toml` (adding a group narrows it
automatically), and each scope's `audited_packages` is compared with an
independent lock-only count from `uv export` (8 and 79 today). A mismatch fails
closed as **audit scope drift**.

## Outcomes

`uv audit` exits `0` clean, `1` with findings and `2` on any error. The wrapper
separates the error class:

| Outcome | Meaning | Exit |
| --- | --- | --- |
| Clean | No unsuppressed findings in either scope | `0` |
| Findings | An unsuppressed advisory matches a locked version | `1` |
| Service outage | uv could not reach OSV (`Request failed after`, `error sending request`) | `0` under `--on-outage warn`, else `1`; never reported as clean |
| Tool error | Any other failure, including a stale lock and any unrecognised exit `2` | `1`, always |
| Interface or scope drift | Unexpected JSON schema, a missing key, exit code and report disagreeing, or a scope-size mismatch | `1`, always |
| Invalid exceptions file | See below | `1`, always |

Only the recognised outage text can be downgraded; every other failure is a
tool error, so a new failure mode fails rather than passes. Identity fields
(`id`, `aliases`, `fix_versions`, the dependency name and version) are strict.
Descriptive fields may be null, because OSV sometimes omits them. `adverse
statuses` (for example a deprecated package) are opaque: printed as warnings and
never failing.

Every finding prints its advisory ID and aliases, package and locked version,
fix versions with the command to apply one, and the advisory link. When no fixed
version exists it says so and names the two choices: a reviewed exception, or
replacing the dependency. Fixed or not, an unsuppressed finding fails.

## Enforcement

| Surface | Runs | Findings | Service outage |
| --- | --- | --- | --- |
| Pull request, push to `main` | `audit` job in `test-template.yml`, part of `All checks passed` | fail | warn, loudly: annotation and job summary say the audit did **not** run |
| Weekly schedule (Monday 06:00 UTC), manual dispatch | same job | fail | fail |
| Release (`release.yml`, dry run included) | `audit` job that `release` needs | fail | fail; **no input bypasses it**, rerun once the service is back |
| Locally | `uv run poe audit` (needs network) | fail | fail unless `-- --on-outage warn` |

An outage warns on a pull request because it is not that change's fault and is
not a clean result either, so it is reported rather than hidden. The schedule
exists precisely to make a persistent outage visible. A new advisory on an
unrelated dependency will fail pull requests until it is fixed or excepted;
that is the gate working, and the response is the remediation below.

The audit is not part of `linux-checks.yml`. It does not depend on the runner
image, so the [runner canary](ci-runner-baseline.md) would only repeat it.

## Exceptions

`.github/audit-exceptions.toml` is the only way to accept a finding, and it
ships empty. Each `[[exception]]` needs `id` (one advisory ID or alias),
`package`, `rationale`, `owner`, `added` and `expires`. Anything else is
rejected, and the audit then fails closed:

- one literal package and one literal advisory, never a wildcard;
- unknown or missing keys, non-string text, non-date dates;
- `added` in the future, or `expires` before `added`;
- a lifetime over **90 days**. Re-review and renew instead of extending.

`expires` is the last day the exception applies. After it the finding fails
again and the output names the lapsed exception. An entry that matches no
current finding is reported as stale and should be removed. An exception is
reviewed like code, in the pull request that adds it; the `owner` is who
re-reviews it before it expires. Prefer fixing the dependency.

## Remediation

1. Read the finding: package, locked version, fix versions, advisory.
2. Fix it: `uv lock --upgrade-package <name>`, then `uv run poe check` and the
   slow suites the changed dependency maps to in [the update
   policy](dependency-updates.md#reviewing-a-proposed-update).
3. No fixed version: add a reviewed, expiring exception, or replace the
   dependency. Never suppress more broadly than one package and one advisory.
4. For a `[runtime]` finding, do the lower-bound review below.

## Lower-bound review

A lock-only upgrade fixes the audited graph. It does **not** by itself change
what the published wheel permits: `[project.dependencies]` keeps its declared
floor, so a consumer whose resolver picks the floor can still install a
vulnerable version.

For a runtime finding, ask whether the declared floor still *permits* the
vulnerable range. If it does and the vulnerability matters to consumers, raising
the floor is a **compatibility decision** under [the compatibility
policy](compatibility-policy.md), taken deliberately and released as a normal
change, not a side effect of the lock refresh. If it does not matter to
consumers, record why in the pull request. A lock-only upgrade is never
automatically a change to a published support floor.

## Provider and client boundary

Each repository owns its own scanning. `create-forge` audits its installed
graph, which includes `forge-template`; this repository audits its own lock and
owns the fix when a finding is in a provider constraint (a floor here, or a
patched release). Neither repository copies the other's pipeline, and this
repository does not scan generated projects.

## Maintaining the pin

`UV_VERSION` appears in `test-template.yml`, `linux-checks.yml` and
`release.yml` and is not updated by Dependabot. Because `uv audit` is preview,
moving it is a deliberate change: run `uv run poe audit`, confirm the scope
cross-check still reports 8 and 79, and let the tests re-verify the JSON schema.
A uv change that moves the interface fails the audit visibly instead of
passing quietly.

## Exclusions

No automatic dependency upgrades, no broad suppressions, no
generated-project scanning product, and no claim that a clean audit proves
security.

## Evidence

Recorded for FT-24.02 ([#192](https://github.com/Sandsy09/forge-template/issues/192)),
run locally on 2026-09-26 with the real scanner on both uv `0.12.5` and the
pinned `0.12.0`:

| Case | Result |
| --- | --- |
| This repository | exit `0`; runtime 8 packages, full 79, both clean |
| Probe project pinned to `jinja2==3.1.2` and `urllib3==1.26.4` | exit `1`; 28 findings listed with fix versions and remediation |
| Unreachable service, `--on-outage warn` | exit `0`, "NOT A CLEAN RESULT" |
| Unreachable service, `--on-outage fail` | exit `1` |
| Stale lock | exit `1`, a tool error even under `warn` |

The recorded JSON fixtures under `tests/fixtures/dependency_audit/` are real
`uv audit` 0.12.0 output. The real run also showed that some OSV entries have a
null `summary`, which is why descriptive fields tolerate null.
