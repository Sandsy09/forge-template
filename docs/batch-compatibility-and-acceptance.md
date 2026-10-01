# Batch compatibility and acceptance

This document defines which versioned engine surfaces the batch archetype
moves, which capability and platform selections are valid, what evidence
accepts each downstream stage, and how the two repositories hand a release
between them. It is the canonical living contract accepted by
[ADR 0081](adr/0081-batch-composition-compatibility-and-acceptance.md) for
[FT-27.02](https://github.com/Sandsy09/forge-template/issues/200), the final
child of [FT-EPIC-27](https://github.com/Sandsy09/forge-template/issues/189).
It completes the Stage 27 pair with the
[archetype contract](batch-archetype.md) (FT-27.01 / ADR 0080).

This was a decision contract: it bumped no version, published no package, and
changed no code, generated content or protocol integer on merge.
[FT-EPIC-28](https://github.com/Sandsy09/forge-template/issues/190) and its
children FT-28.01–03 implement and release the line this contract classifies.
[FT-28.01](https://github.com/Sandsy09/forge-template/issues/201) /
[ADR 0082](adr/0082-batch-archetype-implementation.md) has now landed the
component: `discover_components()` returns `batch`, though the `0.7.0` line
itself is not yet published -- that is FT-28.03's event.
`tests/test_batch_gates.py` pins both facts, updated in step with each stage
rather than deleted, the same discipline `tests/test_streamlit_gates.py`
followed through Stage 20.

## Normative constants

The numbers below are fixed by this contract. Stage 28 implements them; it
does not re-decide them, and the pin test derives its expectations from this
table rather than carrying a second copy.

| Constant | Value |
| --- | --- |
| `PROVIDER_LINE` | `0.7.0` |
| `COMPONENT_VERSION` | `1.0.0` |
| `PYTHON_FLOOR` | `3.11` |
| `PYTHON_ENDPOINTS` | `3.11, 3.14` |
| `JOB_RUN_TIMEOUT_SECONDS` | `5` |
| `PROJECT_CHECK_TIMEOUT_SECONDS` | `600` |
| `COMPOSITION_COUNT_WITH_BATCH` | `3520` |

## Every versioned axis is classified

The [compatibility policy](compatibility-policy.md#the-versioned-axes)
governs the independently versioned surfaces plus the published
extension-point inventory. The batch line moves exactly two of them: the
package version and the set of discovered components. Every other axis is
unchanged, and this is a requirement on Stage 28, not a prediction.

| Axis | Current | Batch line | Change class |
| --- | --- | --- | --- |
| `forge-template` package | `0.6.0` | `0.7.0` | New minor compatibility line |
| ProjectSpec protocol | `1` | `1` | Unchanged |
| Component manifest protocol | `1`, `2`, `3` | `1`, `2`, `3` | Unchanged — `batch` uses protocol `2` and declares no rename or regeneration record |
| Option-schema protocol | `1`, `2` | `1`, `2` | Unchanged — `batch` declares no `options_schema` |
| Foundation source protocol | `1` | `1` | Unchanged |
| Organisation-policy protocol | `1` | `1` | Unchanged (documentation-only by design) |
| Generation metadata `metadata_version` | `1` | `1` | Unchanged |
| Foundation extension points | `16` | `16` | Unchanged — every batch concern uses a published point |
| Discovered components | `15` | `16` | Additive — one new archetype |
| `batch` component | — | `1.0.0` | New |
| The fifteen existing components | current versions | current versions | Unchanged |

## The public engine API does not change

`get_engine_info()`, `discover_components()`, `parse_project_spec()`,
`plan_generation()`, `render_project()`, `plan_update()`, the
generation-metadata functions and `validate_rendered_project()` keep their
signatures, result fields and `EngineErrorCode` values
([template-engine-api.md](template-engine-api.md)). The batch line adds
catalogue content behind that unchanged facade:

- `discover_components()` returns one more descriptor. Its result is a sorted
  tuple, so a strict client that already sorts sees `batch` positioned
  alphabetically, with no new field and no reordering rule.
- `batch` declares no `requires`, `conflicts` or options. The engine already
  validates those edges; this component adds data, not a code path.
- The full composition sweep grows from 2880 to 3520 accepted compositions —
  exactly `cli`'s and `streamlit`'s 640, because `batch` has the same shape:
  no `requires`, no `conflicts`, and `documentation` (which requires
  `library`) unavailable to it.

`run` is a generated-project Poe task, not an engine operation. It adds no
`ForgeEngineError` code and sits outside
[generated-project validation](generated-project-validation.md).

## Why a new minor line

The batch archetype is published as `forge-template` `0.7.0`, not a `0.6.1`
patch and not `1.0.0`. The same three reasons ADR 0069 gave for Streamlit
apply unchanged:

1. **A client opts in at the minor line.** Below `1.0` a supported engine
   range is minor-scoped, `>=0.y.a,<0.(y+1)`
   ([compatibility-policy.md](compatibility-policy.md#compatible-ranges)).
   Published `create-forge` `0.5.0` declares `forge-template>=0.6,<0.7`, so it
   cannot drift into `0.7.0` and adopts deliberately at a future `CF-29.01`
   (already filed as
   [create-forge#204](https://github.com/Sandsy09/create-forge/issues/204)).
2. **The catalogue change is client-observable.** New discovered components
   are observable, and the policy already requires a package bump for that.
3. **`0.6.x` stays a stable fifteen-component line.** A consumer pinned there
   keeps exactly the catalogue it was tested against.

`1.0.0` stays a later decision, exactly as ADR 0061 and ADR 0069 both left
it.

## The component starts at 1.0.0

`batch` enters at component version `1.0.0`, independent of the `0.7.0`
package version and of every protocol integer
([component-manifests.md](component-manifests.md#manifest-and-component-versions)),
matching the first production release of every other archetype. It uses
`manifest_version = 2` with no `[[regeneration]]` or `[[renames]]` record.
`job.py` is owner-edited starter code, the same class of file as `cli.py`,
`app.py` and the Data Science notebook, so it stays on the default `replace`
regeneration disposition — see [ADR 0081](adr/0081-batch-composition-compatibility-and-acceptance.md),
choice 2, for why the archetype's own runtime *output* (`data/output.json`,
governed by [ADR 0080](adr/0080-batch-project-shape.md) choice 7's
atomic-overwrite rule) is a different mechanism at a different layer and
needs no manifest regeneration record at all: it is never a rendered,
manifest-owned target.

This is a different number from the **generated project's** own version,
which is a separate axis from the component version, exactly as with every
other archetype.

## Valid and invalid selections

A ProjectSpec selects exactly one archetype and zero or more capabilities and
platforms. The batch manifest declares no `requires` or `conflicts`, so its
selections need no relationship of their own.

| Selection | Outcome |
| --- | --- |
| `batch` alone | Valid |
| `batch` plus any subset of `changelog`, `coverage`, `dotenv-example`, `jupyter`, `pre-commit`, `pyright`, `scientific-python`, under those components' own rules | Valid |
| `batch` plus the `github` platform and any of `dependabot`, `renovate` under their own `requires`/`conflicts` rules | Valid — 640 compositions in total |
| `batch` + `documentation` | Rejected — `documentation` requires `library`, before rendering |
| `dependabot` without `github`, or with `renovate` | Rejected — the existing `requires` and `conflicts` edges |
| Two archetypes in one spec | Rejected — one archetype per spec |
| A capability ID given as the archetype, or an archetype ID as a capability | Rejected — wrong kind |
| The same component listed twice | Rejected — duplicate selection |
| An unknown component ID | Rejected — not in catalogue |

Every rejection is a structured `ForgeEngineError` raised before any content
renders, matching the
[compatibility policy's](compatibility-policy.md#reporting-an-unsupported-forge-version)
fail-closed rule.

Two behaviours are worth stating because they look odd:

- **Jupyter-only is valid though batch owns no notebook.** `notebook:check`
  discovers notebooks and passes when there are none, so the aggregate
  `check` succeeds. The capability supplies tooling; the archetype supplies
  no notebook.
- **Scientific Python does not collide with batch.** batch declares no
  runtime dependency at all (ADR 0080 choice 3), so there is nothing to
  collide with the capability's bounded scientific stack.

### Deterministic validation requirements

Every valid selection must satisfy all of these, executed by FT-28.01 and
FT-28.02:

- planning and rendering succeed, and repeated renders and manifest-order
  permutations produce byte-identical output;
- the owned target set is exactly the seven batch paths of the
  [archetype contract](batch-archetype.md#reserved-generated-shape) plus the
  selected capabilities' own targets, each with one owner;
- contributions compose in
  [composition order](composition-order.md) — archetype tier first, then
  capabilities lexically;
- the aggregate `check` contains `notebook:check` exactly when `jupyter` is
  selected and never contains `run`; and
- descriptors expose no filesystem or package-resource path.

## Python and dependency evidence

The component's `requires_python` is `>=3.11`. Unlike every other archetype,
batch declares **no runtime dependency**, so there is no third-party
resolution evidence to gather: the standard-library-only job trivially
resolves at every supported endpoint. The executable endpoints stay `3.11`
and `3.14`, the Data Science and Streamlit precedent
([python-support.md](python-support.md)), because the generated project's
own lock, build and `poe check` still need proving at the floor and the
ceiling even with an empty dependency set. The two capability selections
that add a runtime dependency (`jupyter`, `scientific-python`) are already
proven independently by their own capability contracts and do not interact
with batch's own (empty) dependency set.

## Package build and install requirements

The archetype builds a wheel and a source distribution with `uv_build`, the
same fixed mode every other archetype uses. Both artefacts contain **only**
the module tree `src/<package_name>/` (its `__init__.py`, `__main__.py`,
`job.py` and `py.typed`) and the distribution metadata. Neither contains
`data/sample_input.json` nor `tests/`. The acceptance requirements are:

- the wheel and sdist build for every valid selection;
- the wheel installs into an isolated environment, `<package_name>` and
  `<package_name>.job` import, the console script and `python -m
  <package_name>` both run the job successfully against a copy of the
  tracked sample input placed at the expected relative path, `__version__`
  is reported, and `py.typed` ships; and
- the generated project needs neither Forge repository for development,
  build or runtime.

The consequence is deliberate and recorded here so it is not rediscovered as
a defect: **the sample input is a source-tree file, not distribution
content.** The job runs from a checkout; the wheel carries the typed
package and its console-script entry point.

## Committed-lock restoration

Lock finalisation is client-owned
([composition-architecture-review.md](composition-architecture-review.md#client-boundary)),
so provider acceptance simulates it exactly as the Data Science and
Streamlit endpoint sweeps do. For each valid selection and endpoint:

1. `uv lock --python <endpoint>` in the staged project produces the
   committed lock;
2. in a clean copy with no virtual environment, `uv sync --all-groups
   --locked` restores from that lock and fails on drift; and
3. `uv run --locked poe check` passes, which itself begins with
   Foundation's `lock:check`.

## Time-bounded, deterministic smoke

The smoke exists to prove the sample job runs correctly with no scheduler or
network service. It is bounded twice and never retried:

- the generated `tests/test_job.py` completes each job run within
  `JOB_RUN_TIMEOUT_SECONDS` (5 seconds) — tighter than Streamlit's 10-second
  `AppTest` bound because the job does strictly less work (no UI framework
  import or page render, just reading, transforming and writing a handful of
  JSON records);
- the acceptance harness runs the whole `uv run --locked poe check` under a
  `PROJECT_CHECK_TIMEOUT_SECONDS` (600 seconds) subprocess bound, the same
  project-wide bound every other archetype uses; and
- **a timeout is a failure.** It is never retried and the bound is never
  raised to make a run pass; a change to either number requires a
  superseding ADR.

The smoke asserts the job's actual output against a deterministic fixture
(the transformed records) and the idempotency and fail-fast behaviours ADR
0080 fixes, not merely that the process exits.

## The acceptance matrix

Every row names one non-interactive command with a binary outcome and one
owner. A row is "executable" once its command exists and can be run the
moment its stage arrives, not once it passes — Stage 28 is still unbuilt.
`FT` owners run in this repository; `CF` owners run in `create-forge` against
a released or locally overridden engine.

### Engine and catalogue checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| Discovery returns `batch` (archetype, `1.0.0`, no options, protocol `2`, `>=3.11`) | FT-28.01 | `uv run poe check` | FT-28.01 / #201 |
| Descriptor results contain no filesystem or package-resource path | FT-28.01 | `uv run poe check` | FT-28.01 / #201 |
| `batch` reads and contributes through no sibling archetype's resources | FT-28.01 | `uv run poe check` | FT-28.01 / #201 |
| Every generated target has an explicit batch, capability or Foundation owner | FT-28.01 | `uv run poe check` | FT-28.01 / #201 |
| Every valid selection plans and renders deterministically, including repeats and manifest-order permutations | FT-28.01 | `uv run poe check` | FT-28.01 / #201 |
| Invalid selections fail closed as structured engine errors before rendering | FT-28.01 | `uv run poe check` | FT-28.01 / #201 |
| The catalogue sweep plans and renders all 3520 compositions | FT-28.02 | `uv run poe sweep` | FT-28.02 / #202 |
| The built wheel ships every new manifest, contribution and owned resource and still excludes repository tooling | FT-28.02 | `uv run poe check:wheel` | FT-28.01 / #201 |
| Public engine signatures, result fields and `EngineErrorCode` values are unchanged | FT-28.03 | `uv run pytest tests/test_engine.py tests/test_compatibility_policy.py` plus isolated `0.7.0` imports | every Stage 28 child |

### Generated-project checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| A restored project passes the aggregate quality contract from committed lock state, for every valid selection | FT-28.02 | `uv run poe archetype` | FT-28.02 / #202 |
| Wheel and sdist build, install into an isolated environment, import, and report `__version__`, metadata and `py.typed` | FT-28.02 | `uv run poe archetype` | FT-28.02 / #202 |
| Built artefacts contain the module only — no `data/sample_input.json` | FT-28.02 | `uv run poe archetype` | FT-28.02 / #202 |
| The job smoke completes within the per-run bound and `poe check` completes within the project bound; a timeout fails without retry | FT-28.02 | `uv run poe archetype` | FT-28.02 / #202 |
| Rerunning the job twice produces byte-identical `data/output.json`; a malformed record fails fast, logs the error and writes no output | FT-28.02 | `uv run poe archetype` | FT-28.02 / #202 |
| The generated project needs neither Forge repository for development, build or runtime | FT-28.02 | `uv run poe archetype` | FT-28.02 / #202 |

### Python endpoint checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| Each valid selection builds, installs, imports and passes `poe check` at Python 3.11 and 3.14 | FT-28.02 | `uv run poe archetype` (`-n 4`) | FT-28.02 / #202 |

### Client and end-to-end checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| An installed `create-forge` accepts `forge-template` `0.7.0` and fails an out-of-range engine before generation | CF-29.01 | `create-forge` contract tests | CF-29.01 / create-forge#204 |
| Interactive and non-interactive users select batch through the generic archetype/component contract, with no production `batch` branch | CF-29.01 | `create-forge` preview and selection tests | CF-29.01 / create-forge#204 |
| The installed console generates every accepted composition from published artefacts, restores the committed lock and passes checks and the bounded smoke | CF-29.02 | `create-forge` end-to-end suite | create-forge Stage 29 |
| Incompatible providers, invalid selections, lock failures and destination conflicts leave no partial project or staging state | CF-29.02 | `create-forge` end-to-end suite | create-forge Stage 29 |
| Published console installation and generic batch selection are verified | CF-29.03 | `create-forge` release verification | create-forge Stage 29 |

### Regression checks

The direct-Copier path cannot regress *through* Stage 28 content, because no
Stage 28 change touches `template/` or `copier.yml`. The Copier ladder is a
release gate, run once per published line.

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| `library`, `cli`, `data-science` and `streamlit` output is unchanged (byte-level regression pin) | FT-28.02 | `uv run poe check` and `uv run poe archetype` | FT-28.02 / #202 |
| All four Copier combinations render and pass their own `poe check` | FT-28.03 | `uv run poe combos` | FT-28.03 / #203 |
| `copier update` from the last tag preserves local edits and reaches HEAD | FT-28.03 | `uv run poe update` | FT-28.03 / #203 |
| Existing fast, wheel and archetype suites stay green | every Stage 28 child | `uv run poe check`, `poe check:wheel`, `poe archetype` | every Stage 28 child |
| `create-forge`'s existing archetype, default and supported legacy paths are unchanged | CF-29.02 | `create-forge` regression suite | create-forge Stage 29 |

## Cross-repository release hand-offs

The one-way dependency `create-forge → forge-template → generated project`
holds, and the roadmap rule is that the provider merges and releases before
the client adopts the line.

| Gate | Owner | Entry criteria | Exit criteria |
| --- | --- | --- | --- |
| `forge-template` `0.7.0` | FT-28.03 / #203 | Every Engine, Generated-project, Python-endpoint and Regression row above passed on protected `main`; `uv run poe check:wheel` passed on the release candidate; the release dry run was inspected | Tag, GitHub Release and PyPI artefacts name one commit; an isolated published-artefact audit shows discovery returns `batch` and every accepted composition installs and renders; the hand-off records the tag, commit, package bounds and component identity, and claims no client batch support |
| `create-forge` adoption of the `0.7` line | CF-29.01 / create-forge#204 | `0.7.0` is an immutable published target; contract tests pass against it | Engine dependency moves from `>=0.6,<0.7` to `>=0.7,<0.8`; lock refreshed; generic selection works with no production `batch` branch; out-of-range engines fail before generation; plain installs unaffected |
| Installed batch validation | CF-29.02 | CF-29.01 complete | The installed console generates every accepted composition from published artefacts with committed-lock restoration and the bounded smoke; failure paths leave no partial project |
| `create-forge` release | CF-29.03 | `0.7.0` published, CF-29.02 evidence recorded, required checks passed | The published console installs and selects batch through the default path; immutable release and validation evidence is recorded |

The client version number is chosen by `create-forge`, not here. Merging is
not releasing: a merge to `main` leaves it untagged and invisible to a
version-pinned client until `release.yml` runs, exactly as
[CONTRIBUTING.md](../CONTRIBUTING.md#releasing) states, and no version in
this repository changes when this contract merges.

Provider rollback follows the existing rule, not a new one (ADR 0061
decision 5): a published release is never mutated, a `0.7.0` defect is
corrected forward as `0.7.1` and the defective version yanked, and the
`0.6.x` line stays installable through the compatibility policy's
[deprecation window](compatibility-policy.md#deprecation-windows).

## Explicit exclusions

- No runtime implementation, generated-content change, protocol increment,
  package version bump or release in this decision.
- No scheduler, cron integration, workers, queues, cloud services,
  databases, retries, checkpointing or orchestration integration, as fixed
  by the [archetype contract](batch-archetype.md#explicit-exclusions).
- No remote component registry or plugin execution, and no new shared Forge
  runtime dependency for generated projects.

## What Stage 28 may no longer decide

Each downstream issue inherits fixed answers from this contract and the
archetype contract. What genuinely remains open is narrow.

| Issue | Fixed by the Stage 27 contract set | Still owned by the issue |
| --- | --- | --- |
| [FT-28.01 / #201](https://github.com/Sandsy09/forge-template/issues/201) | `batch`, archetype, `1.0.0`, protocol `2`, no options, `requires` or `conflicts`; the seven owned paths; the Foundation contributions | The manifest, resources, and the discovery/ownership/malformed-selection tests |
| [FT-28.02 / #202](https://github.com/Sandsy09/forge-template/issues/202) | 640 valid compositions and the rejections; the Python endpoints; the lock-restoration procedure; the 5 s and 600 s bounds; the artefact expectations | The exhaustive sweep, the executable endpoint harness, the wheel/sdist audit, and the provenance/update evidence |
| [FT-28.03 / #203](https://github.com/Sandsy09/forge-template/issues/203) | The `0.7.0` line; the provider gate and rollback rule; no claim of client support | The version-bump pull request, the protected release, the dry run, and the hand-off receipt for CF-29.01 |

### Known tripwires Stage 28 must expect

These existing checks fail deliberately when Stage 28 moves a line or the
catalogue, and each must be updated in the change that moves it, not worked
around, the same discipline Stage 20 followed for Streamlit:

- `tests/composition_matrix.py`'s `EXPECTED_COMPOSITION_COUNT` (2880 to
  3520);
- `scripts/check_wheel.py`'s explicit list of shipped component paths;
- the component rows of the compatibility-policy current-state table; and
- the catalogue tripwires in `tests/test_batch_contract.py` and
  `tests/test_batch_gates.py`, which must be updated to assert the shipped
  state, not deleted.

## Alignment with existing contracts

| FT-27.02 acceptance criterion | Already owned | New here |
| --- | --- | --- |
| Enumerate accepted/rejected combinations with all current capabilities/platforms; reuse only published extension points | The [archetype contract](batch-archetype.md) fixes the shape; the [capability contracts](data-science-capabilities.md) fix each capability | The valid/invalid table and the 640-composition projection |
| Define generated tasks, Scientific Python optionality, non-network smoke and deterministic fixtures | The archetype contract fixes the `run` task | The time-bounded smoke and its bounds |
| Specify owned paths, provenance/skip-if-exists, update/rename rules and local-edit preservation | The archetype contract fixes the ownership map | The manifest-protocol choice and its reasoning |
| Set packaging, supported Python/Windows/Linux, independent-client and exhaustive validation requirements | [python-support.md](python-support.md) owns the window | The endpoints, the build/install requirements and the acceptance matrix |
| Record any required protocol/version changes explicitly | The [compatibility policy](compatibility-policy.md) defines the axes and ranges | The `0.7.0` line, the axis classification and the finding that no protocol integer changes |

## Deferred decisions

This contract does not decide or implement:

- the `create-forge` UX, its adoption mechanics or its next version number —
  owned by `create-forge` Stage 29;
- the `forge-template` release that carries the line — performed by
  FT-28.03;
- admitting a new CPython release or moving the Python floor — owned by
  [python-support.md](python-support.md);
- any batch capability beyond the archetype itself; or
- promoting the engine to `1.0.0`, or retiring the direct-Copier Library
  path.

The decision changed no package dependency, manifest, catalogue entry,
public API, ProjectSpec, template, Copier answer, generated output, tag or
release.
