# 75. Audit locked dependencies with uv audit

Date: 2026-09-26

## Status

Accepted

## Context

[FT-24.02](https://github.com/Sandsy09/forge-template/issues/192): Dependabot
and Action pinning existed, but nothing checked the repository's resolved
dependencies against known vulnerabilities, so a vulnerable locked version
could be merged, or sit in `uv.lock`, unnoticed. The sibling `create-forge`
repository owns its own audit under CF-24.02 and no pipeline is shared.

Two scanners were viable for a `uv`-managed repository. `pip-audit` is
PyPA-maintained and stable, but it cannot read `uv.lock`: CI would `uv export` a
requirements file first, a second artefact that can drift from the lock, and
`pip-audit` would become a development dependency. `uv audit` audits the lock
directly, adds no dependency and exits `0` clean, `1` with findings and `2` on
error, but it is **preview**: the command warns on every run, and its JSON
`schema.version` is `preview`. Both `0.12.0` (the version CI pins) and `0.12.5`
were exercised against this lock, a known-vulnerable probe project, an
unreachable service and a stale lock.

Running it also showed three things a design must not ignore. `--no-default-groups`
and `--only-dev` do not narrow the audit at all (all 79 locked packages are
audited regardless), while `--no-group <name>` does, so a "runtime" audit built
on the obvious flag would silently cover the whole graph. OSV entries can have a
null `summary`. And uv has no notion of an exception's owner, rationale or
expiry.

## Decision

1. **Use `uv audit`, pinned and fail-closed.** CI keeps pinning `UV_VERSION`. The
   wrapper `scripts/audit_dependencies.py` accepts exactly the `preview` schema,
   treats the identity fields (`id`, `aliases`, `fix_versions`, dependency name
   and version) as strict and descriptive fields as nullable, and fails closed
   on any other drift. *Rejected:* `pip-audit` via `uv export`, for the drifting
   second artefact and the new dependency.
2. **Derive and cross-check the scope.** The runtime audit passes `--no-group`
   for every group read from `pyproject.toml`; each scope's `audited_packages`
   must equal an independent lock-only `uv export` count, or the run fails as
   scope drift.
3. **Separate the outcomes.** Clean, findings, service outage and tool error are
   distinct. Only recognised connection text is an outage; every other failure
   is a tool error and always fails, so an unknown failure mode cannot pass.
4. **Enforcement per surface.** Pull requests and pushes fail on unsuppressed
   findings and only warn on an outage, loudly and never as clean. The weekly
   schedule and manual dispatch fail on both. The release fails on both, through
   a `release` job that `needs` a read-only `audit` job, with no bypass input.
   The audit joins `All checks passed`.
5. **Exceptions are reviewed, scoped and expiring.** `.github/audit-exceptions.toml`
   ships empty; each entry names one package and one advisory, an owner and a
   rationale, and lives at most 90 days. An expired exception stops suppressing;
   an invalid file fails the audit. *Rejected:* uv's own `--ignore`, which has
   no expiry, owner or rationale.
6. **The audit lives in the repository, not the wheel.** It is a `scripts/`
   module like `labels.py` and `check_wheel.py`, so the published package
   boundary and its list of check-only modules do not change.
7. **Each repository scans itself.** `create-forge` audits its installed graph,
   including `forge-template`; this repository owns fixes to provider
   constraints. No pipeline is copied, and generated projects are not scanned.
8. **A lock upgrade is not a floor change.** Remediation includes a lower-bound
   review, and raising a published floor is a compatibility decision under the
   compatibility policy.

## Consequences

- A vulnerable locked version now fails the pull request that introduces it and
  the weekly run that discovers it. An advisory published against an unrelated
  dependency will fail pull requests until it is fixed or excepted.
- The audit depends on a preview command. Moving `UV_VERSION` is a deliberate,
  manual change (Dependabot does not track it) that must re-run `poe audit` and
  re-verify the scope check; a moved interface fails visibly.
- OSV has no snapshot version, so a run cannot be reproduced later; evidence is
  the recorded scanner version, query time and per-finding `modified` time.
- A persistent OSV outage fails the schedule and blocks releases until the
  service returns, by design.
- No published artefact, template path, protocol, component or version changes,
  and nothing here is released.
