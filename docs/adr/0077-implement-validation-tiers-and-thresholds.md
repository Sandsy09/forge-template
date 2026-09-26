# 77. Implement validation tiers and thresholds

Date: 2026-09-26

## Status

Accepted

## Context

[FT-26.02](https://github.com/Sandsy09/forge-template/issues/198): ADR 0076
approved budgets, five tiers, a noise rule and a path-sensitive escalation
*design*, and deliberately changed no CI. This issue implements them without
weakening any required check, and must show the exhaustive tier cannot be
skipped silently.

Facts that shaped the implementation:

- A caller job of a reusable workflow reports `success` even when every inner
  job was *skipped*. Making the sweeps conditional would therefore have let
  `All checks passed` go green with no sweep run, unless the gate checks for it.
- Both sweeps parametrise by composition slug, so a JUnit file names exactly
  which compositions executed, which is stronger evidence than a count.
- Real failed and cancelled runs from history show the shape to classify: a
  test failure fails in the check step (`Schema and unit tests`), a cancellation
  has no failing step, and the aggregate `All checks passed` job also fails as
  a consequence.

Decisions taken with the maintainer: pull requests use path-sensitive sweeps
(ADR 0076), and a release verifies its own commit's `Test template` run rather
than re-running the sweeps inside `release.yml`.

## Decision

1. **A fail-closed classifier decides.** `scripts/classify_changes.py` reads the
   `[escalation]` table of `.github/validation-budgets.toml`. `push`,
   `schedule` and `workflow_dispatch` always require the sweeps. A pull request
   requires them when it changes a sensitive path. Anything that stops it
   proving a pull request insensitive (an unreadable file, a git failure, an
   empty diff, a missing base, an unrecognised event) requires them. The Linux
   call skips them only for the literal output `false`, and the `sweeps` input
   defaults to true. The canary always runs the full set.
2. **Coverage is proved by name.** Each sweep writes JUnit XML and
   `validation_report.py verify-sweep` compares the compositions that executed
   with the catalogue's valid set, failing on any missing, unexpected,
   duplicated, skipped or failed composition or any other failing test in the
   file. It publishes the executed count and the runner CPU as job outputs.
3. **The gate proves a required sweep ran.** A new `budget` job, which
   `All checks passed` needs together with `classify`, fails if the sweeps were
   required and a sweep job was skipped or missing or reports an executed count
   other than the valid count. This closes the reusable-workflow gap above.
4. **Thresholds apply the approved rule.** `budget` reads this run and the
   previous two successful `main` runs from the Actions API. `WARN` needs 2 of
   the last 3 above `warn`; `FAIL` needs the run above `fail` and the median of
   3 above `warn`, and fails the required check; a lone run above `fail` with a
   low median is an `OUTLIER`, reported and not failed. Attribution names the
   job, tier, multiple of baseline, dominant step, runner CPU and recent
   timings. The critical path is judged the same way against 16 / 20 minutes.
5. **Failures are classified by step.** Cancelled, lost-runner and setup-step
   failures (`Set up job`, checkout, `Install uv`, `Install dependencies`) are
   *infrastructure*, with the advice to rerun the failed job; any other failing
   step is a *test* failure, with the advice to fix the change. The aggregate
   gate and the report's own job are never reported as causes.
6. **A release verifies its own commit's run.** A read-only job that the release
   `needs` requires the newest `push` run for the release SHA to have succeeded
   with both sweep jobs `success`. It fails closed for no run, a run still going,
   a red run or a skipped or missing sweep, and no input bypasses it. *Rejected:*
   re-running both sweeps inside the release through a nested reusable workflow,
   which is stronger but adds about 11 minutes to every release and dry run,
   duplicates `main`'s work and renames the sweep jobs across the budgets file,
   the timing script and several pins.
7. **No new third-party action and no artifacts.** Evidence travels through job
   outputs, step summaries and the Actions API, with `actions: read` only on the
   two jobs that need it.
8. **Everything else is unchanged.** Only the two sweeps became conditional; the
   ADR 0076 tripwire that pinned them as unconditional is replaced by tests of
   the new wiring, and mutation checks prove each rule is enforced.

## Consequences

- A pull request that touches no sensitive path no longer waits for the sweeps
  (the critical path falls from about 13 minutes to the archetype job behind
  lint), while every sensitive change, `main`, the weekly run and every release
  still get the full matrix.
- A regression can now fail the required check. The noise rule keeps a single
  slower CPU from doing so, and a real failure attributes itself; an
  infrastructure failure is recognised and rerun, not debugged.
- The report depends on the Actions API and on the job display names in the
  budgets file; a rename must update both, and a pin enforces it.
- A release requires main's run for its commit to have finished, so releasing
  moments after a merge waits for CI. The evidence is the recorded run for that
  commit, not a fresh execution.
- Classification is step-level: a network failure inside a test step cannot be
  told from a test failure.
- No published artefact, template path, protocol, component or version changes,
  and nothing here is released.
