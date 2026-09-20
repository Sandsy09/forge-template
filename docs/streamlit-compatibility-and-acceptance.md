# Streamlit compatibility and acceptance

This document defines which versioned engine surfaces the Streamlit archetype
moves, which capability selections are valid, what evidence accepts each
downstream stage, and how the two repositories hand a release between them. It
is the canonical living contract accepted by
[ADR 0069](adr/0069-streamlit-composition-compatibility-and-acceptance.md) for
[FT-19.02](https://github.com/Sandsy09/forge-template/issues/158), the final
child of
[FT-EPIC-19](https://github.com/Sandsy09/forge-template/issues/144). It
completes the Stage 19 pair with the
[archetype contract](streamlit-archetype.md) (FT-19.01 / ADR 0068).

Its review obligations are **FT-ROADMAP-02-AC-01** (an accepted contract defines
the project shape, entry point, dependency and task ownership, supported Python
range and deployment boundary, shared with FT-19.01),
**FT-ROADMAP-02-AC-04** (no-capability, Jupyter, Scientific Python and combined
selections have an accepted compatibility matrix and deterministic render
results, shared with
[FT-20.02](https://github.com/Sandsy09/forge-template/issues/160) and
[FT-20.03](https://github.com/Sandsy09/forge-template/issues/161)) and
**FT-ROADMAP-02-EX-03** (no engine-default cutover, owned solely here).

This is a decision contract. It bumps no version and publishes no package.
FT-19.02 changed no code, generated content or protocol integer; FT-20.01
([ADR 0070](adr/0070-streamlit-archetype-implementation.md)) then added the
`streamlit` component, FT-20.02
([ADR 0071](adr/0071-streamlit-tasks-safeguards-and-composition.md)) completed
it, and FT-20.03 ([ADR 0072](adr/0072-validate-streamlit-generated-projects.md))
proved it (see [streamlit-validation.md](streamlit-validation.md)), so
`discover_components()` returns fifteen components. FT-20.04 carries them in
`forge-template` `0.6.0` ([release record](streamlit-provider-release.md)), the
line that follows the published
[`forge-template` `0.5.0`](cutover-provider-release.md), and the package version
is `0.6.0`.
`tests/test_streamlit_gates.py` reads this contract's tables against the live
engine so the two cannot drift apart.

## Normative constants

The numbers below are fixed by this contract. Later stages implement them; they
do not re-decide them, and the pin test derives its expectations from this table
rather than carrying a second copy.

| Constant | Value |
| --- | --- |
| `PROVIDER_LINE` | `0.6.0` |
| `COMPONENT_VERSION` | `1.0.0` |
| `PYTHON_FLOOR` | `3.11` |
| `PYTHON_ENDPOINTS` | `3.11, 3.14` |
| `SMOKE_RUN_TIMEOUT_SECONDS` | `10` |
| `PROJECT_CHECK_TIMEOUT_SECONDS` | `600` |
| `COMPOSITION_COUNT_WITH_STREAMLIT` | `2880` |

## Every versioned axis is classified

The [compatibility policy](compatibility-policy.md#the-versioned-axes) governs
the independently versioned surfaces plus the published extension-point
inventory. The Streamlit line moves exactly two of them: the package version and
the set of discovered components. Every other axis is unchanged, and this is a
requirement on Stage 20, not a prediction.

| Axis | Current | Streamlit line | Change class |
| --- | --- | --- | --- |
| `forge-template` package | `0.5.0` | `0.6.0` | New minor compatibility line |
| ProjectSpec protocol | `1` | `1` | Unchanged |
| Component manifest protocol | `1`, `2`, `3` | `1`, `2`, `3` | Unchanged — `streamlit` uses protocol `2` and declares no rename or regeneration record |
| Option-schema protocol | `1`, `2` | `1`, `2` | Unchanged — `streamlit` declares no `options_schema` |
| Foundation source protocol | `1` | `1` | Unchanged |
| Organisation-policy protocol | `1` | `1` | Unchanged (documentation-only by design) |
| Generation metadata `metadata_version` | `1` | `1` | Unchanged |
| Foundation extension points | `16` | `16` | Unchanged — every Streamlit concern uses a published point |
| Discovered components | `14` | `15` | Additive — one new archetype |
| `streamlit` component | — | `1.0.0` | New |
| The fourteen existing components | current versions | current versions | Unchanged |

The "Current" column is the 19 September 2026 decision baseline, kept so the
classified transition stays explicit. FT-20.01 has since landed the two
catalogue axes and FT-20.04 the package axis, so the live engine matches the
"Streamlit line" column for the package, discovered components and the
`streamlit` component. The living
[current compatibility state](compatibility-policy.md#current-compatibility-state)
table lists all three.

## The public engine API does not change

`get_engine_info()`, `discover_components()`, `parse_project_spec()`,
`plan_generation()`, `render_project()`, `plan_update()`, the generation-metadata
functions and `validate_rendered_project()` keep their signatures, result fields
and `EngineErrorCode` values ([template-engine-api.md](template-engine-api.md)).
The Streamlit line adds catalogue content behind that unchanged facade:

- `discover_components()` returns one more descriptor. Its result is a sorted
  tuple, so a strict client that already sorts sees `streamlit` last, after
  `scientific-python`, with no new field and no reordering rule.
- `streamlit` declares no `requires`, `conflicts` or options. The engine already
  validates those edges; this component adds data, not a code path.
- The full composition sweep grows from 2240 to 2880 accepted compositions —
  exactly `cli`'s 640, because `streamlit` has the same shape as `cli`: no
  `requires`, no `conflicts`, and `documentation` (which requires `library`)
  unavailable to it.

`run` is a generated-project Poe task, not an engine operation. It adds no
`ForgeEngineError` code and sits outside
[generated-project validation](generated-project-validation.md).

## Why a new minor line

The Streamlit archetype is published as `forge-template` `0.6.0`, not a `0.5.1`
patch and not `1.0.0`. Three reasons, in order of weight:

1. **A client opts in at the minor line.** Below `1.0` a supported engine range
   is minor-scoped, `>=0.y.a,<0.(y+1)`
   ([compatibility-policy.md](compatibility-policy.md#compatible-ranges)).
   Published `create-forge` `0.4.0` declares `forge-template>=0.5,<0.6` (PyPI
   metadata, reviewed 19 September 2026), so it cannot drift into `0.6.0` and
   adopts deliberately at
   [CF-21.01](https://github.com/Sandsy09/create-forge/issues/165) — the same
   opt-in step the `0.3.2` to `0.4.0` Data Science line used. A patch would
   put a new archetype inside the range a released client already accepts, with
   no adoption step and no client-side validation.
2. **The catalogue change is client-observable.** New discovered components are
   observable, and the policy already requires a package bump for that.
3. **`0.5.x` stays a stable fourteen-component line.** A consumer pinned there
   keeps exactly the catalogue it was tested against.

`1.0.0` stays a later decision, exactly as
[ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md) left
it: promoting the engine to major-scoped ranges is not something a new archetype
should trigger.

## The component starts at 1.0.0

`streamlit` enters at component version `1.0.0`, independent of the `0.6.0`
package version and of every protocol integer
([component-manifests.md](component-manifests.md#manifest-and-component-versions)),
matching the first production release of `data-science`, `jupyter` and
`scientific-python`. It uses `manifest_version = 2` with no `[[regeneration]]` or
`[[renames]]` record. That follows `library`, `cli` and `data-science`, whose
user-edited starter code stays on the default `replace` regeneration disposition
and is protected by the client at merge time; the only `skip-if-exists`
reference set is `CHANGELOG.md` and `.env`, mirroring `copier.yml`'s
`_skip_if_exists` ([generation-provenance.md](generation-provenance.md)).

This is a different number from the **generated project's** initial version,
which [the archetype contract](streamlit-archetype.md#archetype-identity-and-fixed-choices)
fixes at `0.1.0`. The component version describes the reviewed catalogue entry;
the project version describes the scaffolded repository. They never move
together. Later component movement follows the standard rules — patch for
corrected content, minor for additive content or a new option, major for a
breaking change to owned content or a contribution.

## Valid and invalid selections

A ProjectSpec selects exactly one archetype and zero or more capabilities and
platforms. The Streamlit manifest declares no `requires` or `conflicts`, so its
four capability selections need no relationship of their own.

| Selection | Outcome |
| --- | --- |
| `streamlit` alone | Valid |
| `streamlit` + `jupyter` | Valid |
| `streamlit` + `scientific-python` | Valid |
| `streamlit` + `jupyter` + `scientific-python` | Valid |
| Any of the above plus the `github` platform and any of `changelog`, `coverage`, `dependabot`, `dotenv-example`, `pre-commit`, `pyright`, `renovate`, under those components' own rules | Valid — 640 compositions in total |
| `streamlit` + `documentation` | Rejected — `documentation` requires `library`, before rendering |
| `dependabot` without `github`, or with `renovate` | Rejected — the existing `requires` and `conflicts` edges |
| Two archetypes in one spec | Rejected — one archetype per spec |
| A capability ID given as the archetype, or an archetype ID as a capability | Rejected — wrong kind |
| The same component listed twice | Rejected — duplicate selection |
| An unknown component ID | Rejected — not in catalogue |

Every rejection is a structured `ForgeEngineError` raised before any content
renders, matching the
[compatibility policy's](compatibility-policy.md#reporting-an-unsupported-forge-version)
fail-closed rule.

Two behaviours of the four selections are worth stating because they look odd:

- **Jupyter-only is valid though Streamlit owns no notebook.** `notebook:check`
  discovers notebooks and passes when there are none, so the aggregate `check`
  succeeds. The capability supplies tooling; the archetype supplies no notebook.
- **Scientific Python does not collide with Streamlit.** Streamlit `1.63.0`
  requires `numpy<3` and `pandas<4`, both of which contain the capability's
  `numpy>=2.4,<2.5` and `pandas>=3.0,<4` lines.

### Deterministic validation requirements

Every valid selection must satisfy all of these, executed by FT-20.02 and
FT-20.03:

- planning and rendering succeed, and repeated renders and manifest-order
  permutations produce byte-identical output;
- the owned target set is exactly the seven Streamlit paths of the
  [archetype contract](streamlit-archetype.md#reserved-generated-shape) plus the
  selected capabilities' own targets, each with one owner;
- contributions compose in
  [composition order](composition-order.md) — archetype tier first, then
  capabilities lexically — so `run` precedes `notebook` in the task table,
  `streamlit` precedes the scientific lines in the runtime dependencies, and the
  `/.streamlit/secrets.toml` ignore entry precedes `.ipynb_checkpoints/`;
- the aggregate `check` contains `notebook:check` exactly when `jupyter` is
  selected and never contains `run`; and
- descriptors expose no filesystem or package-resource path.

## Python and dependency evidence

The component's `requires_python` is `>=3.11`, satisfied across the whole
selected range by definition
([compatibility-policy.md](compatibility-policy.md#compatible-ranges)). The
executable endpoints are Python 3.11 and 3.14, the same two the Data Science line
uses ([python-support.md](python-support.md)). Resolution is the separate
property, and it was checked on 19 September 2026 against official PyPI metadata
with `uv` 0.12.5:

| Check | Selections | Result |
| --- | --- | --- |
| Universal resolve, floor 3.11 (what `uv lock` performs) | all four | resolves; `streamlit 1.64.0`, `pandas 3.0.6`, `pyarrow 25.0.1`, `numpy 2.4.6` (Python 3.11) and `2.5.3` (3.12 and later) without the capability |
| Wheels only (`--only-binary :all:`) at 3.11, 3.12, 3.13 and 3.14 | `streamlit` alone; all three components combined | resolves at every interpreter |
| Floor resolution (`--resolution lowest-direct`) at 3.11 and 3.14 | all three components combined | resolves `streamlit 1.63.0` |
| Generated project's own `poe check` (FT-20.01, 19 September 2026), Python 3.11, 3.13 and 3.14 | `streamlit` alone | passes with the development-only `numpy<2.5` cap in the `dev` group; **fails at `mypy` without it** (see below) |

**Correction found by FT-20.01.** Resolution alone was not sufficient evidence.
Running the generated project's own `poe check` showed that Streamlit's
`numpy<3` lets the lock select NumPy 2.5 on Python 3.12 and later, whose type
stubs use Python 3.12 syntax that Foundation's `mypy` — which targets the 3.11
floor — cannot parse, so a default project (floor 3.11, development 3.13) failed
its type check. Streamlit-alone resolution never exercised that. The archetype
contributes a development-only `numpy<2.5` (see the
[archetype contract](streamlit-archetype.md#packaging-and-dependency-contract)
and [ADR 0070](adr/0070-streamlit-archetype-implementation.md)); it never
enters the wheel metadata, and the two capability selections that include
`scientific-python` already carry the same ceiling. FT-20.03's executable
endpoint check exists to catch exactly this class of failure.

The declared line `streamlit>=1.63,<2` therefore stands unchanged from the
archetype contract. Streamlit `1.63.0` lists Python 3.10 to 3.14 in its
classifiers and requires `>=3.10`, so the Forge floor is not the binding
constraint. The bounds are normative compatibility lines under the
[capability maintenance rules](data-science-capabilities.md#maintenance-and-compatibility):
lock movement within them is routine, a bound change needs an upstream review
and a resolution across the accepted range, and crossing an upper bound needs a
superseding ADR. Admitting CPython 3.15 belongs to
[python-support.md](python-support.md#admitting-a-new-cpython-release); it needs
both Forge's own evidence and Streamlit's, and is never a silent bound change.

## Package build and install requirements

The archetype builds a wheel and a source distribution with `uv_build`. Building
the archetype's layout with `uv` 0.12.5 showed that both artefacts contain
**only** the module tree `src/<package_name>/` (its `__init__.py`, `app.py` and
`py.typed`) and the distribution metadata. Neither contains the root `app.py`
launcher, `.streamlit/config.toml` or `tests/`, and a planted
`.streamlit/secrets.toml` reached neither artefact. The acceptance requirements
are:

- the wheel and sdist build for every valid selection;
- the wheel installs into an isolated environment and `<package_name>` and
  `<package_name>.app` import, `__version__` is reported, and `py.typed` ships;
- neither artefact contains `.streamlit/secrets.toml` or any ignored working
  material; and
- the generated project needs neither Forge repository for development, build or
  runtime.

The consequence is deliberate and recorded here so it is not rediscovered as a
defect: **the launcher and `.streamlit/config.toml` are source-tree files, not
distribution content.** The application runs from a checkout with
`streamlit run app.py`; the wheel carries the typed package. That is consistent
with the [deployment boundary](streamlit-archetype.md#explicit-exclusions), which
provides no hosting or delivery.

## Committed-lock restoration

Lock finalisation is client-owned
([composition-architecture-review.md](composition-architecture-review.md#client-boundary)),
so provider acceptance simulates it exactly as the Data Science endpoint sweep
does. For each valid selection and endpoint:

1. `uv lock --python <endpoint>` in the staged project produces the committed
   lock;
2. in a clean copy with no virtual environment, `uv sync --all-groups --locked`
   restores from that lock and fails on drift; and
3. `uv run --locked poe check` passes, which itself begins with Foundation's
   `lock:check`.

## Time-bounded, non-serving smoke

The smoke exists to prove the starter page renders without starting a server. It
is bounded twice and never retried:

- every `AppTest` run in the generated `tests/test_app.py` completes within
  `SMOKE_RUN_TIMEOUT_SECONDS` (10 seconds) — the test constructs its `AppTest`
  with that `default_timeout`;
- the acceptance harness runs the whole `uv run --locked poe check` under a
  `PROJECT_CHECK_TIMEOUT_SECONDS` (600 seconds) subprocess bound; and
- **a timeout is a failure.** It is never retried and the bound is never raised
  to make a run pass; a change to either number requires a superseding ADR.

The smoke is non-serving. No acceptance command invokes `streamlit run`, no
process is left listening after a run, and the aggregate `check` never contains
the `run` task. The bounds are set from a measurement, not a guess: a prototype
of the exact layout ran two `AppTest` cases, including importing Streamlit, in
about 3 seconds of wall time, against a Streamlit default of 3 seconds per run
that is tight on a cold CI runner. FT-20.01's shipped starter measured the three
`AppTest` cases at about 4 to 5 seconds in total and the whole generated
`poe check` at about 55 seconds at Python 3.11, 3.13 and 3.14 on a local Windows
machine, well inside both bounds.

## The acceptance matrix

Every row names one non-interactive command with a binary outcome and one owner.
A row is "executable" once its command exists and can be run the moment its stage
arrives, not once it passes — the Stage 20 work is still unbuilt. `FT` owners run
in this repository; `CF` owners run in `create-forge` against a released or
locally overridden engine.

### Engine and catalogue checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| Discovery returns `streamlit` (archetype, `1.0.0`, no options, protocol `2`, `>=3.11`), lexically last of fifteen | FT-20.01 | `uv run poe check` | FT-20.01 / #159 |
| Descriptor results contain no filesystem or package-resource path | FT-20.01 | `uv run poe check` | FT-20.01 / #159 |
| `streamlit` reads and contributes through no sibling archetype's resources | FT-20.01 | `uv run poe check` | FT-20.01 / #159 |
| Every generated target has an explicit Streamlit, capability or Foundation owner | FT-20.01 | `uv run poe check` | FT-20.01 / #159 |
| The four accepted selections plan and render deterministically, including repeats and manifest-order permutations | FT-20.02 | `uv run poe check` | FT-20.02 / #160 |
| Contributions compose in archetype-then-capability order | FT-20.02 | `uv run poe check` | FT-20.02 / #160 |
| Invalid selections fail closed as structured engine errors before rendering | FT-20.02 | `uv run poe check` | FT-20.02 / #160 |
| The catalogue sweep plans and renders all 2880 compositions | FT-20.03 | `uv run poe sweep` | FT-20.03 / #161 |
| The built wheel ships every new manifest, contribution and owned resource and still excludes repository tooling | FT-20.03 | `uv run poe check:wheel` | FT-20.01 / #159 |
| Public engine signatures, result fields and `EngineErrorCode` values are unchanged | FT-20.04 | `uv run pytest tests/test_engine.py tests/test_compatibility_policy.py` plus isolated `0.6.0` imports | every Stage 20 child |

### Generated-project checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| A restored project passes the aggregate quality contract from committed lock state, for all four selections | FT-20.03 | `uv run poe archetype` | FT-20.03 / #161 |
| Wheel and sdist build, install into an isolated environment, import, and report `__version__`, metadata and `py.typed` | FT-20.03 | `uv run poe archetype` | FT-20.03 / #161 |
| Built artefacts contain the module only — no root `app.py`, `.streamlit/config.toml` or `.streamlit/secrets.toml` | FT-20.03 | `uv run poe archetype` | FT-20.03 / #161 |
| The `AppTest` smoke renders within the per-run bound and `poe check` completes within the project bound; a timeout fails without retry | FT-20.03 | `uv run poe archetype` | FT-20.03 / #161 |
| No acceptance command starts `streamlit run` or leaves a listening process, and `check` never contains `run` | FT-20.03 | `uv run poe archetype` | FT-20.03 / #161 |
| No generated file carries a secret; `/.streamlit/secrets.toml` is ignored and shadows no tracked file | FT-20.02 | `uv run poe check` | FT-20.02 / #160 |
| The generated project needs neither Forge repository for development, build or runtime | FT-20.03 | `uv run poe archetype` | FT-20.03 / #161 |

### Python endpoint checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| `streamlit>=1.63,<2`, alone and with the Jupyter and Scientific Python lines, resolves at Python 3.11 and 3.14 | FT-20.02 | `uv run poe archetype` | FT-20.02 / #160 |
| Each of the four selections builds, installs, imports and passes `poe check` at Python 3.11 and 3.14 | FT-20.03 | `uv run poe archetype` (`-n 4`) | FT-20.03 / #161 |

### Client and end-to-end checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| An installed `create-forge` accepts `forge-template` `0.6.0` and fails an out-of-range engine before generation | CF-21.01 | `create-forge` contract tests | CF-21.01 / create-forge#165 |
| Interactive and non-interactive users select Streamlit through the generic archetype/component contract, with no production `streamlit` branch | CF-21.01 | `create-forge` preview and selection tests | CF-21.01 / create-forge#165 |
| The installed console generates all four compositions from published artefacts, restores the committed lock and passes checks and the bounded smoke | CF-21.02 | `create-forge` end-to-end suite | CF-21.02 / create-forge#166 |
| Incompatible providers, invalid selections, lock failures and destination conflicts leave no partial project or staging state | CF-21.02 | `create-forge` end-to-end suite | CF-21.02 / create-forge#166 |
| Published console installation, generic Streamlit selection and documentation deployment are verified | CF-21.03 | `create-forge` release verification | CF-21.03 / create-forge#167 |

### Regression checks

The direct-Copier path cannot regress *through* Stage 20 content, because no
Stage 20 change touches `template/` or `copier.yml`. The Copier ladder is a
release gate, run once per published line.

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| `library`, `cli` and `data-science` output is unchanged (byte-level regression pin) | FT-20.03 | `uv run poe check` and `uv run poe archetype` | FT-20.03 / #161 |
| All four Copier combinations render and pass their own `poe check` | FT-20.04 | `uv run poe combos` | FT-20.04 / #162 |
| `copier update` from the last tag preserves local edits and reaches HEAD | FT-20.04 | `uv run poe update` | FT-20.04 / #162 |
| Existing fast, wheel and archetype suites stay green | every Stage 20 child | `uv run poe check`, `poe check:wheel`, `poe archetype` | every Stage 20 child |
| `create-forge`'s existing archetype, default and supported legacy paths are unchanged | CF-21.02 | `create-forge` regression suite | CF-21.02 / create-forge#166 |

## Cross-repository release hand-offs

The one-way dependency `create-forge → forge-template → generated project`
holds, and the roadmap rule is that the provider merges and releases before the
client adopts the line. `create-forge`'s
[release-coordination order](https://github.com/Sandsy09/create-forge/blob/main/docs/integration-contract.md#release-coordination)
is authoritative for client-side mechanics; this contract states the gates, not
a competing procedure.

| Gate | Owner | Entry criteria | Exit criteria |
| --- | --- | --- | --- |
| `forge-template` `0.6.0` | FT-20.04 / #162 | Every Engine, Generated-project, Python-endpoint and Regression row above passed on protected `main`; `uv run poe check:wheel` passed on the release candidate; the release dry run was inspected | Tag, GitHub Release and PyPI artefacts name one commit; an isolated published-artefact audit shows discovery returns `streamlit` and every accepted composition installs and renders; the hand-off records the tag, commit, package bounds and component identity, and claims neither client Streamlit support nor an engine-default cutover |
| `create-forge` adoption of the `0.6` line | CF-21.01 / create-forge#165 | `0.6.0` is an immutable published target; contract tests pass against it | Engine dependency moves from `>=0.5,<0.6` to `>=0.6,<0.7`; lock refreshed; generic selection works with no production `streamlit` branch; out-of-range engines fail before generation; plain installs unaffected |
| Installed Streamlit validation | CF-21.02 / create-forge#166 | CF-21.01 complete | The installed console generates all four compositions from published artefacts with committed-lock restoration and the bounded smoke; failure paths leave no partial project |
| `create-forge` release | CF-21.03 / create-forge#167 | `0.6.0` published, CF-21.02 evidence recorded, required checks passed | The published console installs and selects Streamlit through the default path; documentation is deployed; immutable release and validation evidence is recorded |

The client version number is chosen by `create-forge`, not here. Merging is not
releasing: a merge to `main` leaves it untagged and invisible to a
version-pinned client until `release.yml` runs, exactly as
[CONTRIBUTING.md](../CONTRIBUTING.md#releasing) states, and no version in this
repository changes when this contract merges.

Provider rollback follows the existing rule, not a new one
([ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md)
decision 5): a published release is never mutated, a `0.6.0` defect is corrected
forward as `0.6.1` and the defective version yanked, and the `0.5.x` line stays
installable through the compatibility policy's
[deprecation window](compatibility-policy.md#deprecation-windows) so a client can
pin back. FT-20.04 may not yank `0.5.0` when it publishes `0.6.0`.

### The cutover is shipped, and is not a gate

Full cutover completion is not required merely because this is roadmap v4, and
it is not required here. As of 19 September 2026 it has in fact shipped on both
sides: `forge-template` `0.5.0` and `create-forge` `0.4.0` are both published, and
`create-forge` `0.4.0` makes the engine its default `new` path and removes
`--engine-preview`.

The roadmap therefore also asks for the case where cutover has *not* shipped: a
client adopting Streamlit would then use the supported `--engine-preview` path,
would not expand the Copier registry to expose Streamlit, and would leave plain
installs unaffected. That path is **recorded and not applicable** to the released
client — adoption uses the default path — and it stays defined for any
pre-cutover client. The open
[FT-EPIC-18](https://github.com/Sandsy09/forge-template/issues/143) is
bookkeeping, not a Streamlit gate.

## Explicit exclusions

- **FT-ROADMAP-02-EX-03 — no engine-default cutover.** Streamlit delivery
  makes no default-path switch. The direct-Copier `template/` and `copier.yml`
  path is unchanged, un-deprecated and Library-only, and Streamlit is reachable
  only through the engine.
- No runtime implementation, generated-content change, protocol increment,
  package version bump or release in this decision.
- No cloud deployment, container orchestration, authentication, database or
  FastAPI surface, and no arbitrary Streamlit plugin ecosystem, as fixed by the
  [archetype contract](streamlit-archetype.md#explicit-exclusions).
- No remote component registry or plugin execution, and no new shared Forge
  runtime dependency for generated projects.

## What Stage 20 may no longer decide

Each downstream issue inherits fixed answers from this contract and the
archetype contract. What genuinely remains open is narrow.

| Issue | Fixed by the Stage 19 contract set | Still owned by the issue |
| --- | --- | --- |
| [FT-20.01 / #159](https://github.com/Sandsy09/forge-template/issues/159) | `streamlit`, archetype, `1.0.0`, protocol `2`, no options, `requires` or `conflicts`; the seven owned paths; the eight Foundation contributions | **Done** ([ADR 0070](adr/0070-streamlit-archetype-implementation.md)): the manifest, six of the seven owned paths, six contributions (the five packaging ones and the development-only NumPy cap), the path-free descriptor, and discovery, ownership and malformed-selection tests. `.streamlit/config.toml` and the other three contributions moved to FT-20.02 |
| [FT-20.02 / #160](https://github.com/Sandsy09/forge-template/issues/160) | `streamlit>=1.63,<2`; the `run` task outside `check`; the configuration and secret safeguards; the four valid selections and the rejections; the deterministic-validation requirements; the exclusions | **Done** ([ADR 0071](adr/0071-streamlit-tasks-safeguards-and-composition.md)): the `run` task outside `check`, `.streamlit/config.toml`, the secrets ignore rule and the README section (the archetype's last three contributions and last path), deterministic composition tests for the four selections, ordering and the rejections, and the resolution-only endpoint check of the Python row |
| [FT-20.03 / #161](https://github.com/Sandsy09/forge-template/issues/161) | Endpoints 3.11 and 3.14; lock restoration; the 10 s and 600 s bounds; the artefact expectations; the 2880-composition sweep; the regression protections | **Done** ([ADR 0072](adr/0072-validate-streamlit-generated-projects.md)): the executable endpoint harness with clean-copy lock restoration, the bounds and the listen guard, the module-only artefact audit, Forge-free installs, the full-composition cell, the regression digests for all four archetypes, and the source-tree-derived wheel and sdist audit. The 2880-composition sweep needed no update: the catalogue count moved at FT-20.01 |
| [FT-20.04 / #162](https://github.com/Sandsy09/forge-template/issues/162) | The `0.6.0` line; the provider gate and rollback rule; no claim of client support or cutover | **Done** (no new decision executed; [streamlit-provider-release.md](streamlit-provider-release.md) records the version-bump pull request, the protected release and dry run, the tag, Release and PyPI artefact audit, the direct-Copier regression, and the client-bound hand-off) |

### Known tripwires Stage 20 must expect

These existing checks fail deliberately when Stage 20 moves a line or the
catalogue, and each must be updated in the change that moves it, not worked
around. FT-20.01 moved the catalogue ones and FT-20.04 the package-line
ones:

- **Moved by FT-20.01:** `tests/composition_matrix.py`'s
  `EXPECTED_COMPOSITION_COUNT` (2240 to 2880); the `streamlit` row of
  `tests/test_cutover_gates.py`'s component classification;
  `scripts/check_wheel.py`'s explicit list of shipped component paths; the
  component rows of the compatibility-policy current-state table; the
  architecture-review size pin; and the catalogue tripwires in
  `tests/test_streamlit_contract.py` and `tests/test_streamlit_gates.py`, which
  now assert the shipped state.
- **Widened by FT-20.03:** the regression-digest fixture now covers
  `data-science` and `streamlit` as well as `library` and `cli`, the
  full-composition build gained its `streamlit` cell, and `scripts/check_wheel.py`
  derives its resource audit from the source tree.
- **Moved by FT-20.04:** `tests/test_cutover_gates.py`'s package-version
  assertion (now `0.6.`), the package row of the compatibility-policy table and
  the cutover contract's "Current" package cell (both now `0.6.0`), and
  `tests/test_streamlit_gates.py`'s package-line tripwire, which now asserts the
  live package equals `PROVIDER_LINE` and fails again at the next bump.

No cutover implementation dependency is added. Everything Streamlit needs —
manifest protocol `2`, the published extension points and the metadata
contract — shipped in `0.5.0`, so no `blocked_by` edge changes and the
hash-pinned `docs/roadmap-v4/**` mirror is untouched.

## Alignment with existing contracts

| FT-19.02 acceptance criterion | Already owned | New here |
| --- | --- | --- |
| Approve the four capability selections with compatibility and deterministic validation requirements | The [archetype contract](streamlit-archetype.md) fixes the shape; the [capability contracts](data-science-capabilities.md) fix each capability | The valid/invalid table, the resolution evidence and the deterministic-validation requirements |
| Select Python and dependency bounds, build and install requirements, lock restoration and a time-bounded non-serving smoke | [python-support.md](python-support.md) owns the window; the Data Science endpoint sweep is the lock-restoration pattern | The endpoints, the artefact expectations, the 10 s and 600 s bounds and the no-server rule |
| Choose the provider line and public-interface impacts; add only required cutover dependencies | The [compatibility policy](compatibility-policy.md) defines the axes and ranges | The `0.6.0` line, the axis classification, the unchanged facade, and the finding that no cutover dependency is required |
| Define provider-first release gates and the preview path without requiring full cutover | `create-forge`'s integration contract defines client-side mechanics | The four named gates, the shipped-cutover finding and the recorded not-applicable preview path |

## Deferred decisions

This contract does not decide or implement:

- the `create-forge` UX, its adoption mechanics or its next version number —
  owned by `create-forge` Stage 21;
- the `forge-template` release that carries the line — performed by FT-20.04
  and recorded in [streamlit-provider-release.md](streamlit-provider-release.md);
- admitting a new CPython release or moving the Python floor — owned by
  [python-support.md](python-support.md);
- `pages/` multipage scaffolding or any Streamlit capability beyond the archetype;
- promoting the engine to `1.0.0`, or retiring the direct-Copier Library path; or
- crossing the `streamlit` upper bound, which needs a superseding ADR.

The decision changed no package dependency, manifest, catalogue entry, public
API, ProjectSpec, template, Copier answer, generated output, tag or release.
