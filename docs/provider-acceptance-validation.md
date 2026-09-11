# Provider acceptance, reproducibility and distribution validation

This is FT-17.05's evidence record: execution of the seven acceptance-matrix
rows it owns from
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md)
(FT-15.04 / [ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md)),
against the candidate `forge-template` `main` carrying FT-17.01 through
FT-17.04. Accepted by
[ADR 0066](adr/0066-validate-provider-parity-reproducibility-and-distributions.md).
It is the direct analogue of
[data-science-validation.md](data-science-validation.md) (FT-12.03) and
[cross-repository-validation.md](cross-repository-validation.md) (FT-14.02):
real commands, real output, one row per acceptance-matrix line.

## Why this exists

FT-17.02 and FT-17.03 tripled the discovered catalogue — five components to
fourteen — but every new component (`github`, and the eight FT-17.03
capabilities) was proven only by fast, in-memory render assertions. No
`archetype`-marked test built, installed, or ran `poe check` against a
composition that selected any of them; no enumeration of "every valid
composition" had been updated past the pre-Stage-17 ten; the provider's own
sdist had never been audited; and two acceptance rows cited test evidence
that did not actually prove them. FT-17.05 closes all four gaps.

## Validated revision

| Repository | Branch | Commit |
| --- | --- | --- |
| `forge-template` | `test/validate-provider-parity` (merges to `main`) | see the merge commit this document's PR records |

Local validation platform: Windows 11, Python 3.13.1 (development), sweeping
`library` / `cli` / `data-science` archetype endpoints per their own
documented floors. CI validates in parallel on `ubuntu-latest` (the primary
matrix) and `windows-latest` (the smoke job) — see
[.github/workflows/test-template.yml](../.github/workflows/test-template.yml).

## The seven FT-17.05-owned rows

