# CLAUDE.md — forge-template

Guidance for Claude Code working in this repository.

## What this is

A [Copier](https://copier.readthedocs.io/) template and public composition
engine that scaffold modern Python projects. The source catalogue contains
independent **library**, **CLI Application**, and **Data Science** archetypes
plus the optionless **Jupyter** and **Scientific Python** capabilities. The
published [`v0.4.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0)
catalogue contains all five components with the public facade and protocol
tuples unchanged from `0.3.x`. The direct-Copier compatibility path remains
Library-only.

Copier was chosen over Cookiecutter specifically for `copier update`, which
three-way merges template changes into projects generated months earlier. Every
decision here is downstream of preserving that capability. See
[docs/adr/0002](docs/adr/0002-copier-over-cookiecutter.md) for the full
rationale and its consequences.

## Repository relationship

| Repo | Role |
| --- | --- |
| `https://github.com/Sandsy09/forge-template` | This repo. The templates. |
| `https://github.com/Sandsy09/create-forge` | The CLI that scaffolds from it. |

Separate because Copier resolves template versions from PEP440 git tags here.
**Do not merge them.** See
[docs/adr/0003](docs/adr/0003-two-repo-split.md).

## Layout

```text
forge-template/
├── copier.yml              Question schema. MUST be at root.
├── pyproject.toml          This repo's OWN tooling — NOT part of the scaffold
├── src/forge_template/     Repository checks plus the public template engine
├── tests/                  pytest suite: schema, ADRs, combos (slow), update (slow)
├── docs/adr/               Why past decisions were made (Nygard-format ADRs)
├── scripts/
│   └── verify-ci.sh        Push `poe combos` output to throwaway repos, watch CI
├── .github/workflows/
│   ├── test-template.yml   This repo's CI
│   └── release.yml         Manual tag + release
└── template/               EVERYTHING here becomes the scaffold
```

Nothing inside `template/` describes the template itself. `copier.yml`,
`pyproject.toml`, `src/`, `tests/`, scripts, and this repo's own CI stay at
root and are excluded via `_subdirectory: template`. `src/forge_template` is
not scaffold code — it holds the checks (`schema.py`, `adr.py`, `render.py`,
`github_actions.py`) that both `poe check` and
`tests/test_combos.py`/`test_update.py` call, plus the public engine facade.
Since [ADR 0036](docs/adr/0036-publish-the-engine-to-pypi.md), those two
halves diverge at the published wheel: `pip install forge-template` ships
only the facade and the `foundation`/`components` content trees the checks
modules do not touch — `[tool.hatch.build.targets.wheel]`'s `exclude` list
names the four checks modules by path, `scripts/check_wheel.py` (`poe
check:wheel`) verifies the split holds on every CI run, and this is why
`pyyaml` (needed only by `schema.py`/`render.py`) stays a dev-group-only
dependency rather than a runtime one — see
[forge-template#8](https://github.com/Sandsy09/forge-template/issues/8),
closed by that decision. Editable installs (`uv sync --all-groups`) are
unaffected; the exclusion applies only to the built wheel. The strict
[ProjectSpec protocol](docs/project-spec.md) models live in
`project_spec.py`,
[organisation policy protocol](docs/organisation-policy.md) `1` is a
documentation contract with an executable, test-only reference resolver
([organisation-policy-fixtures.md](docs/organisation-policy-fixtures.md),
`tests/organisation_policy_contract.py`, [ADR
0040](docs/adr/0040-organisation-policy-reference-fixture.md)): still do not
add policy parsing, resolution, public exports, or `ForgeEngineError` values
to `src/forge_template` itself — a shipped implementation remains
unscheduled,
[component manifest protocol](docs/component-manifests.md) models and loader
in `component_manifest.py` (manifest protocols `1` and `2`), the implicit
[Foundation content source](docs/component-manifests.md#foundation-content-source)
in `foundation_source.py`,
[composition order](docs/composition-order.md) tier and within-tier ordering
in `composition.py`,
[file conflict and override rules](docs/file-conflicts.md) rendered output
target ([ADR 0032](docs/adr/0032-render-component-content-paths.md)) and
collision resolution in `file_conflicts.py`, the
[safe override and extension points](docs/extension-points.md) contract
([ADR 0039](docs/adr/0039-deny-policy-file-overrides.md)) denying any
`override` grant and publishing the extension-point inventory as a versioned
contract, pinned by `tests/test_extension_points.py`, and the
[template variable contract](docs/template-variables.md) rendered namespace
and option-schema vocabulary (protocols `1` and `2`, `format` support) in
`template_variables.py`. The supported
[template-engine API](docs/template-engine-api.md) in `engine.py` exposes
package-bound discovery, strict validation, deterministic planning, in-memory
rendering, structured failures, and the `map_legacy_library_answers` helper
from the top-level package, at package version `0.4.0`. The `0.4.x` line keeps
the `0.3.x` public facade and protocol tuples while adding the Data Science
catalogue; ADR 0037's Stage 08 review and ADR 0056's Stage 14 confirmation
define its Foundation boundary. The
[Forge-Blueprint compatibility policy](docs/compatibility-policy.md)
([ADR 0041](docs/adr/0041-forge-blueprint-compatibility-policy.md)) defines
every versioned axis above (package, both protocols, component versions,
option-schema and Foundation source protocols), compatible ranges, a
90-day-plus-one-release deprecation window, and the facts a conformant
unsupported-version report must carry, pinned by
`tests/test_compatibility_policy.py`.
The [no-copy inheritance proof](docs/no-copy-inheritance.md)
([ADR 0042](docs/adr/0042-validate-no-copy-downstream-inheritance.md)) closes
forge-template Stage 09: `tests/no_copy_downstream.py` consumes only the
top-level public facade, real-catalogue equivalence is byte-for-byte, and the
private fixture catalogue separately demonstrates additive selected-component
extensions. Never present that private override as a plugin or client
distribution mechanism.
Its
[generated-project validation](docs/generated-project-validation.md) checks
plan/output agreement, universal `pyproject.toml` metadata, and completed
Forge extension rendering before a result is returned. **The source catalogue
now holds three independent reference archetypes plus the Jupyter and
Scientific Python capabilities**:
FT-08.02
populated it with `library`
([contract](docs/library-archetype.md)/[ADR 0033](docs/adr/0033-migrate-library-production-catalogue.md)),
FT-08.04 added `cli`
([contract](docs/cli-application-archetype.md)/[ADR 0035](docs/adr/0035-implement-cli-application-archetype.md)),
and FT-12.01 added `data-science`
([contract](docs/data-science-archetype.md)/[ADR 0053](docs/adr/0053-production-data-science-archetype.md)),
with FT-12.02 completing its notebook and working-tree shape
([ADR 0054](docs/adr/0054-data-science-notebook-and-artefact-layout.md)) and
FT-12.03 validating both compositions end to end
([contract](docs/data-science-validation.md)/[ADR 0055](docs/adr/0055-validate-data-science-generated-projects.md)),
all alongside the implicit Foundation source at `src/forge_template/foundation/`;
FT-11.02 adds the optionless `jupyter` capability without a notebook or
runtime dependency; FT-11.03 adds the independently optional
`scientific-python` runtime stack and component-owned import test. `data-science`
declares `requires = [{ id = "jupyter", version = ">=1,<2" }]` — the archetype,
not the capability, owns that edge — and is rejected before rendering when
`jupyter` is not also selected. `uv run poe
archetype` (since FT-12.03 `pytest -m archetype -n 4`) proves real
wheels/sdists for
Library across all three packaging modes and for CLI's fixed packaging mode,
plus a real installed console script and `python -m` invocation; it also
proves both archetypes' locked aggregate checks with Jupyter selected, and a
real Data Science wheel/install/`__version__`/`py.typed` plus its own locked
`poe check` — which since FT-12.02 runs `notebook:check`
over the real starter notebook and a live kernel, and since FT-12.03 sweeps
both `data-science` compositions (with and without `scientific-python`) across
Python 3.11 and 3.14.
`discover_components()` now returns
`("cli", "data-science", "jupyter", "library", "scientific-python")`. No
archetype inherits from or reads
resources from another; a ProjectSpec selects exactly one. These
contracts are not
yet consumed by the direct-Copier path; see
[#5](https://github.com/Sandsy09/forge-template/issues/5), done,
[#32](https://github.com/Sandsy09/forge-template/issues/32),
[#33](https://github.com/Sandsy09/forge-template/issues/33),
[#34](https://github.com/Sandsy09/forge-template/issues/34),
[#35](https://github.com/Sandsy09/forge-template/issues/35),
[#36](https://github.com/Sandsy09/forge-template/issues/36),
[#37](https://github.com/Sandsy09/forge-template/issues/37), and
[#38](https://github.com/Sandsy09/forge-template/issues/38), all done. The composition,
file-conflict, template-variable, and rendering contracts are proven to
compose into one deterministic artefact by
[composition-fixtures.md](docs/composition-fixtures.md)'s golden fixtures,
exercised through the public facade with a private fixture-catalogue override.
Never expose that override or accept arbitrary catalogue roots in the public
API — the mirrored `_FOUNDATION_ROOT_OVERRIDE` seam carries the identical
rule. Destination staging and finalisation remain `create-forge`
responsibilities; keep engine validation in memory.

## The question schema

`copier.yml` is the contract. Once projects exist in the wild, changing it is
expensive.

Key mechanics:

- **`build_backend` and `versioning` are a linked pair.** `versioning` is only
  asked when Hatchling is chosen; `versioning_resolved` is a hidden computed
  value that collapses to `static` for `uv_build`. **All templates read
  `versioning_resolved`, never `versioning`.** This makes the invalid
  combination unrepresentable rather than merely unselected, which matters
  because `copier update` replays stored answers. Full rationale:
  [docs/adr/0004](docs/adr/0004-build-backend-and-versioning.md).
- **`python_matrix` is computed**, sliced from `python_all` between
  `python_min_version` and `python_version`. Version additions, default moves,
  deprecations, and removals follow the
  [Python support policy](docs/python-support.md); changing `python_all` alone
  is not a complete support transition.
- **Computed values use `when: false`** with the value in `default`.
- **`github_org` has an empty default** deliberately. The CLI supplies it.

## Invariants — do not break these

Six hard rules, with full rationale, live in
[docs/invariants.md](docs/invariants.md). Read it before changing anything
under `template/` or `copier.yml`. The numbering is stable and is cited
from ADRs and code comments.

1. [Generated output must be pre-commit clean](docs/invariants.md#1-generated-output-must-be-pre-commit-clean)
2. [`.copier-answers.yml` must be generated and committed](docs/invariants.md#2-copier-answersyml-must-be-generated-and-committed)
3. [Moving or deleting files under `template/` breaks updates](docs/invariants.md#3-moving-or-deleting-files-under-template-breaks-updates)
4. [Jinja and GitHub Actions both use `${{ }}`](docs/invariants.md#4-jinja-and-github-actions-both-use--)
5. [`.gitattributes` is mandatory, in the template AND at repo root](docs/invariants.md#5-gitattributes-is-mandatory-in-the-template-and-at-repo-root)
6. [Every template change that should reach users needs a tag](docs/invariants.md#6-every-template-change-that-should-reach-users-needs-a-tag)

## Conditional filenames

Optional files use conditional names — when the name renders empty, the file is
skipped:

```text
template/{% if use_docs %}mkdocs.yml{% endif %}.jinja
template/{% if dependency_updates == 'renovate' %}renovate.json{% endif %}.jinja
```

Works for directories too. Files needing no rendering (`py.typed`,
`.editorconfig`) carry no `.jinja` suffix — `py.typed` in particular **must
stay byte-empty**.

## Workflow

Every change is a branch (`<type>/<short-slug>`) and a pull request into
`main`, squash merged — never commit directly to `main`. See
[CONTRIBUTING.md](CONTRIBUTING.md) and
[docs/adr/0009](docs/adr/0009-branch-and-pr-workflow.md).

## Validation

Run in this order. All five currently pass.

```bash
uv run poe check             # fast: this repo's own lint/typecheck + schema/ADR/render unit tests
uv run poe combos            # slow: 4 combos in parallel, render assertions, each combo's own poe check
./scripts/verify-ci.sh <org> # pushes poe combos' output to throwaway repos, watches CI
uv run poe update             # slow: both copier update scenarios (local edits survive; latest tag -> HEAD)
uv run poe archetype          # slow: real uv build/install/import for the Library archetype, 3 packaging modes
```

`poe check`, `poe combos`, `poe update`, and `poe archetype` are all `pytest`
under a marker select (`tests/test_combos.py` / `tests/test_update.py` /
`tests/test_library_build.py` carry the `combos` / `update` / `archetype`
markers; `poe check` runs everything else). `tests/`, ported from the
former `scripts/test-combos.sh` and `scripts/test-update.sh` — see
[#5](https://github.com/Sandsy09/forge-template/issues/5), done — is a single
definition of every assertion, called from both here and CI's
`test-template.yml`, closing the duplication that let CI and the local script
drift (see below). `poe combos` scaffolds from a **non-git snapshot** by
default (`tests/conftest.py`'s `template_snapshot` fixture) so uncommitted
edits are picked up, matching what `test-combos.sh` did; pass `--from-git` (a
`pytest` option registered in `conftest.py`) to scaffold from real git history
instead, which is what CI does since `_commit` must be recorded.
`tests/test_update.py` always uses real git history — updates need real tags
regardless.

Combo 4 (kitchen sink) flips every remaining conditional at once. It has caught
real bugs the other three missed — including all 11 byte-empty template files
below, once an eighth assertion (no zero-byte file in rendered output, outside
a `py.typed`/`tests/__init__.py` allowlist) was added. Keep both.

**Local-green does not mean CI-green — verify actual GitHub Actions runs, not
just `poe combos` locally.** The `lint` job's shellcheck step, and three
separate bugs in `scaffold`/`windows`/`update-compat` (git identity missing on
the runner; a Jinja-leftover regex broader than `test-combos.sh`'s that
false-positived on the intentionally-raw git-cliff Tera block; scaffolding
from a relative `.` path, which made `_src_path` resolve wrong once `copier
update` ran from inside the scaffolded project) — all of this sat broken on
`main` since at least 2026-08-16, invisible because `needs: lint` meant one
early failure hid everything downstream. `test-combos.sh` never caught any of
it because it ran entirely locally, on a machine that already has a git
identity configured and doesn't reproduce the CI runner's environment. Fixed
2026-08-21; `gh run view <run-id>` on the actual push is the only way to know
CI is real, not just that the local suite exited 0. The git-identity class of
bug specifically is now closed for good rather than just fixed once:
`tests/conftest.py`'s `_git_identity` autouse fixture supplies one whenever
the environment (local or CI) doesn't already have one, so CI's workflow no
longer needs its own `git config --global` steps.

The shellcheck failure specifically was possible because shellcheck existed
**only** in CI, with no local config to catch it first. Closed by adding a
root `.pre-commit-config.yaml` (which the `lint` job now runs directly via
`uv run pre-commit run --all-files`, replacing the hand-rolled apt-get +
shellcheck steps) — see backlog item 1, done.

## Current state

Working: Library, CLI Application, and Data Science archetypes plus the
package-bound Jupyter and Scientific Python capabilities on `main`, with the
two-capability composition layer validated end to end (FT-11.04 / ADR 0052 —
Stage 11 closed) and the Data Science line published (FT-12.04 — Stage 12
closed); all four Copier combos green
locally and in CI, update merge validated, root and template
`.gitattributes` both in place, no byte-empty template files remain,
`task_runner`/`make` removed (it was the one untested, 100%-broken
conditional — see Deferred). **`v0.4.0` is the latest tagged release and the
first published five-component Data Science line.** `v0.3.2` carries the
reviewed Stage 08 boundary corrections. `v0.3.0` first carried
the production
engine catalogue (both `library` and `cli`) alongside the direct-Copier
template. Root repo hygiene is done:
root
`pyproject.toml`, `.pre-commit-config.yaml`, and real content for `LICENSE`,
`README.md`, `CONTRIBUTING.md`, `SECURITY.md` all exist; `src/forge_template`
holds checks for `copier.yml` itself (layout, computed-value defaults, the
`versioning`/`versioning_resolved` indirection), exercised by `tests/` and run
via `uv run poe check`, which the `lint` CI job now calls directly.
`docs/adr/` holds contiguous ADRs through 0056 recording the rationale behind
decisions already made, checked for internal consistency by
`src/forge_template/adr.py`. `scripts/test-combos.sh`/`test-update.sh` are
gone: ported to `tests/test_combos.py`/`test_update.py`, backed by
`src/forge_template/render.py` and run in parallel via `pytest-xdist` (`poe
combos -n 4`) — see [#5](https://github.com/Sandsy09/forge-template/issues/5),
done. `copier.yml` also gained two schema checks issue #5 asked for:
`check_question_usage` (every question is referenced under `template/**` and
vice versa) and `check_conditional_filenames` (every `{% if %}name{% endif %}`
path renders to a valid filename or empty, never something in between).

## Roadmap work

The completed
[Foundation roadmap](docs/roadmap-v1/github-issues/forge-template/ISSUE-INDEX.md)
is the historical source for Stages 00–09. The live
[Data Science epic index](docs/roadmap-v2/github-issues/forge-template/ISSUE-INDEX.md)
continues through Stages 10–14 under
[ADR 0044](docs/adr/0044-plan-data-science-as-the-third-archetype.md): a
package-backed, notebook-oriented third archetype, reusable optional
  capabilities, and create-forge delivery that remains behind
  `--engine-preview`. All 24 child issues are filed and attached to their
  epics; GitHub issue bodies and native relationships are authoritative.
FT-10.01's [Data Science contract](docs/data-science-archetype.md) now fixes
the future optionless package, test, starter-notebook, ignored working-tree,
and ownership shape without adding it to the production catalogue.
FT-10.02's [initial capability contracts](docs/data-science-capabilities.md)
define reusable optionless `jupyter` development tooling and an independently
optional `scientific-python` runtime stack. Data Science explicitly requires
Jupyter. FT-11.02 ships Jupyter in the source catalogue; FT-11.03
ships Scientific Python.
FT-10.03's [notebook, data, and model safeguards](docs/notebook-data-and-model-safeguards.md)
([ADR 0047](docs/adr/0047-notebook-data-and-model-safeguards.md)) fix the
fail-closed `notebook:check` validation order, the 300-second per-cell
nbclient timeout on a discarded temporary copy, ten deterministic failure
identifiers, output- and secret-free diagnostics, and the reading that
"guidance markers remain tracked" means the root README prose and
root-anchored `.gitignore` entries only — no `.gitkeep` or per-tree README,
so ADR 0045 stands. `notebook:check` is a generated-project task, not an
engine check, and adds no `ForgeEngineError` code.
FT-10.04's
[compatibility and acceptance contract](docs/data-science-compatibility-and-acceptance.md)
([ADR 0048](docs/adr/0048-data-science-compatibility-and-acceptance.md))
closes Stage 10: the Data Science rollout moves only the package version
(`0.3.2` → `0.4.0`, reviewed `0.4.1`) and the discovered-component set (three
new components at `1.0.0`), leaving every protocol and the public engine
facade unchanged; acceptance is an executable matrix whose rows each name one
non-interactive command and one FT- or CF-repository owner; dependency
resolution is swept at Python 3.11 and 3.14; and four release gates bind to
create-forge's existing coordination order. No version was bumped by the
decision itself — FT-12.04 has performed the `0.4.0` release and FT-14.03
retains the later `0.4.1` release. **Stage 10 is complete.**

Stage 11 (`FT-EPIC-11 / #97`) delivers the reusable capability layer.
FT-11.01's
[capability-tooling extension points](docs/extension-points.md#capability-tooling-extends-the-same-foundation-content)
([ADR 0049](docs/adr/0049-foundation-capability-tooling-extension-points.md))
grow the published Foundation inventory from eight points to eleven —
`pyproject-development-dependencies`, `pyproject-task-definitions`, and
`pyproject-aggregate-check` on `content/pyproject.toml.jinja` — so a selected
*capability*, not only an archetype, can attach a dev dependency, a Poe task,
and an aggregate-`check` entry. Additive: `foundation_version` stays `1`, no
engine module or public signature changes, `library`/`cli` stay at `1.0.1`,
and their generated output is byte-for-byte unchanged except the aggregate
`check` array is now multi-line (a recorded, semantics-preserving reformat so
a marker line fits inside it). Any selected owner may contribute; multiple
contributions compose in composition order, never last-write-wins; an
unfilled point emits zero bytes. A capability's `.gitignore` and README
guidance route through the existing `gitignore-project-shape` /
`readme-project-shape` points — no new point for either. Pinned by
`tests/test_extension_points.py` (inventory) and
`tests/test_capability_extension_points.py` (behaviour). **FT-11.01 is
complete.** FT-11.02 / #106 then ships `jupyter` `1.0.0`: a package-bound,
optionless capability with no requirements, conflicts, runtime dependencies,
or notebook content. It contributes four development dependencies,
`notebook` and `notebook:check`, the aggregate-check entry, README safety
guidance, and `.ipynb_checkpoints/`; its literal
`scripts/check_notebooks.py` validates every notebook structurally before
executing byte-identical temporary copies with nbclient. Diagnostics expose
only relative paths, optional zero-based cell indexes, fixed safe messages,
and ten stable codes. [ADR 0050](docs/adr/0050-production-jupyter-capability.md)
records the choices. FT-11.03 / #107 then ships `scientific-python` `1.0.0`,
its four bounded runtime dependencies, generated import test, and guidance
under [ADR 0051](docs/adr/0051-production-scientific-python-capability.md).
FT-11.04 / #108's
[capability composition validation](docs/capability-composition-validation.md)
([ADR 0052](docs/adr/0052-validate-production-capability-composition.md))
closes Stage 11: `tests/test_capability_composition.py` proves both
capabilities compose across `library` and `cli`, every documented invalid
selection fails closed as a structured `ForgeEngineError` before rendering
(`operation` is `parse` or `validate`, never `render`), descriptors stay
path-free, Foundation and every capability-free render name no capability or
domain tool, and no composition depends on a Forge package. Three test-only
synthetic capabilities under `tests/fixtures/capability_composition/`
(`requires-jupyter`, `conflicts-jupyter`, `optioned-tooling`) exercise the
`requires`/`conflicts`/options paths the production catalogue cannot reach;
`requires-jupyter` rehearses the exact `jupyter >=1,<2` edge FT-12.01's
`data-science` archetype declares. `scripts/check_wheel.py` now also
requires every component's `component.toml` and `extensions/` tree, plus
`foundation.toml` and `library/options.schema.json`. No manifest, content,
engine module, public signature, `EngineErrorCode`, or version changes.
**FT-11.01 through FT-11.04 are complete; `FT-EPIC-11 / #97` and its milestone
are closed.**

Stage 12 (`FT-EPIC-12 / #98`, milestone *Data Science Archetype — Stage 12*)
adds the third archetype and publishes `0.4.0`. FT-12.01 / #109's
[Data Science archetype](docs/data-science-archetype.md)
([ADR 0053](docs/adr/0053-production-data-science-archetype.md)) ships
`data-science` `1.0.0`: an independent, package-backed archetype declaring
`requires = [{ id = "jupyter", version = ">=1,<2" }]`, owning
`src/<package>/__init__.py` (byte-identical to `library`'s), `py.typed`,
`tests/__init__.py`, and `tests/test_smoke.py`, and contributing through the
four archetype-neutral pyproject points (`build-system`, `archetype-metadata`,
`build-configuration`, `classifiers`) exactly as `cli` does — fixed
`uv-build-static`, generated version `0.1.0`, and the three scientific
classifiers. Selecting it without `jupyter` is rejected as
`INVALID_COMPONENT_SELECTION` / `validate` from both `plan_generation` and
`render_project`, never `render`. `tests/test_data_science_archetype.py`
(fast) and `tests/test_data_science_build.py` (`archetype`-marked, real
build/install) cover it. No engine module, public signature, `EngineErrorCode`,
protocol integer, Foundation file, existing component, or package version
changes; `library`/`cli` stay `1.0.1`, both capabilities stay `1.0.0`, the
package stays `0.3.2` and untagged. FT-12.02 / #110's
[notebook and artefact layout](docs/notebook-data-and-model-safeguards.md)
([ADR 0054](docs/adr/0054-data-science-notebook-and-artefact-layout.md)) then
completes the archetype's generated shape within the same `1.0.0` component:
an output-free, stdlib-and-package-only
`content/notebooks/getting-started.ipynb.jinja`, a `gitignore-project-shape`
contribution carrying the five root-anchored working-tree entries
(`/data/raw/` … `/artifacts/`, ahead of `jupyter`'s `.ipynb_checkpoints/`),
and a `readme-project-shape` contribution documenting the package/test/notebook
structure and the ignored `data/`, `models/`, and `artifacts/` trees — no
`.gitkeep` or per-tree placeholder. It also corrects one
[compatibility-and-acceptance](docs/data-science-compatibility-and-acceptance.md)
row whose evidence named a generated-project pre-commit run the engine path
does not produce. `tests/test_data_science_notebook.py` (fast: nbformat
cleanliness, real `ruff check`/`format --check` over the rendered project,
stdlib-only imports, no-payload, ignored-tree discovery) is added;
`tests/test_data_science_build.py`'s generated `poe check` now runs
`notebook:check` over a real notebook and kernel. `scripts/check_wheel.py`
needs no change. `library`/`cli` render byte-for-byte unchanged. FT-12.03's
[generated-project validation](docs/data-science-validation.md)
([ADR 0055](docs/adr/0055-validate-data-science-generated-projects.md)) then
proves the matrix: `tests/test_data_science_composition.py` (fast:
determinism under repetition/reorder/catalogue-layout/`PYTHONHASHSEED`, the
archetype rejections, Forge-freedom, `ruff format` clean at every floor incl.
`py314`, and a `{target: sha256}` regression pin on `library`/`cli` in
`tests/fixtures/archetype_regression/digests.json`, regenerated with
`--update-goldens`) and `tests/test_data_science_endpoints.py`
(`archetype`-marked: both compositions × Python 3.11/3.14 through lock, sync,
build, isolated install, and the generated `poe check` incl. a live-kernel
`notebook:check`; ignored-tree artefact exclusion; Forge-free install).
`poe archetype` now runs `pytest -m archetype -n 4`. Building the sweep forced
two content corrections in already-merged capability content —
`scientific-python`'s `tests/test_scientific_python.py` gains
`# type: ignore[import-untyped]` on `pandas`/`sklearn` (generated `mypy
--strict`), and `jupyter`'s `scripts/check_notebooks.py` splits one
`except (OSError, UnicodeError)` into two clauses (ruff at `target-version =
py314` rewrites it to pre-3.14 syntax); both components stay `1.0.0`. FT-12.04
prepared the package in [PR #128](https://github.com/Sandsy09/forge-template/pull/128),
then published and verified
[`forge-template 0.4.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0)
on [PyPI](https://pypi.org/project/forge-template/0.4.0/), with the public API
and protocols unchanged. **FT-12.01 through FT-12.04 are complete;
`FT-EPIC-12 / #98` and its milestone are closed.**

Create-forge Stage 13 is complete. Its current `main` branch constructs and
consumes ProjectSpec behind `new --engine-preview` with the compatible
`forge-template>=0.4,<0.5` range. FT-14.01 / #113's
[three-archetype composition review](docs/composition-architecture-review.md)
([ADR 0056](docs/adr/0056-three-archetype-composition-boundary-review.md))
finds no production boundary defect, records all deliberate duplication and
all eleven Foundation extension points, and deterministically exercises all
ten valid compositions. FT-14.02 / #114 is the next actionable issue;
FT-14.03 / #115 alone owns the reviewed `0.4.1` release. Stage 14 remains open.

FT-08.02 populated the
production component catalogue under the
[Library archetype contract](docs/library-archetype.md) — additive, package-bound
content that leaves `template/` untouched. FT-08.04 (repurposed
[#4](https://github.com/Sandsy09/forge-template/issues/4)) added `cli` beside
it under the
[CLI Application contract](docs/cli-application-archetype.md), the second,
optionless package-bound shape, equally additive and equally untouched by
`template/` or `copier.yml`. FT-08.05's
[composition architecture review](docs/composition-architecture-review.md)
keeps deliberate archetype-owned duplication while removing layout,
classifier, coverage, and pre-commit leakage from Foundation; coordinated
client lock finalisation shipped in `create-forge 0.2.1`, completing Stage 08.
Stage 14 extends that review across Data Science, Jupyter, and Scientific
Python without changing production content or public contracts.
A future cutover that actually
retires `template/` in favour of this catalogue is the `_migrations` moment:
plan it before moving template paths and keep Library paths stable where
possible.

[#6](https://github.com/Sandsy09/forge-template/issues/6), done — a
`markdownlint-cli2` hook now covers root `*.md` and `docs/**` in
`.pre-commit-config.yaml`, ruleset in `.markdownlint-cli2.jsonc`
(`docs/adr/` is exempt from line-length only, since records are immutable).

Also open, not yet scheduled:
[#1](https://github.com/Sandsy09/forge-template/issues/1) (reintroduce `make`,
see Deferred below).

## Known limitation, documented not fixed

Local edits at the **very end** of a templated file can be lost on update: both
sides append at EOF, there is no trailing context for the patch to anchor to,
and the incoming side wins. Mid-file edits merge correctly.

Mitigation is template design — keep a stable section (License, etc.) at the
end of long templated files so user additions land above it. Noted in the
generated `CONTRIBUTING.md`.

## Deferred, with reasons

Full rationale for each of these lives in `docs/adr/`; this section stays as a
quick-reference summary rather than restating it.

- **python-semantic-release** — heavy, fights git-cliff over changelog
  ownership, and a stray `feat!:` can trigger an unintended major. See
  [docs/adr/0005](docs/adr/0005-git-cliff-for-changelogs.md).
- **Zensical instead of MkDocs** — MkDocs 2.0 removes the plugin system and
  breaks mkdocstrings; Material is in maintenance mode. Zensical is the
  successor but sits at 0.0.x with preliminary mkdocstrings support. Both
  Renovate and Dependabot configs pin below the breaking versions. Revisit when
  Zensical reaches 1.0 with mkdocstrings parity. See
  [docs/adr/0007](docs/adr/0007-mkdocs-pinned-below-2.md).
- **`make` as a `task_runner` choice** — removed entirely (see Current state).
  It was the widest-blast-radius conditional, `make` is absent on Windows by
  default (the author's own dev platform, so it could never be dogfooded), and
  nothing in the validation suite ever actually invoked `make` — combo 4 set
  `task_runner=make` and then ran `uv run poe typecheck` directly. The result
  shipped as a byte-empty `Makefile` with an unrunnable `make check` in
  `_message_after_copy`. Reintroduce only as a fully CI-tested option (a real
  Makefile mirroring every Poe task, plus a workflow job that runs `make check`
  on Linux) — tracked as [#1](https://github.com/Sandsy09/forge-template/issues/1),
  not scheduled yet. See
  [docs/adr/0008](docs/adr/0008-remove-make-task-runner.md).
