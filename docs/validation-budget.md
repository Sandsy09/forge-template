# Validation budget

This is the canonical living contract for what `forge-template`'s validation
costs, what that cost may grow to, and which tier proves which guarantee.
[ADR 0076](adr/0076-approve-validation-budgets-and-tiers.md) records the
decision. The approved numbers live in
[.github/validation-budgets.toml](../.github/validation-budgets.toml);
`tests/test_validation_budget.py` pins that file to the catalogue, the
workflows and the rule below, and `scripts/ci_timings.py` reproduces every
measured figure here from the recorded runs.

The 5,761 cases and the timings in the 21 September review were starting
observations. The figures below are the re-measurement, tied to exact commits;
none is a permanent constant.

## Baseline

Window: the 25 successful `push`, `pull_request` and `schedule` runs of `Test
template` from `d1de861` (run 35475114537, 19 September 2026, the first with
FT-20.03's archetype cells) to `d0b3ec2` (run 36241783316, 26 September 2026).
Every measured Ubuntu job ran on `ubuntu-24.04` (image versions
`20260907.300.1` to `20260920.314.1`) on a 4-vCPU, 16 GB runner, with the
sweeps at `-n 4`. Reproduce it with:

```bash
uv run poe ci:timings -- --since 2026-09-19T23:00 --until 2026-09-26T12:30 \
    --events push pull_request schedule --steps
```

### Composition counts

The catalogue has 4 archetypes, 10 capabilities and 1 platform, so a selection
is one archetype, any subset of capabilities and either platform choice.
`tests/composition_matrix.py` derives the valid set from the components' own
`requires` and `conflicts` edges; the count is deterministic, sorted and unique
(pinned).

| | Count |
| --- | --- |
| Raw candidates (4 x 2^10 x 2^1) | 8,192 |
| Valid compositions | **2,880** |
| Rejected compositions | 5,312 |
| Valid per archetype | 640 `cli`, 320 `data-science`, 1,280 `library`, 640 `streamlit` |

Collected tests per marker at this catalogue: fast 930, `sweep` 5,761 (two
sweeps of 2,880 plus one tripwire), `archetype` 57, `combos` 4, `update` 3,
`cutover` 41, `crossrepo` 20.

### Wall time per job

Minutes of a job's own wall time, queueing excluded. The p90 is the baseline
each limit is derived from.

| Job | min | p50 | p90 | max |
| --- | --- | --- | --- | --- |
| Composition sweep, independent client | 6.1 | 10.5 | 10.6 | 10.8 |
| Composition sweep, direct engine | 2.6 | 5.2 | 5.3 | 5.3 |
| Archetype builds | 2.1 | 3.6 | 3.9 | 4.2 |
| Lint template (pre-commit and `poe check`) | 1.6 | 2.5 | 2.6 | 2.7 |
| Windows smoke | 1.4 | 1.6 | 2.0 | 2.0 |
| Four direct-Copier combinations | 0.4 | 0.5 to 0.8 | 0.6 to 0.9 | 0.7 to 0.9 |
| `copier update` compatibility | 0.7 | 0.8 | 0.9 | 1.4 |
| Released client, wheel contents | 0.2 | 0.2 to 0.3 | 0.3 | 0.3 |
| **Whole run (first start to last end)** | 8.1 | 13.0 | 13.3 | 13.5 |

### The dominant cost

The critical path is `Lint template` (2.5 min) followed by the **independent-
client sweep** (10.5 min): together the 13.0 minute run. The two sweeps are
about 58% of all job-minutes, and the independent-client sweep alone is about
38% of them and 81% of the run's wall time. Each composition costs roughly
**215 ms** in the independent-client sweep and **104 ms** in the direct-engine
sweep, so cost is proportional to the composition count.

### Growth of the count

The count grows multiplicatively: a capability or a platform with no
`requires` or `conflicts` doubles it.

| Change | Valid compositions | Independent sweep | Direct sweep |
| --- | --- | --- | --- |
| Today | 2,880 | 10.3 min | 5.0 min |
| One more archetype | about 3,900 | 13.9 min | 6.7 min |
| One more free capability or platform | about 5,760 | 20.6 min | 9.9 min |

### Runner noise is hardware

The same job on the same kind of runner varies with the CPU GitHub assigns.
Six throwaway measurement runs (commit `7a53355`, and `d5678956` with the uv
cache disabled; the branches are deleted, the runs remain) printed each heavy
job's CPU and time. Every runner reported 4 vCPUs and about 16 GB.

| CPU | Independent sweep | Direct sweep | Archetype builds |
| --- | --- | --- | --- |
| AMD EPYC 7763 (the common, slow case) | 10.5, 10.6, 10.7 | 5.2, 5.3, 5.4 | 3.9, 3.9, 3.9, 4.0 |
| Intel Xeon Platinum 8370C | 9.7 | | |
| AMD EPYC 9V74 | 7.5, 7.7 | | 3.2, 3.8 |
| AMD EPYC 9V45 | | 2.8, 3.2 | |
| Intel Xeon Platinum 8573C | | 4.5 | |

So a run is fast or slow because of hardware, not because of the code: the
worst same-CPU spread is under 5% for the sweeps, and a faster CPU only ever
makes a job faster. The hazard for a budget is therefore the slow-CPU ceiling,
not the fast outliers.

### Memory and cache

- **Memory.** Whole-machine used memory, sampled every 5 seconds, peaked at
  1.25 to 1.62 GB in the sweeps and 3.1 to 3.5 GB in the archetype builds, at
  most 22% of the runner's 16 GB. Memory is not a constraint, so no memory limit
  is set; it stays a recorded figure.
- **Cache.** Every sampled history run restored the uv cache (warm). A
  deliberate cold run, with the cache disabled, showed no measurable
  difference: `Install dependencies` took 3 seconds in warm and cold runs alike
  and `Install uv` 1 to 3 seconds, and its sweep times matched warm runs on the
  same CPU (10.6 against 10.5 and 10.7 minutes). Cache state is not a budget
  input.
- **Runner image.** The `ubuntu-26.04` canary ran the same jobs in the same
  range (independent sweep 5.5 to 10.7, direct 5.1 to 5.2, archetype 3.1 to
  4.1), but with only four runs it is informational, not a baseline.

## Approved budgets

**Per job.** `warn = 1.25 x` and `fail = 1.5 x` the baseline p90, each rounded
up to 0.5 minutes, with floors of 1.5 and 2.0 minutes so small jobs are not
policed on seconds. A job's baseline needs at least 20 successful runs from the
current window.

| Job | Baseline p90 | Warn | Fail |
| --- | --- | --- | --- |
| Independent-client sweep | 10.6 | 13.5 | 16.0 |
| Direct-engine sweep | 5.3 | 7.0 | 8.0 |
| Archetype builds | 3.9 | 5.0 | 6.0 |
| Lint template | 2.6 | 3.5 | 4.0 |
| Windows smoke | 2.0 | 2.5 | 3.0 |
| Every other job | 0.9 or less | 1.5 | 2.0 |

`Dependency audit` is provisional (2 runs) and uses the floors until it has a
real baseline.

**Critical path.** The PR critical path, first job start to last job end, is
approved at **warn 16 minutes, fail 20 minutes** against a measured p90 of 13.3
minutes.

**Noise treatment.** The baseline is the slow-CPU p90, so a normal slow run is
never a warning. A **warning** needs 2 of the last 3 runs above `warn`. A
**failure** needs one run above `fail` and the median of the last 3 above
`warn`, so one hardware outlier cannot fail a build but a real shift does.

**Why these numbers.** The limits were checked against history rather than
chosen by feel: with them, **0 of the 25 baseline runs** would have warned or
failed on any job (the script prints the counts). They are still sensitive to a
real shift: before FT-20.03 the archetype job's p90 was 1.9 minutes (5 runs), so
its limits would have been 2.5 and 3.0; its 3.6 minute p50 afterwards is about
2.1 times higher and would have failed at once.

## Tiers and guarantees

Each tier is a set of jobs and pytest markers; the machine-readable map is in
the budgets file and every workflow job and registered marker is pinned to
exactly one tier (`structural` jobs aside).

| Tier | Name | Runs | Proves |
| --- | --- | --- | --- |
| T0 | fast | `Lint template` (`poe check`, 930 tests, pre-commit) | static quality, contract pins |
| T1 | project proof | combos, archetype builds, `copier update`, wheel, released client, Windows smoke, audit | real generated projects, distributions |
| T2 | exhaustive | direct-engine sweep | every valid composition plans and renders |
| T3 | independent client | independent-client sweep | every valid composition renders from path-free facts |
| T4 | sibling-gated | `crossrepo`, `cutover` row 339 | pairing with a sibling `create-forge`; outside CI (ADR 0057) |

`tests/test_no_copy_inheritance.py` holds both fast tests (T0) and the
independent-client sweep (T3); the `cutover` marker covers the hermetic
released-client check (T1) and the sibling-gated pairing (T4).

| Guarantee | Tier | Pinned by |
| --- | --- | --- |
| `static-quality` | T0 | ruff and strict mypy (`pyproject.toml`) |
| `living-contracts` | T0 | `test_living_docs`, `test_compatibility_policy`, `test_adr` |
| `public-engine-api` | T0 | `test_engine`, `test_generation_provenance`, `test_cutover_gates`, `test_streamlit_gates` |
| `composition-rules` | T0 | `test_component_manifest`, `test_composition_contract`, `test_extension_points`, `test_platform_composition`, `test_parity_inventory` |
| `workflow-policy` | T0 | `test_github_actions`, `test_runner_baseline`, `test_dependency_audit`, `test_dependency_updates` |
| `direct-copier-projects` | T1 | `test_combos` |
| `copier-update` | T1 | `test_update` |
| `generated-project-proof` | T1 | `test_full_composition_build`, `test_streamlit_endpoints`, `test_scientific_python_capability_build` |
| `distribution-contents` | T1 | `scripts/check_wheel.py` |
| `released-client-compatibility` | T1 | `test_released_client_compatibility` |
| `dependency-vulnerabilities` | T1 | `scripts/audit_dependencies.py` |
| `windows-portability` | T1 | `test_combos` on Windows |
| `every-valid-composition-renders` | T2 | `test_composition_sweep` |
| `client-independence` | T3 | `test_no_copy_inheritance` |
| `cross-repository-pairing` | T4 | `test_cross_repository_validation`, `test_released_provider_cutover` |

**Full accepted-composition coverage stays mandatory before a release.** T2
and T3 are never sampled, shortened or dropped for a release.

## Escalation

Implemented by FT-26.02 ([ADR 0077](adr/0077-implement-validation-tiers-and-thresholds.md)).
Only the two sweeps (T2 and T3) can be skipped, and only on a pull request that
changes no composition-sensitive path. Every other check runs on every change,
and nothing else was weakened.

- **What is sensitive.** Anything under `src/forge_template/` except the four
  check-only modules the wheel excludes (`adr.py`, `github_actions.py`,
  `render.py`, `schema.py`), `tests/composition_matrix.py`, the two sweep test
  modules, `tests/no_copy_downstream.py`, `tests/conftest.py`, `pyproject.toml`,
  `uv.lock` and `.github/workflows/**`. The list is the `[escalation]` table of
  the budgets file.
- **Who decides.** The `classify` job runs `scripts/classify_changes.py`, which
  diffs the pull request against its base. `push`, `schedule` and
  `workflow_dispatch` **always** require the sweeps. The decision **fails
  closed**: an unreadable budgets file, a git failure, an empty diff, a missing
  base or an unrecognised event all require them, with the reason printed. The
  Linux call skips them only when the output is the literal `false`, so an empty
  or failed classification still runs them, and the `sweeps` input of
  `linux-checks.yml` defaults to true.
- **The canary** always runs the full set; it is non-blocking and off the
  critical path.
- **Forcing a full run.** Dispatch `Test template` on the branch
  (`gh workflow run test-template.yml --ref <branch>`): a dispatch always
  requires the sweeps.

### Evidence of zero silent omissions

Each sweep writes JUnit XML, and `scripts/validation_report.py verify-sweep`
compares the compositions that **executed** with the compositions the catalogue
says are valid, by name, not by count. The job fails on any composition missing,
unexpected, duplicated, skipped or failed, or on any other test in the file not
passing, and prints `expected N compositions, executed N, passed N` with the
runner CPU. A sweep that ran 2,879 of 2,880 fails and names the one it lost.

### The report and the gate

The `budget` job (`Validation budget`) reads this run's jobs and the previous two
successful runs on `main` from the Actions API and writes the matrix-size and
timing report to the job summary: each job's tier, wall time, baseline, warn and
fail limits and verdict, the run's critical path against 16 / 20 minutes, and
for each sweep whether it was required, its result, and executed against
expected compositions with its CPU.

- **Thresholds.** The approved noise rule applies per job and to the critical
  path: `WARN` when 2 of the last 3 runs are above `warn`; `FAIL` when the run
  is above `fail` and the median of the last 3 is above `warn`; `OUTLIER` (not a
  failure) when one run is above `fail` but the median is not, which is the
  signature of slower runner hardware. A `FAIL` fails the job and so
  `All checks passed`.
- **Attribution.** A warning or failure names the job, its tier, how many times
  its baseline p90 the run was, which step dominated, the runner CPU, and the
  last three timings, so a slow-CPU run is recognised at a glance.
- **A skipped sweep is never acceptable when it was required.** A called
  workflow whose inner jobs are skipped still reports `success`, so `budget`
  fails if the classification required the sweeps and a sweep job was skipped or
  missing, or its executed count is not the valid count. `All checks passed`
  needs `classify`, `linux`, `windows`, `audit` and `budget`.

### Infrastructure failures versus test failures

A failed job is classified from the step that failed. **Infrastructure:** the
job was cancelled, ran with no failing step (a lost runner), or failed in a
setup step (`Set up job`, checkout, `Install uv`, `Install dependencies`); the
report says to rerun the failed job (`gh run rerun --failed`). **Test:** any
other step failed; the report says to fix the change, not to rerun. The
aggregate gate is never reported as a cause. This is a step-level rule: a
network error inside a test step cannot be told from a test failure.

### Release gate

`release.yml` has a read-only `Exhaustive tier evidence` job that the release
`needs`. It finds the `push` run of `Test template` for the release commit and
requires it to have succeeded with **both** sweep jobs `success`, not skipped,
cancelled or missing, so a release cannot proceed without the exhaustive tier
and the independent-client evidence on its own commit. It fails closed: no run,
a run still going, a red run or a skipped sweep all refuse the release with the
reason. There is no bypass input, and a dry run needs it too. A newer run for
the commit decides, so a rerun that goes red is not hidden by an older green
one. It trusts the recorded run for that commit, which `main` pushes always
produce with the sweeps.

### Running it yourself

```bash
# Reproduce the timings (needs gh and network):
uv run poe ci:timings -- --since <commit or date>

# Classify a change the way CI does:
uv run poe ci:classify -- --event pull_request --base main --head HEAD

# Prove a sweep's coverage locally:
uv run pytest -m sweep tests/test_composition_sweep.py -n 4 --no-cov \
    --junitxml=direct.xml
uv run poe ci:report -- verify-sweep --kind direct --junit direct.xml

# Check a release commit (needs gh and network):
uv run poe ci:report -- release-evidence --sha <sha>
```

Read a run's report in the job summary of `Validation budget`, and rerun an
infrastructure failure with `gh run rerun <id> --failed`.

## Growth guard

`tests/test_validation_budget.py` projects the catalogue's cost (the valid
count times the per-composition cost above) and fails when it reaches a
sweep's approved failure limit. Today the independent-client sweep projects to
10.3 of 16 minutes, so one more free capability or platform, which would
project to about 20.6 minutes, fails the fast suite. The response is a
deliberate tiering decision and a re-baseline, never raising the limit to make
the test pass.

## Re-baselining

Only in a reviewed pull request that re-runs `uv run poe ci:timings` for the
new window (at least 20 successful runs), updates the budgets file, and cites
the run window and commits. A hardware mix shift is not a reason to
re-baseline; a change in what the jobs do is.

## Boundaries

The budget covers this repository's own CI. It does not govern
`create-forge`'s workflows or any generated project's CI. It does not reduce
release coverage and it makes no performance change to the engine.

Throwaway note that exists only to exercise the docs-only PR path.
