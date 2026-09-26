# 76. Approve validation budgets and tiers

Date: 2026-09-26

## Status

Accepted

## Context

[FT-26.01](https://github.com/Sandsy09/forge-template/issues/197): the
composition catalogue grows multiplicatively, so validation cost had outpaced
any explicit runtime budget. The 21 September review reported 5,761 cases and
rising CI time; those were observations to remeasure, not constants.

Measured over the 25 successful runs from `d1de861` to `d0b3ec2`
(`docs/validation-budget.md`): 8,192 raw candidates, 2,880 valid and 5,312
rejected compositions; a run takes a median 13.0 minutes, whose critical path is
`Lint template` (2.5) then the independent-client sweep (10.5). The two sweeps
are about 58% of job-minutes and cost roughly 215 ms (independent client) and
104 ms (direct engine) per composition, so one more capability, which doubles
the count, would push the independent sweep to about 20.6 minutes.

The run-to-run spread is hardware, not code. Six deliberate measurement runs
showed the same job taking 10.5 to 10.7 minutes on an AMD EPYC 7763 and 7.5 to
7.7 on a 9V74, on identical 4-vCPU, 16 GB runners; memory peaked at 1.6 GB in
the sweeps and 3.5 GB in the archetype builds; and a cold uv cache changed
nothing measurable.

## Decision

1. **Approve numeric limits by a stated rule, checked against history.** Per
   job, `warn = 1.25 x` and `fail = 1.5 x` the baseline p90 (rounded up to 0.5
   minutes, floors 1.5 and 2.0), from a window of at least 20 successful runs.
   The PR critical path is approved at **warn 16 / fail 20 minutes** against a
   measured p90 of 13.3. With these numbers 0 of the 25 baseline runs would have
   warned or failed, while FT-20.03's 2.1 times step in the archetype job would
   have failed at once. *Rejected:* a tighter 14 / 16 critical-path budget,
   which ordinary hardware variance and a single added archetype would trip.
2. **Treat runner noise as hardware.** Baselines use the slow-CPU p90. A warning
   needs 2 of the last 3 runs above `warn`; a failure needs one run above `fail`
   and the median of the last 3 above `warn`, so one outlier cannot fail a build.
3. **Define five tiers and map every guarantee.** T0 fast, T1 project proof, T2
   exhaustive (direct-engine sweep), T3 independent client, T4 sibling-gated.
   Every guarantee class is mapped to a tier and to what pins it, and every
   workflow job and registered pytest marker belongs to exactly one tier.
   **Full accepted-composition coverage (T2 and T3) stays mandatory before a
   release** and is never sampled.
4. **Approve path-sensitive escalation as the design.** A pull request runs T2
   and T3 only when it changes a composition-sensitive path (the engine and
   content under `src/forge_template/` bar the four wheel-excluded check-only
   modules, the composition matrix and sweep tests, `tests/conftest.py`,
   `pyproject.toml`, `uv.lock`, the workflows). T2 and T3 always run on `main`,
   weekly, on manual dispatch and as a release gate. *Rejected:* sampling the
   independent-client sweep on pull requests, which would leave a sensitive
   change seeing only a fraction of the matrix.
5. **Guard growth.** A derived test projects the catalogue's cost and fails when
   it reaches a sweep's failure limit, so the next capability forces a tiering
   decision and a re-baseline instead of a quietly slower CI.
6. **Make the baseline reproducible.** `scripts/ci_timings.py` regenerates the
   figures from a run window, and the approved numbers live in
   `.github/validation-budgets.toml`, which FT-26.02 consumes.
7. **Change no CI here.** Every protected check stays until FT-26.02's
   replacement coverage is separately approved; a test pins that the sweeps are
   still unconditional. No release coverage is reduced and no performance work
   is done.

## Consequences

- Validation cost has an explicit, evidence-based budget and a trigger for when
  it must change, instead of a silent drift.
- Adding a capability or platform now fails the fast suite until the tier
  decision is made; this is intended, and the limit is not to be raised to make
  it pass.
- Thresholds are approved but not yet enforced: FT-26.02 implements the
  observability, the regression checks and the escalation.
- The baseline is tied to one hardware mix and one window; re-baselining is a
  reviewed change that re-runs the script.
- No published artefact, template path, protocol, component or version changes,
  and nothing here is released.
