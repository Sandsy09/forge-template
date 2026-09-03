# Data Science compatibility and acceptance

This document defines which versioned engine surfaces the Data Science rollout
moves, what evidence accepts each downstream stage, and how the two
repositories hand a release between them. It is the canonical living contract
accepted by
[ADR 0048](adr/0048-data-science-compatibility-and-acceptance.md) for FT-10.04,
the final child of
[FT-EPIC-10](https://github.com/Sandsy09/forge-template/issues/96).

This contract itself bumped no version or published package. Stages 11 and 12
subsequently implemented the two capabilities and Data Science archetype, and
FT-12.04 published them in
[`forge-template 0.4.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0)
on [PyPI](https://pypi.org/project/forge-template/0.4.0/). Stage 14 reviews the
result and publishes the reviewed line. Nothing here changes the direct-Copier
Library path.

It completes the Stage 10 set:
[the archetype shape](data-science-archetype.md) (FT-10.01),
[the capability contracts](data-science-capabilities.md) (FT-10.02), and
[the notebook, data, and model safeguards](notebook-data-and-model-safeguards.md)
(FT-10.03) each deferred compatibility, acceptance, and release classification
to this decision.

## Every versioned axis is classified before implementation

The [compatibility policy](compatibility-policy.md#the-versioned-axes) governs
eight independently versioned surfaces plus the published extension-point
inventory. Data Science moves exactly two of them: the package version and the
set of discovered components. Every other axis is unchanged, and this is a
requirement on the implementing stages, not a prediction.

| Axis | Pre-rollout baseline | Data Science line | Change class |
| --- | --- | --- | --- |
| `forge-template` package | `0.3.2` | `0.4.0`, reviewed `0.4.1` | New minor compatibility line |
| ProjectSpec protocol | `1` | `1` | Unchanged |
| Component manifest protocol | `1`, `2` | `1`, `2` | Unchanged — new components use protocol `2` |
| Option-schema protocol | `1`, `2` | `1`, `2` | Unchanged — all three new components declare no `options_schema` |
| Foundation source protocol | `1` | `1` | Unchanged — new extension points are content, not a source-shape change |
| Organisation-policy protocol | `1` | `1` | Unchanged (documentation-only by design) |
| Extension-point inventory | 8 points across 3 Foundation files | 11 points across 3 Foundation files (FT-11.01) | Additive only; no rename, no removal |
| `library` component | `1.0.1` | `1.0.1` | Unchanged |
| `cli` component | `1.0.1` | `1.0.1` | Unchanged |
| `data-science` component | — | `1.0.0` | New |
| `jupyter` component | — | `1.0.0` | New |
| `scientific-python` component | — | `1.0.0` | New |

The living
[current compatibility state](compatibility-policy.md#current-compatibility-state)
table advanced to `0.4.0` only when FT-12.04 published the release. The table
above preserves the `0.3.2` decision baseline so the classified transition
remains explicit.

## The public engine API does not change

`get_engine_info()`, `discover_components()`, `parse_project_spec()`,
`plan_generation()`, `render_project()`, `validate_rendered_project()`, and
`map_legacy_library_answers()` keep their current signatures, result fields,
and `EngineErrorCode` values from package version `0.3.2` through `0.4.0`
([template-engine-api.md](template-engine-api.md)). The Data Science line adds
catalogue content behind that unchanged facade:

- `discover_components()` returns three more descriptors. Its result is a
  sorted tuple, so a strict client that already sorts sees
  `("cli", "data-science", "jupyter", "library", "scientific-python")` with no
  new field and no reordering rule.
- `data-science` declares `requires = [{ id = "jupyter", version = ">=1,<2" }]`
  ([data-science-capabilities.md](data-science-capabilities.md#data-science-requires-jupyter)).
  The engine already validates `requires`; the edge adds data, not a code
  path.
- The three manifests carry no `options_schema`, so the option-prompting
  surface create-forge Stage 13 builds is exercised only by fixtures, exactly
  as [FT-11.04 / #108](https://github.com/Sandsy09/forge-template/issues/108)
  did — its `optioned-tooling` fixture proves capability option validation
  and rendering
  ([capability-composition-validation.md](capability-composition-validation.md)).

`notebook:check` is a generated-project Poe task, not an engine operation. It
adds no `ForgeEngineError` code and sits outside
[generated-project validation](generated-project-validation.md#checks-that-remain-outside-this-boundary),
which already lists notebook cleanliness and execution as out of boundary.

## Why additive content still opens the 0.4.0 line

Adding components and extension points breaks nothing, yet it is still a new
minor line rather than a `0.3.3` patch. Three reasons, in order of weight:

1. **A client opts in at the minor line.** Below `1.0` a supported engine
   range is minor-scoped — `>=0.y.a,<0.(y+1)`
   ([compatibility-policy.md](compatibility-policy.md#compatible-ranges)).
   Released `create-forge` declares `forge-template>=0.3.1,<0.4`, so it cannot
   see a Data Science shipped inside `0.3.x` and cannot be made to. Publishing
   at `0.4.0` gives the client a deliberate adoption step
   ([CF-13.01](https://github.com/Sandsy09/create-forge/issues/106) moves the
   extra to `>=0.4,<0.5`) instead of a new archetype appearing mid-range.
2. **The catalogue change is client-observable.** The compatibility policy
   already requires a package bump for a Foundation change a client can
   observe, "including publishing, removing, or renaming an extension point".
   New discovered components are at least as observable. A patch is the floor
   the policy sets; the roadmap fixes the actual step at a minor for reason 1.
3. **`0.3.x` stays a stable two-archetype line.** A consumer pinned there
   keeps exactly the catalogue it was tested against.

This is consistent with
[extension-points.md](extension-points.md#stability-and-versioning): adding a
point "requires no version transition beyond the normal patch/minor release
that ships it". The points alone would not force a minor; the requirable
components ride the same release and the roadmap sets it at `0.4.0`.

## New components start at 1.0.0

`data-science`, `jupyter`, and `scientific-python` each enter at component
version `1.0.0`. Component versions are independent PEP 440 and unrelated to
the `0.4.0` package version or any protocol integer
([component-manifests.md](component-manifests.md#manifest-and-component-versions)):
`library` and `cli` sat at `1.0.1` inside the `0.3.2` baseline and remain there
in `0.4.0`. A first
production release of reviewed, owned content is a `1.0.0`, matching that
precedent. Later movement follows the standard component version rules — patch
for corrected content, minor for additive content or a new option, major for a
breaking change to owned content or an extension contribution.

This is a different number from the **generated project's** initial version.
The [archetype contract](data-science-archetype.md#archetype-identity-and-fixed-choices)
fixes a generated Data Science project's `[project].version` at `0.1.0`, the
same starting point Library offers through its `initial_version` option. The
component version describes the reviewed catalogue entry; the project version
describes the scaffolded repository. The two never move together.

## The acceptance matrix

Every row names one non-interactive command with a binary outcome and one
owner. A row is "executable" when the command exists and can be run the moment
its stage arrives — not when it passes today, since the components are
unbuilt. `FT` owners run in this repository; `CF` owners run in `create-forge`
against a released or locally overridden engine.

### Engine and catalogue checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| Manifest validation accepts contributions to each new Foundation extension point | FT-11.01 | `uv run pytest tests/test_capability_extension_points.py` — **done** ([ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md)) | FT-11.01 / #105 |
| Empty new points render `library` and `cli` byte-for-byte unchanged | FT-11.01 | `uv run pytest tests/test_capability_extension_points.py` — **done** | FT-11.01 / #105 |
| Multiple deterministic capability contributions compose without last-write-wins | FT-11.01 | `uv run pytest tests/test_capability_extension_points.py` — **done** | FT-11.01 / #105 |
| Discovery returns `data-science`, `jupyter`, `scientific-python` with the accepted metadata, in lexical order | FT-12.01 | `uv run pytest tests/test_data_science_archetype.py` — **done** ([ADR 0053](adr/0053-production-data-science-archetype.md)) | FT-11.02 / #106 and FT-11.03 / #107 for the capabilities; FT-12.01 / #109 for the archetype |
| Descriptor results contain no filesystem or package-resource path | FT-11.04 | `uv run pytest tests/test_capability_composition.py` — **done** ([ADR 0052](adr/0052-validate-production-capability-composition.md)) | FT-11.02 / #106 and FT-11.03 / #107 |
| Invalid selections fail closed through stable structured engine errors before rendering | FT-11.04 | `uv run pytest tests/test_capability_composition.py` — **done** | FT-11.04 / #108 |
| The built wheel ships every new manifest, contribution, and owned resource and still excludes repo tooling | FT-12.04 | `uv run poe check:wheel` plus the [published-wheel audit](data-science-validation.md#published-040-release-verification) — **done** | FT-11.02 / #106 and FT-11.03 / #107 |
| Public engine signatures, result fields, and `EngineErrorCode` values are unchanged | FT-12.04 | `uv run pytest tests/test_engine.py tests/test_compatibility_policy.py` plus isolated `0.4.0` imports — **done** | every Stage 11–12 child |

### Generated-project checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| A restored project passes the aggregate quality contract from committed lock state | FT-12.03 | `uv run poe archetype` (`tests/test_data_science_endpoints.py`) — **done** ([ADR 0055](adr/0055-validate-data-science-generated-projects.md)) | FT-12.03 / #111 |
| Wheel and sdist build, install into an isolated environment, import, and report `__version__`, metadata, and `py.typed` | FT-12.01 | `uv run poe archetype` (`tests/test_data_science_build.py`) — **done for `data-science` + `jupyter`** | FT-12.01 / #109 |
| Every generated target has an explicit Data Science or Foundation owner | FT-12.02 | `uv run poe check` (`tests/test_data_science_archetype.py`) — **done** ([ADR 0054](adr/0054-data-science-notebook-and-artefact-layout.md)) | FT-12.02 / #110 |
| The starter notebook is clean and executes | FT-12.02 | `uv run --locked poe notebook:check` in the generated project, via `uv run poe archetype` — **done** | FT-12.02 / #110 |
| Notebook validation is deterministic, output- and secret-free, and leaves the tracked notebook byte-identical | FT-11.02 | `uv run pytest tests/test_notebook_validator.py` — **done** | FT-11.02 / #106 |
| No generated example carries a secret, credential, binary model, or embedded dataset | FT-12.02 | `uv run pytest tests/test_data_science_notebook.py` plus this repository's `detect-private-key` / `check-added-large-files` hooks over the authored fragments — **done** (the engine path generates no `.pre-commit-config.yaml`; [ADR 0054](adr/0054-data-science-notebook-and-artefact-layout.md)) | FT-12.02 / #110 |
| Built artefacts contain no ignored `data/`, `models/`, or `artifacts/` content | FT-12.03 | `uv run poe archetype` (`tests/test_data_science_endpoints.py`) — **done** ([ADR 0055](adr/0055-validate-data-science-generated-projects.md)) | FT-12.03 / #111 |
| The generated project needs neither Forge repository for development, build, or runtime | FT-12.03 | `uv run poe archetype` (isolated venv) — **done** ([ADR 0055](adr/0055-validate-data-science-generated-projects.md)) | FT-12.01 / #109 |
| Repeated renders and manifest-order permutations produce identical output | FT-12.03 | `uv run poe check` (`tests/test_data_science_composition.py`) — **done** ([ADR 0055](adr/0055-validate-data-science-generated-projects.md)) | FT-12.03 / #111 |

### Python endpoint checks

`requires_python` for all three components is `>=3.11`
([data-science-capabilities.md](data-science-capabilities.md#shared-component-contract)),
which is satisfied at every endpoint by definition. Resolution is the separate
property: the *combined* dependency set must actually lock.

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| The `jupyter` development dependency set resolves at Python 3.11 and at 3.14 | FT-11.02 | `uv run pytest tests/test_jupyter_capability_build.py` — **done** | FT-11.02 / #106 |
| The `scientific-python` runtime dependency set resolves at Python 3.11 and at 3.14 | FT-11.03 | `uv run pytest tests/test_scientific_python_capability_build.py` — **done** | FT-11.03 / #107 |
| A Data Science project (with `jupyter`, and with `jupyter` + `scientific-python`) builds, installs, imports, and passes `notebook:check` at Python 3.11 and at 3.14 | FT-12.03 | `uv run poe archetype` (`tests/test_data_science_endpoints.py`, `-n 4`) — **done** ([ADR 0055](adr/0055-validate-data-science-generated-projects.md)) | FT-12.03 / #111 |
| `library` and `cli` retain their current single-selection build evidence as regression | FT-12.03 | `uv run poe archetype` (`tests/test_library_build.py`, `tests/test_cli_build.py`) plus the byte-level pin in `tests/test_data_science_composition.py` — **done** | FT-12.03 / #111 |

FT-12.03 built that machinery: `tests/test_data_science_endpoints.py` sweeps
each valid composition across `development` 3.11 and 3.14 (the floor stays
`data-science`'s fixed `>=3.11`), and `uv run poe archetype` now runs its
cases under `-n 4`. Building the sweep forced two content corrections in
already-merged capability content — the generated `mypy --strict` failed on
`pandas`/`sklearn` imports, and a `py314` target reformatted `check_notebooks.py`
into pre-3.14 syntax; both are recorded in
[ADR 0055](adr/0055-validate-data-science-generated-projects.md). The known
live constraint is the NumPy `>=2.4,<2.5` ceiling
([data-science-capabilities.md](data-science-capabilities.md#dependency-evidence)):
`2.5.0` drops Python 3.11, so a wider bound would fail the 3.11 endpoint. A
resolution failure at any endpoint is fixed by an upstream compatibility
review and a superseding ADR under the
[capability maintenance rules](data-science-capabilities.md#maintenance-and-compatibility),
never by silently widening a bound or raising the Python floor.

### Client and end-to-end checks

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| An installed `0.4` engine passes package and protocol negotiation; a `0.3` or out-of-range engine fails with the documented status before generation | CF-13.01 | `create-forge` contract tests | CF-13.01 / create-forge#106 |
| Interactive and non-interactive users can request a valid Data Science composition through `new --engine-preview` | CF-13.05 | `create-forge` preview-pipeline tests | CF-13.05 / create-forge#110 |
| The real console script generates Data Science, resolves its lock, and passes its canonical checks and notebook validation | CF-14.02 | `create-forge` end-to-end suite | CF-14.02 / create-forge#112 |
| Plain `create-forge` installs stay importable and usable without the engine extra | CF-13.01 | `create-forge` packaging tests | CF-13.01 / create-forge#106 |
| No component identifier, catalogue copy, or compatibility rule is duplicated into `create-forge` | CF-13.01 | `create-forge` review + tests | every CF Stage 13–14 child |

### Regression checks

The direct-Copier path cannot regress *through* Stage 11 or 12 content,
because no Stage 11–12 change touches `template/` or `copier.yml` — only
`src/forge_template/foundation/` and `src/forge_template/components/*/content`.
The Copier ladder is therefore a release gate, run once per published line,
not a per-child obligation.

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| All four Copier combos render and pass their own `poe check` | FT-12.04 | `uv run poe combos` — **done** in the protected [release commit run](https://github.com/Sandsy09/forge-template/actions/runs/33736737699) | FT-12.04 / #112 |
| `copier update` from the last tag preserves local edits and reaches HEAD | FT-12.04 | `uv run poe update` — **done** in the protected [release commit run](https://github.com/Sandsy09/forge-template/actions/runs/33736737699) | FT-12.04 / #112 |
| Existing fast, wheel, and archetype suites stay green | every child | `uv run poe check`, `poe check:wheel`, `poe archetype` | every Stage 11–12 child |
| `create-forge` Library, CLI Application, default-Copier, and no-engine paths are unchanged | CF-14.03 | `create-forge` regression suite | CF-14.03 / create-forge#113 |

## Valid and invalid selections

A ProjectSpec selects exactly one archetype and zero or more capabilities.
Data Science requires `jupyter` explicitly; the engine rejects an omitted hard
dependency rather than adding it silently
([data-science-capabilities.md](data-science-capabilities.md#data-science-requires-jupyter)).

| Selection | Outcome |
| --- | --- |
| `library` or `cli`, with none / `jupyter` / `scientific-python` / both | Valid |
| `data-science` + `jupyter` | Valid |
| `data-science` + `jupyter` + `scientific-python` | Valid |
| `data-science` alone | Rejected — unsatisfied `requires` edge, before rendering |
| `data-science` + `scientific-python`, no `jupyter` | Rejected — unsatisfied `requires` edge, before rendering |
| Two archetypes in one spec | Rejected — one archetype per spec |
| A capability ID given as the archetype, or an archetype ID as a capability | Rejected — wrong kind |
| The same component listed twice | Rejected — duplicate selection |
| An unknown component ID | Rejected — not in catalogue |

Every rejection is a structured `ForgeEngineError` raised before component
discovery completes or any content renders, matching the
[compatibility policy's](compatibility-policy.md#reporting-an-unsupported-forge-version)
fail-closed rule. `scientific-python` has no relationship to `jupyter`: a
project may take either, both, or neither where its archetype permits.

## Cross-repository release hand-offs

The one-way dependency `create-forge → forge-template → generated project`
holds, and the roadmap rule is that the provider merges and releases before
the client adopts the line. `create-forge`'s existing
[release-coordination order](https://github.com/Sandsy09/create-forge/blob/main/docs/integration-contract.md#release-coordination)
is authoritative for the client-side mechanics; this contract states the gates,
not a competing procedure.

| Gate | Owner | Entry criteria | Exit criteria |
| --- | --- | --- | --- |
| `forge-template` `0.4.0` | FT-12.04 / #112 — **complete** | Every Engine, Generated-project, Python-endpoint, and Regression row above passed on protected [`main`](https://github.com/Sandsy09/forge-template/actions/runs/33736737699); the [dry run](https://github.com/Sandsy09/forge-template/actions/runs/33737131150) was inspected | The [release run](https://github.com/Sandsy09/forge-template/actions/runs/33737307302), tag, [GitHub Release](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0), and [PyPI artefacts](https://pypi.org/project/forge-template/0.4.0/) name commit `91f1cc5606778379a10b1b7591c9d924e0ba6218`; installed discovery and both Data Science compositions passed the [published artefact audit](data-science-validation.md#published-040-release-verification) |
| `create-forge` `>=0.4,<0.5` adoption | CF-13.01 / create-forge#106 | `v0.4.0` is an immutable published target; contract tests pass against it | Engine extra is `>=0.4,<0.5`; lock refreshed; `0.3` and out-of-range engines fail before generation; plain installs unaffected |
| Reviewed `forge-template` `0.4.1` | FT-14.03 / #115 | FT-14.01 composition review and FT-14.02 cross-repository validation complete; dry-run inspected | Tag `v0.4.1`, release, PyPI artefacts, and engine metadata agree; isolated public-import, discovery, render, and generated-project validation pass |
| `create-forge` `0.3.0` | CF-14.04 / create-forge#114 | `v0.4.1` published; CF-14.01 adoption, CF-14.02 end-to-end, and CF-14.03 regressions complete | Tag `v0.3.0`; the released pair generates and validates the accepted Data Science compositions behind `--engine-preview`; both Stage 14 milestones close with no open issues |

Merging is not releasing. A merge to `main` leaves it untagged and invisible
to `copier update` and to a version-pinned engine client until
`release.yml` runs, exactly as
[CONTRIBUTING.md](../CONTRIBUTING.md#releasing) states. No version in this
repository changes when this contract merges.

## What Stages 11 and 12 may no longer decide

Each downstream issue inherits fixed answers from this contract and the three
earlier Stage 10 decisions. What genuinely remains open is narrow.

| Issue | Fixed by the Stage 10 contract set | Still owned by the issue |
| --- | --- | --- |
| FT-11.01 / #105 | **Complete.** [ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md) fixed the three point identifiers, the any-selected-owner and composition-order rules, the byte-neutral-when-empty guarantee, and the one recorded `check`-array reformat | — |
| FT-11.02 / #106 | **Complete.** `jupyter` at `1.0.0`, protocol `2`, ProjectSpec `[1]`, `>=3.11`, no options, no requires/conflicts; four development dependency lines; fixed tasks, validator, safe diagnostics, contributions, tests, and [ADR 0050](adr/0050-production-jupyter-capability.md) | — |
| FT-11.03 / #107 | `scientific-python` at `1.0.0`, same shared fields; the four runtime dependency lines and their bounds | **Complete.** [ADR 0051](adr/0051-production-scientific-python-capability.md): the packaged manifest, runtime dependency contribution, import test, guidance, and endpoint resolution evidence |
| FT-11.04 / #108 | The valid/invalid selection set above; determinism and path-free descriptor requirements | **Complete.** [ADR 0052](adr/0052-validate-production-capability-composition.md) and [capability-composition-validation.md](capability-composition-validation.md): the fixture catalogue and the assertions that exercise it |
| FT-12.01 / #109 | `data-science` at `1.0.0`, protocol `2`, `>=3.11`, `requires = [{ id = "jupyter", version = ">=1,<2" }]`, no options/conflicts, `uv-build-static`, generated version `0.1.0`, classifiers, reserved shape | **Complete.** [ADR 0053](adr/0053-production-data-science-archetype.md): the manifest, the owned `src/` tree and smoke tests, and the four packaging/metadata/classifier contributions |
| FT-12.02 / #110 | The five root-anchored ignore entries; the prose-only guidance reading; the output-free stdlib starter notebook; no tracked placeholder | **Complete.** [ADR 0054](adr/0054-data-science-notebook-and-artefact-layout.md): the four notebook cells, the README project-shape and working-directory fragment, and the `gitignore-project-shape` fragment |
| FT-12.03 / #111 | The Generated-project and Python-endpoint rows above; both valid compositions; the missing-Jupyter rejection | **Complete.** [ADR 0055](adr/0055-validate-data-science-generated-projects.md) and [data-science-validation.md](data-science-validation.md): the two test modules, the `-n 4` archetype task, the `library`/`cli` digest fixture, and two forced content corrections (`scientific-python` `mypy` ignores, `jupyter` `check_notebooks.py` `py314` `except` split) |
| FT-12.04 / #112 | `0.4.0`; every unchanged axis; the release gate above | **Complete.** [PR #128](https://github.com/Sandsy09/forge-template/pull/128), protected `main`, dry-run and publication workflows, [`v0.4.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0), [PyPI](https://pypi.org/project/forge-template/0.4.0/), and the [published artefact audit](data-science-validation.md#published-040-release-verification) |

## Alignment with existing contracts

| FT-10.04 acceptance criterion | Already owned | New here |
| --- | --- | --- |
| The acceptance matrix is executable and assigns each check to a repository | Foundation guarantees name the aggregate quality contract; `poe archetype`, `poe combos`, `poe update`, `poe check:wheel` already exist; `create-forge`'s integration contract owns client-side release mechanics | The five matrix tables, the command and owner per row, the "executable = the command exists when the stage arrives" reading, and the Python endpoint rows |
| Every versioned axis and compatibility consequence is classified | The [compatibility policy](compatibility-policy.md) defines the axes, the compatible-range rules, and the deprecation window; `python-support.md` owns the CPython window | The per-axis classification for the Data Science line, the `0.4.0` justification, `1.0.0` for the three new components, and the project-version-versus-component-version distinction |
| Stage 11 and Stage 12 issue scopes are decision-complete | ADR 0045/0046/0047 fixed the shape, capabilities, and safeguards | The per-issue "fixed / still owned" mapping and the valid/invalid selection set |
| Cross-repository release entry and exit criteria are explicit | `create-forge`'s integration contract defines the four-step breaking-change order and reserves exit status `3` | The four named gates with entry and exit criteria, bound to that order rather than restating it |

## Deferred decisions

This contract does not decide or implement:

- the `create-forge` capability and option selection UX, or its adoption of
  the `0.4` and `0.4.1` ranges — owned by create-forge Stages 13 and 14;
- the reviewed `0.4.1` package release — owned by FT-14.03; `0.4.0` is
  complete;
- admitting a new CPython release or moving the Python floor — owned by
  [python-support.md](python-support.md); or
- retiring the direct-Copier Library path, which remains a separate future
  initiative.

The original documentation decision changed no package dependency, manifest,
catalogue entry, public API, ProjectSpec, template, Copier answer, generated
output, tag, or release. The implementation and release evidence above records
the later stages that executed its accepted contract.