| Row | Check | Evidence command | Result |
| --- | --- | --- | --- |
| E1 | The built wheel *and sdist* ship every manifest, contribution and owned resource, exclude repo tooling (wheel only — see below), and stay under their size ceilings | `uv run poe check:wheel` | Pass — see [Artefact identities](#artefact-identities) |
| E2 | Public signatures and result-model fields are unchanged bar the additive names | `uv run pytest tests/test_engine.py::test_public_callable_signatures_are_pinned tests/test_engine.py::test_public_result_model_fields_are_pinned` plus the isolated import in E1 | Pass |
| G1 | A project with `github` and selected capabilities builds, installs, and passes its own `poe check` including the type-check, coverage and pre-commit gates | `uv run pytest tests/test_full_composition_build.py -m archetype` | Pass — three cells, see [Full-composition build cells](#full-composition-build-cells) |
| G2 | The generated project needs neither Forge repository | Same run — the Forge-freedom probe in each cell | Pass |
| I1 | An independent client on the public facade renders every valid composition without a `create-forge` dependency | `uv run pytest tests/test_no_copy_inheritance.py -m sweep` plus `uv run poe crossrepo` | Pass provider-side (2240/2240); `poe crossrepo`'s create-forge half fails on a recorded, expected lag — see [Independence: what `poe crossrepo` shows](#independence-what-poe-crossrepo-shows) |
| I2 | The client never reads a component resource: negotiation and selection both work from path-free facts alone | `uv run pytest tests/test_compatibility_policy.py::test_client_selection_reads_no_component_resource tests/test_compatibility_policy.py::test_negotiation_precedes_discovery` | Pass |
| R1 | `library` / `cli` / `data-science` single-selection output is byte-identical to `0.4.1` bar approved additive fills | `uv run poe archetype` plus `tests/fixtures/archetype_regression/digests.json` | Pass — digest fixture unmoved (no archetype content changed; only `pre-commit`, which no digest-pinned composition selects) |

## Full-composition build cells

`tests/test_full_composition_build.py`, three cells (`library`, `cli`,
`data-science`), each paired with `github` and every capability it can carry:

| Cell | Capabilities |
| --- | --- |
| `library` | `changelog`, `coverage`, `dependabot`, `documentation`, `dotenv-example`, `jupyter`, `pre-commit`, `pyright`, `scientific-python` |
| `cli` | same, minus `documentation` (requires `library`) |
| `data-science` | same, minus `documentation` |

`renovate` is left out of every cell — it conflicts with `dependabot`, which
exercises the `dependabot` → `github` `requires` edge instead. Each cell:
`uv lock`, `uv sync --all-groups --locked`, `uv build` (wheel + sdist,
exactly one each, the sdist contains the package), isolated install and
`__version__` check, `uv run --locked poe check`, a real `git init` +
`uv run pre-commit run --all-files`, and the Forge-freedom probe at both
build time (the lockfile) and install time (a clean venv). All three passed.

`coverage.fail_under` is set to `80` (its default, `0`, disables the gate
entirely — leaving it there would make row G1's "including the ... coverage
... gate" a no-op assertion). Measured: **100%** coverage on every cell's
trivial generated smoke test (`src/<package>/__init__.py`, 4 statements).

### A defect this validation found

The first full-composition cell (`library`) failed
`pre-commit run --all-files` on its first run: `check-added-large-files`
(500 KB default, no override) rejected the generated project's own
`uv.lock` — 636 KB once `jupyter` and `scientific-python` were both
selected, a fully realistic composition. Measured for scale:

| Composition | `uv.lock` size |
| --- | --- |
| no capabilities | 100 KB |
| `jupyter` only | 340 KB |
| `jupyter` + `scientific-python` + every other capability | 636 KB |

Confirmed with the maintainer: fixed in this issue rather than deferred.
`pre-commit`'s own upstream documentation names lockfiles as the standard
exclusion for this hook (large by design, not "added by mistake"). One line,
`exclude: ^uv\.lock$`, added to
`src/forge_template/components/pre-commit/content/.pre-commit-config.yaml.jinja`;
`pre-commit` moved `1.0.0` → `1.0.1`. See
[ADR 0066](adr/0066-validate-provider-parity-reproducibility-and-distributions.md#a-defect-the-validation-itself-found).
All three cells passed `pre-commit run --all-files` clean after the fix.

## The exhaustive composition sweep

`tests/composition_matrix.py::valid_compositions()` derives every selection
the installed catalogue accepts from `discover_components()`'s own path-free
`requires` / `conflicts` edges — no component resource is read to compute it.
Post-FT-17.03 the count is **2240** (3 archetypes × subsets of 10
capabilities × `github` on/off, minus the four `requires`/`conflicts` edges),
up from the pre-Stage-17 ten every prior enumeration in this repository still
meant.

`tests/test_composition_sweep.py` (`sweep`-marked, `-n 4 --no-cov`) plans and
renders all 2240 — proving row R1's byte-identity claim and the composition
contracts generalise past the ten compositions earlier suites covered. All
2240 passed. `--no-cov` is deliberate: coverage.py's branch tracing
measurably slows this volume of CPU-bound in-process calls (unlike
`combos`/`archetype`/`crossrepo`, dominated by subprocess wall time), and
every line the sweep exercises is already covered by `poe check`.

Combined with the independent-client sweep below (also 2240, also
`sweep`-marked, sharing the same marker so a local `uv run poe sweep` runs
both), the real total is 4481 cases (2 × 2240 + one tripwire), measured at
**~47 minutes in one `-n 4` job** — a genuine cost, not the ~7-8 minutes this
issue's plan first estimated (which budgeted for only one sweep). CI splits
the two sweeps into parallel jobs (`sweep-composition`,
`sweep-independence`), keeping the critical path close to the existing
`archetype` job's ~22-minute pole rather than doubling total required CI
time; the local `poe sweep` task is unchanged and still runs both together.

## Independence: what `poe crossrepo` shows

`tests/no_copy_downstream.py` / `tests/test_no_copy_inheritance.py`'s new
`test_downstream_client_renders_every_valid_composition_identically` proves
row I1's provider-side half exhaustively: for every one of the 2240
compositions, a policy-resolved client consuming only the public
`forge_template` facade renders byte-for-byte identically to a direct
`render_project` call, with no Forge runtime dependency in the result. All
2240 passed.

`poe crossrepo` was run against the paired local sources to record the
client-consumption half honestly rather than skip it: **19 passed, 1
failed** in 611s.
`test_create_forge_cross_repository_contract_passes_against_the_local_engine`
is the one failure — it shells out to create-forge's own canonical
`tests/test_engine_cross_repository.py`, which fails at collection:
create-forge `main` (`9a911e5`) constructs `EngineInfo(...)` at
`tests/test_engine_cross_repository.py:62` without the FT-17.01
`metadata_version` field, which `EngineInfo` has required since `0.4.1`'s
successor line. (The same root cause — `EngineInfo(...)` missing
`metadata_version` — also appears in create-forge's own `tests/test_cli.py`,
`tests/test_data_science_pipeline.py`, `tests/test_downstream_reference.py`
and `tests/test_engine_adapter.py` helpers, per a source grep; `poe
crossrepo` itself exercises only the one file above.) This is not a defect
in either repository: the cross-repository release-gate table
([cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md#cross-repository-release-gates))
places `create-forge`'s `metadata_version`-aware adoption at **CF-18.01,
strictly after** the `0.5.0` release this repository has not yet performed.
Editing the sibling checkout is out of scope here and would pre-empt
CF-18.01's own reviewed adoption step. **Owner: CF-18.01 / FT-18.01.**

## Artefact identities

`uv run poe check:wheel` builds both a wheel and an sdist into a fresh
temporary directory, applies the content/size/isolated-import checks to
each, and prints each artefact's identity:

| Artefact | Size | SHA-256 |
| --- | --- | --- |
| `forge_template-0.4.1-py3-none-any.whl` | 108,244 bytes | `1014021e59c8fbb70db3f01f595941b065632572106007b9249d9b2035464076` |
| `forge_template-0.4.1.tar.gz` | 725,771 bytes | `fa7c431fff98c97450d7c99415b360ec5ecb64d50f7d1ebe927f50450a0830fa` |

Both are local build measurements from this validation, not published
artefacts — FT-17.06 performs the real `release.yml` run and its own
published-artefact audit. The wheel stays under `_MAX_WHEEL_BYTES`
(131,072 bytes / 128 KiB); the sdist — which correctly carries the full
repository, since no `[tool.hatch.build.targets.sdist]` override narrows it —
stays under the new `_MAX_SDIST_BYTES` (2,097,152 bytes / 2 MiB). Both
isolated-import smoke tests now also negotiate via `get_engine_info()` and
render one composition end to end, not only call `discover_components()`.

The content-tree size pin
(`tests/test_composition_architecture_review.py::test_package_content_size_matches_the_recorded_review_baseline`)
moved with the `pre-commit` fix: 112 files, 68,954 bytes (was 68,378 — the
576-byte `exclude:` addition). File count and duplicate overhead (892 bytes)
are unaffected.

## Regression

`uv run poe archetype` (all modules, including the new
`test_full_composition_build.py`) and
`tests/fixtures/archetype_regression/digests.json` together prove row R1: no
archetype's single-selection output moved. `poe combos` and `poe update`
(the direct-Copier regressions) were run unchanged — this issue touches no
`copier.yml` or `template/**` path.

## Scope held

No `EngineErrorCode` was added (still nine, unchanged since ADR 0061). No
component version moved except `pre-commit` (`1.0.0` → `1.0.1`, a recorded
content fix — see above); `foundation_version` stays `1`; no
`copier.yml` or `template/**` change. `main` stays `0.4.1` and untagged —
FT-17.06 releases `0.5.0`.
