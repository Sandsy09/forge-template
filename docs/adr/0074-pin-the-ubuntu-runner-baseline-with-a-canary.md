# 74. Pin the Ubuntu runner baseline with a canary

Date: 2026-09-25

## Status

Accepted

## Context

[FT-24.01](https://github.com/Sandsy09/forge-template/issues/191): every Linux
job in `test-template.yml` and `release.yml` named `runs-on: ubuntu-latest`,
so the effective baseline was whatever GitHub currently pointed that alias at.
The 17 September 2026 announcement
([changelog](https://github.blog/changelog/2026-09-17-ubuntu-26-generally-available-and-latest-migration/),
[runner-images #14747](https://github.com/actions/runner-images/issues/14747)
and [#14748](https://github.com/actions/runner-images/issues/14748)) made
Ubuntu 26.04 generally available and said `ubuntu-latest` moves to it,
gradually, between 19 October and 19 November 2026. The review's 19 October
date is therefore the start of a month-long window, not a cut-over day, and
GitHub states no end-of-support date for 24.04.

Observed before this change (`main` run 35741510636 and release run
35539758128): every Ubuntu job resolved to `ubuntu-24.04`, `windows-latest`
to `windows-2025-vs2026`. The only required check is `All checks passed`.

The sibling `create-forge` repository settled the same question in its
ADR 0058 with a reusable Linux workflow called twice: once pinned, once on
the next image with no aggregate job. Both repositories are consumed together,
so the same shape keeps their CI predictable in the same way.

## Decision

1. **Pin every protected Ubuntu job to `ubuntu-24.04`.** The `linux` call and
   the `all-green` aggregate in `test-template.yml`, and both jobs in
   `release.yml`. Pinning is per image, so routine image updates still apply;
   only the operating system stops moving without a reviewed commit.
   *Rejected:* pinning to `ubuntu-26.04` now. The image is generally
   available, but promoting it before the checks have run against it, on the
   scheduled cadence, would make the required gate the first place a
   difference surfaces.
2. **Add a non-blocking `ubuntu-26.04` canary running the identical checks.**
   The eight Linux jobs move into a reusable `linux-checks.yml` taking a
   `runner` input. `test-template.yml` calls it with the baseline and
   `runner-canary.yml` with the candidate. The canary has no aggregate job,
   is not a `needs` of anything and cannot produce the `All checks passed`
   context, so a red canary is a triage signal, not a blocked merge.
   *Rejected:* a slimmer standalone canary. It would omit the sweeps and the
   released-client check and could drift from what the gate requires.
3. **Keep `release.yml` out of the canary.** It holds `contents: write` and
   `id-token: write`; the checks that protect a release are the canary's
   scope.
4. **Keep least privilege and the pins.** Every workflow stays read-only at
   workflow level, `publish` alone gets `id-token`, and the SHA-pinning policy
   is unchanged. The reusable workflow repeats `UV_VERSION` because `env` does
   not cross `workflow_call`.
5. **Enforce it.** `check_runner_labels` rejects `ubuntu-latest` in `runs-on`
   and in a reusable-workflow caller's `runner` input, run by
   `schema.check_all()`. `tests/test_runner_baseline.py` derives the expected
   labels from the contract's `Baseline` and `Canary` rows.
6. **Do not touch generated workflows.** The `github` platform and the
   direct-Copier template still generate `ubuntu-latest`. Moving a user's
   project baseline needs its own compatibility decision, and a test pins the
   exclusion.
7. **Promotion is a documented, criteria-driven pull request** (green on
   `main` HEAD and on four consecutive Monday scheduled runs, no open
   canary issue, `scaffold`/`archetype`/`update-compat`/`wheel` counted),
   rolled back by reverting it. `docs/ci-runner-baseline.md` owns the
   criteria, ownership and rollback; following them needs no new ADR.

## Consequences

- Merges are gated on `ubuntu-24.04` regardless of when GitHub moves
  `ubuntu-latest`; a 26.04 incompatibility shows up in the canary first.
- The Windows smoke job no longer waits on lint: a job cannot depend on a job
  inside a called workflow. It is cheap and independent, so this costs only
  the early stop, and `All checks passed` still requires both.
- CI runs the Linux checks twice per trigger, doubling the Linux minutes.
  The repository is public, so this is free, and it is what keeps the canary
  identical to the gate.
- `windows-latest` remains a moving alias, tracked as a follow-up; the
  promotion itself is tracked separately. Neither changes any released
  behaviour.
- No published artefact, template path, protocol, component or version
  changes; nothing here is released.
