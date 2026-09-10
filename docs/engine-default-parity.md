# Engine-default parity and responsibility inventory

This is the responsibility matrix required by
[FT-15.01](https://github.com/Sandsy09/forge-template/issues/146), the first
child of the
[Engine-Default Cutover](roadmap-v3/README.md) roadmap
([FT-EPIC-15](https://github.com/Sandsy09/forge-template/issues/141)). It
accounts for every behaviour the released default generation path — direct
Copier over `copier.yml` and `template/` — provides today, and assigns each
one to the **provider** (`forge-template`), the **client** (`create-forge`),
or a maintainer-approved **exclusion**.

The cutover makes the composition engine the default generator. It cannot be
planned until the gap between the two paths is written down. Direct Copier
emits up to 30 files from 23 questions; the engine's implicit Foundation
source plus its catalogue components emit 13 files for the direct-Copier
compatibility (`library`) shape, from a `ProjectSpec` plus the `library`
component's two packaging options.

This document decides no runtime behaviour. It introduces no protocol
increment, no new component, no `copier.yml` change, and no package version
bump. The four Stage 15 decision children own the design calls the matrix
surfaces:
[FT-15.02](https://github.com/Sandsy09/forge-template/issues/147) (provenance
and reproducible-update inputs),
[FT-15.03](https://github.com/Sandsy09/forge-template/issues/148) (platform
and generated-tooling assignment plus extension points), and
[FT-15.04](https://github.com/Sandsy09/forge-template/issues/149)
(compatibility, failure and release gates, and Stage 17 scope
reconciliation). [ADR 0058](adr/0058-inventory-default-copier-parity.md)
records the decisions this inventory itself makes.

## Scope and method

Every row was enumerated from source, not from roadmap history: the top-level
question keys in `copier.yml`, every path under `template/`, and the
`copier.yml` generation mechanics (`_tasks`, `_message_after_copy`,
`_message_after_update`, `_skip_if_exists`, `_answers_file`, `_exclude`,
`_min_copier_version`). A completed roadmap stage is not parity evidence: the
engine catalogue was built additively alongside `template/` and has never
been proven to reproduce the full default scaffold.

The comparison point for "shipped" is a real `render_project()` call for the
`library` archetype — the documented direct-Copier compatibility shape
(`docs/library-archetype.md`). `cli` and `data-science` add their own files
but do not close any Copier-parity gap the `library` render leaves open.

## How to read a row

| Column | Meaning |
| --- | --- |
| **Engine status** | `shipped` — a real engine render already produces this. `gap` — it does not. |
| **Disposition** | `provider`, `client`, or `excluded` (a maintainer-approved decision never to rebuild the behaviour). |
| **Tier** | For a `gap`: `cutover-blocking` (a generated repository is incomplete or unsafe without it) or `deferred` (rebuilt as an optional concern after the engine becomes the default). `n/a` otherwise. |
| **Implementation owner** | A filed issue that will deliver or has delivered the behaviour, or `needs a bounded issue` where no filed child fits and FT-15.04 must split one. |
| **Validation requirement** | The observable check that proves the row, once delivered. |

The disposition follows the routing table in
[foundation-scope.md](foundation-scope.md#routing-non-foundation-concerns):
primary project shape → archetype; optional cross-shape concern → capability;
adaptation to an external host → platform. That table's "Current Library
scaffold mapping" is the conceptual ancestor of this matrix.

## Answer inputs

The 23 `copier.yml` questions. A `shipped` input reaches the engine through a
`ProjectSpec` field or a component option; a `gap` input has no engine route.

| Behaviour | Copier source | Engine status | Disposition | Tier | Implementation owner | Validation requirement |
| --- | --- | --- | --- | --- | --- | --- |
| `project_name` | Project identity | shipped | provider | n/a | Foundation (`ProjectSpec.project.name`) | `tests/test_project_spec.py`; rendered `README.md` / `pyproject.toml` |
| `package_name` | Import name, `src/` dir | shipped | provider | n/a | archetype (`ProjectSpec.project.package_name`) | `tests/test_composition_architecture_review.py` render targets |
| `repo_name` | Distribution name, clone URLs | shipped | provider | n/a | Foundation (`ProjectSpec.project.repository_name`) | rendered `pyproject.toml` `[project].name` |
| `project_description` | Metadata, README | shipped | provider | n/a | Foundation (`ProjectSpec.project.description`) | rendered `README.md` / `pyproject.toml` |
| `github_org` | `repo_url`, CODEOWNERS, MkDocs `repo_name` | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | the `github` platform's required `organisation` option; `tests/test_github_platform.py` |
| `repo_url` | README install, `[project.urls]`, CONTRIBUTING, SECURITY links | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | derived `https://github.com/<organisation>/<repository_name>` in `github` templates and contributed into `pyproject-project-urls` / `readme-project-shape` / `contributing-project-shape` / `security-project-shape`; `tests/test_github_platform.py` |
| `author_name` | `[project].authors`, LICENSE holder | shipped | provider | n/a | Foundation (`ProjectSpec.project.authors[].name`) | rendered `pyproject.toml` / `LICENSE` |
| `author_email` | `[project].authors`, SECURITY contact | shipped | provider | n/a | Foundation (`ProjectSpec.project.authors[].email`) | rendered `pyproject.toml` / `SECURITY.md` |
| `codeowners_team` | `.github/CODEOWNERS` entry | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | derived `@<organisation>/<repository_name>-maintainers` in the `github` `CODEOWNERS` template (a recorded narrowing: not overridable); `tests/test_github_platform.py` |
| `license` | `[project].license`, `LICENSE`, private-upload classifier | shipped | provider | n/a | Foundation (`ProjectSpec.project.licence`); the `proprietary` `Private :: Do Not Upload` classifier is archetype-owned | `tests/test_composition_architecture_review.py`; the choice vocabulary is a client concern |
| `python_all` | Version-window bounds | shipped | provider | n/a | engine (`project_spec.SUPPORTED_PYTHON_MINORS`) | `tests/test_project_spec.py` |
| `python_version` | `.python-version`, dev floor | shipped | provider | n/a | Foundation (`ProjectSpec.python.development`) | rendered `.python-version` |
| `python_min_version` | `requires-python`, CI matrix floor | shipped | provider | n/a | Foundation (`ProjectSpec.python.minimum`) | rendered `pyproject.toml` `requires-python` |
| `python_matrix` | CI test matrix | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | the `github` CI `test` job matrix is the JSON-encoded `python.tested_versions`; `tests/test_github_platform.py` |
| `build_backend` | `[build-system]`, tool config | shipped | provider | n/a | `library` option `packaging_mode` | `tests/test_library_archetype.py`; `map_legacy_library_answers` |
| `versioning` | Static vs `hatch-vcs` version | shipped | provider | n/a | folded into `library` `packaging_mode` | `map_legacy_library_answers` |
| `versioning_resolved` | Collapsed effective constraint | shipped | provider | n/a | folded into `library` `packaging_mode` (invalid pairs unrepresentable) | `map_legacy_library_answers` rejects `("uv_build", "vcs")` |
| `initial_version` | Static version literal | shipped | provider | n/a | `library` option `initial_version` | `tests/test_library_archetype.py` |
| `type_checking` | CI gate, `[tool.mypy]` / `[tool.pyright]`, `typecheck` task | gap | provider | deferred | FT-15.03 → FT-17.03 | FT-15.03 decides: a type-checker capability, or an accepted mypy-only narrowing (Foundation is mypy-only today, `tests/test_composition_architecture_review.py`) |
| `coverage_fail_under` | `[tool.coverage]` gate, `--cov` addopts | gap | provider | deferred | FT-15.03 → FT-17.03 | Foundation deliberately excludes coverage (ADR 0037); a coverage capability owns the gate. `tests/test_composition_architecture_review.py` pins the current exclusion |
| `dependency_updates` | `renovate.json` / `.github/dependabot.yml` | gap | provider | cutover-blocking | FT-15.03 → FT-17.03 | the `dependabot` / `renovate` capability pair contributes the selected config (FT-15.03 / ADR 0060) |
| `use_docs` | MkDocs site, `docs/` tree, CI docs job, `docs` dependency group, Documentation URL | gap | provider | deferred | FT-15.03 → FT-17.03 | the `documentation` capability (FT-15.03 / ADR 0060); FT-17.03 delivers the site, tree, job, group and URL |
| `changelog_tool` | `CHANGELOG.md`, git-cliff config, `changelog` task | gap | provider | deferred | FT-15.03 → FT-17.03 | a changelog capability contributes the file, config and task |

## Generated files

The 30 paths under `template/`. Conditional filenames are keyed by their
rendered base path (`template/mkdocs.yml`,
`template/.github/dependabot.yml`).

### Shipped through Foundation and the archetype

| Behaviour | Copier source | Engine status | Disposition | Tier | Implementation owner | Validation requirement |
| --- | --- | --- | --- | --- | --- | --- |
| `template/.editorconfig` | Editor-neutral text conventions | shipped | provider | n/a | Foundation | `tests/test_extension_points.py` |
| `template/.gitattributes` | LF normalisation (invariant 5) | shipped | provider | n/a | Foundation | `tests/test_foundation_source.py`; rendered output |
| `template/.gitignore` | Base hygiene and secret-ignore rules | shipped | provider | n/a | Foundation + `gitignore-project-shape` extension | `tests/test_extension_points.py` |
| `template/.python-version` | Pinned dev interpreter | shipped | provider | n/a | Foundation | rendered `.python-version` |
| `template/CONTRIBUTING.md` | Neutral contribution starter | shipped | provider | n/a | Foundation | `tests/test_composition_architecture_review.py` |
| `template/LICENSE` | Selected licence text | shipped | provider | n/a | Foundation; `license-files` key in `pyproject.toml` is a gap within a shipped file (below) | rendered `LICENSE` |
| `template/README.md` | Root README starter | shipped | provider | n/a | Foundation + `readme-project-shape` extension | `tests/test_composition_architecture_review.py` |
| `template/SECURITY.md` | Security-reporting starter | shipped | provider | n/a | Foundation | `tests/test_composition_architecture_review.py` |
| `template/pyproject.toml` | Packaging, tooling, tasks | shipped | provider | n/a | Foundation + archetype via 11 extension points; see gaps within shipped files | `tests/test_extension_points.py` |
| `template/src/{{package_name}}/__init__.py` | Package init, `__version__` | shipped | provider | n/a | archetype | `tests/test_composition_architecture_review.py` |
| `template/src/{{package_name}}/py.typed` | Typed-package marker | shipped | provider | n/a | archetype | `tests/test_composition_architecture_review.py` |
| `template/tests/__init__.py` | Test package marker | shipped | provider | n/a | archetype | `tests/test_composition_architecture_review.py` |
| `template/tests/test_smoke.py` | Import/version smoke test | shipped | provider | n/a | archetype (`library`, `data-science`; `cli` emits `tests/test_cli.py`) | `tests/test_composition_architecture_review.py` |

### Gaps — cutover-blocking

| Behaviour | Copier source | Engine status | Disposition | Tier | Implementation owner | Validation requirement |
| --- | --- | --- | --- | --- | --- | --- |
| `template/.copier-answers.yml` | Update/regeneration provenance state | gap | provider | cutover-blocking | FT-15.02 → FT-17.01 | engine emits equivalent versioned generation metadata; secret-free; sufficient to reproduce an earlier render |
| `template/.github/workflows/ci.yml` | Lint, type-check, test matrix, build jobs | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | `github` owns `content/.github/workflows/ci.yml.jinja` (four `poe`-task jobs; pinned actions per `docs/github-action-pinning.md`); `tests/test_github_platform.py` |
| `template/.github/CODEOWNERS` | Review routing | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | `github` owns `content/.github/CODEOWNERS.jinja`; `tests/test_github_platform.py` |
| `template/.github/dependabot.yml` | Weekly `uv` + actions updates (when `dependency_updates == dependabot`) | gap | provider | cutover-blocking | FT-15.03 → FT-17.03 | the `dependabot` capability renders the selected config |
| `template/renovate.json` | Renovate config (when `dependency_updates == renovate`) | gap | provider | cutover-blocking | FT-15.03 → FT-17.03 | the `renovate` capability renders the selected config |
| `template/.pre-commit-config.yaml` | Fast local hooks, `commit-msg` enforcement | gap | provider | cutover-blocking | FT-15.03 → FT-17.03 | a pre-commit capability contributes the config; Foundation stays hook-free (ADR 0037), client still owns hook installation |
| `template/.env.example` | Placeholder-only environment template | gap | provider | cutover-blocking | FT-15.03 → FT-17.03 | secret-handling capability contributes the file; `docs/secret-handling.md` enforces placeholder-only content |

### Gaps — deferred past the cutover gate

| Behaviour | Copier source | Engine status | Disposition | Tier | Implementation owner | Validation requirement |
| --- | --- | --- | --- | --- | --- | --- |
| `template/.github/ISSUE_TEMPLATE/bug_report.yml` | Bug report form | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | `github` owns `content/.github/ISSUE_TEMPLATE/bug_report.yml.jinja`; `tests/test_github_platform.py` |
| `template/.github/ISSUE_TEMPLATE/config.yml` | Issue chooser config | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | `github` owns `content/.github/ISSUE_TEMPLATE/config.yml`; `tests/test_github_platform.py` |
| `template/.github/ISSUE_TEMPLATE/feature_request.yml` | Feature request form | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | `github` owns `content/.github/ISSUE_TEMPLATE/feature_request.yml`; `tests/test_github_platform.py` |
| `template/.github/pull_request_template.md` | PR checklist | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | `github` owns `content/.github/pull_request_template.md.jinja` (the "Docs updated" line is unconditional -- a recorded narrowing); `tests/test_github_platform.py` |
| `template/CHANGELOG.md` | Changelog seed | gap | provider | deferred | FT-15.03 → FT-17.03 | changelog capability contribution; `_skip_if_exists` behaviour reconciled by FT-15.02 |
| `template/docs/index.md` | MkDocs landing page | gap | provider | deferred | FT-15.03 → FT-17.03 | the `documentation` capability |
| `template/docs/reference.md` | mkdocstrings API page | gap | provider | deferred | FT-15.03 → FT-17.03 | the `documentation` capability, via the `api-reference` point |
| `template/docs/adr/0001-record-architecture-decisions.md` | Seed ADR | gap | provider | deferred | FT-15.03 → FT-17.03 | the `documentation` capability |
| `template/docs/adr/README.md` | ADR index | gap | provider | deferred | FT-15.03 → FT-17.03 | the `documentation` capability |
| `template/mkdocs.yml` | MkDocs site config | gap | provider | deferred | FT-15.03 → FT-17.03 | the `documentation` capability |

## Gaps within shipped files

`pyproject.toml` is produced by the engine, but the following fragments the
Copier template emits have no engine contributor yet. Each is assigned with
its owning question or file row above:

- `[tool.coverage.run]` / `[tool.coverage.report]` and the `--cov` /
  `--cov-report` pytest `addopts` — coverage capability (`coverage_fail_under`).
- `[tool.pyright]` and the chained `typecheck` task — type-checker capability
  (`type_checking`).
- `pre-commit>=4.0` in the `lint` dependency group — pre-commit capability
  (`.pre-commit-config.yaml`).
- the `docs` dependency group and the `mkdocs` / `docs:build` tasks —
  documentation capability (`use_docs`).
- `git-cliff>=2.7` in `dev` and the `[tool.git-cliff.*]` block — changelog
  capability (`changelog_tool`).
- `[project.urls]` (Repository / Issues / Documentation) — GitHub platform
  (`repo_url`).
- `license-files = ["LICENSE"]` — Foundation; a small addition to the
  Foundation `pyproject.toml` contribution, in FT-17.03.

## Copier generation mechanics

| Behaviour | Copier source | Engine status | Disposition | Tier | Implementation owner | Validation requirement |
| --- | --- | --- | --- | --- | --- | --- |
| `_tasks` | `git init` / `add` / `commit`, `uv sync`, lockfile commit, `pre-commit install` | n/a | client | n/a | CF-16.02 | client staging, lock resolution, VCS and hook execution; the engine spawns no process (FT-ROADMAP-01-EX-01) |
| `_message_after_copy` | Post-generation next-steps text | n/a | client | n/a | CF-16.01 | client UX and error presentation |
| `_message_after_update` | Post-update next-steps text | n/a | client | n/a | CF-16.02 | client update dispatch and messaging |
| `_skip_if_exists` | `CHANGELOG.md`, `.env` are never clobbered on regeneration | gap | provider | cutover-blocking | FT-15.02 → FT-17.04 | the engine metadata records which rendered targets are regeneration-safe; the client applies the skip |
| `_answers_file` | `.copier-answers.yml` name + `copier update` three-way merge | gap | provider | cutover-blocking | FT-15.02 → FT-17.04 | reproducible old/new render from recorded metadata; client owns the on-disk merge |
| `_exclude` | Files Copier never renders (`copier.yml`, `*.pyc`, `.git`) | n/a | client | n/a | CF-18.03 | client staging filter; the engine renders only declared component content |
| `_min_copier_version` | Minimum Copier runtime | excluded | excluded | n/a | engine protocol negotiation (`get_engine_info`) supersedes it | `tests/test_engine.py`; no Copier-runtime floor in the engine path |

## Cross-cutting behaviours

| Behaviour | Copier source | Engine status | Disposition | Tier | Implementation owner | Validation requirement |
| --- | --- | --- | --- | --- | --- | --- |
| `operating-systems` | Generated CI runs `ubuntu-latest` only; generation itself runs on any OS | shipped | provider | n/a | `github` platform (FT-17.02 / ADR 0063) | every `github` CI job is `runs-on: ubuntu-latest`; engine rendering stays OS-neutral, proven by `poe combos` / `poe archetype` on Windows; `tests/test_github_platform.py` |
| `packaging-modes` | `uv-build-static`, `hatchling-static`, `hatchling-vcs` | shipped | provider | n/a | `library` option `packaging_mode` (all three); `cli` / `data-science` fixed by design | `tests/test_library_build.py` builds all three modes |
| `conditional-filenames` | `{% if %}name{% endif %}` path collapsing skips optional files | excluded | excluded | n/a | engine uses explicit component selection and `output_target` | `tests/test_file_conflicts.py` |

## Known engine-preview gaps

The gaps above cluster into work the later Stage 15 children must resolve
before Stage 17 can implement:

- **Seven unrouted questions.** `github_org`, `repo_url`, `codeowners_team`,
  `python_matrix` (the CI consumer), `type_checking`, `coverage_fail_under`,
  `dependency_updates`, `use_docs` and `changelog_tool` have no `ProjectSpec`
  field or component option. FT-15.02 decides which belong in generation
  metadata versus a component option; FT-15.03 decides the platform and
  capability owners.
- **No GitHub platform component.** *(Closed by FT-17.02 / ADR 0063.)* At
  FT-15.01 the catalogue had three archetypes and two capabilities and
  `discover_components()` returned no platform. FT-15.03 defined the `github`
  platform and the Foundation extension points it needs; FT-17.02 shipped it,
  and the eleven `github`-owned rows above are now `shipped`.
- **No optional-tooling capabilities.** Pre-commit configuration, coverage
  gating, MkDocs documentation, changelog generation, secret scanning and
  dependency-update automation are all capability-shaped concerns with no
  filed implementation child scoped to build them. FT-15.03 assigns each an
  owner; FT-15.04 files the bounded issues the marked rows need and
  reconciles them against Stage 17's six children.
- **No engine-native update.** `copier update`'s three-way merge has no
  engine equivalent. FT-15.02 specifies the reproducible old/new render
  inputs in [generation-provenance.md](generation-provenance.md); FT-17.04
  implements the reproducible rendering; the client owns the filesystem merge.

## Explicit exclusions

Per **FT-ROADMAP-01-EX-01**, the following are permanently `create-forge`
concerns and never provider ones. The provider renders component content in
memory and negotiates protocol compatibility; it never touches a filesystem,
spawns a process, initialises or commits to Git, installs or runs a hook, or
presents an error to a person:

- CLI flags, subcommands and their parsing;
- interactive prompts and the `--yes` / non-interactive contract;
- user identity, saved preferences and profile selection;
- Git initialisation, the initial commit and lockfile commit;
- pre-commit hook installation and execution;
- destination staging, filesystem application, conflict resolution on disk
  and cleanup on failure.

Nothing in this inventory moves any of these toward the provider.

## What this inventory does not decide

Reserved for the later Stage 15 children and their ADRs:

- the generation-metadata schema and version-negotiation rules are now fixed
  by [generation-provenance.md](generation-provenance.md) (FT-15.02); its
  persisted filename stays a client decision, and which unrouted questions
  become metadata versus a component option is FT-15.03's;
- the merge, conflict and recovery policy for engine-native updates is
  client-side (CF-16.02); FT-15.02 fixed only the reproducible render inputs
  it consumes;
- the concrete GitHub platform descriptor, its options and its Foundation
  extension points (FT-15.03);
- whether `type_checking` becomes a capability or an accepted mypy-only
  narrowing (FT-15.03);
- the MkDocs / Streamlit / documentation layout (FT-15.03, and the Streamlit
  roadmap);
- which protocol or package compatibility lines move, and the
  migration/rollback expectations (FT-15.04);
- the bounded issues the `needs a bounded issue` rows require, and how they
  reconcile with Stage 17's filed children (FT-15.04).

FT-15.03 settled the platform, `type_checking` and documentation items above:
[platform-and-tooling-parity.md](platform-and-tooling-parity.md)
([ADR 0060](adr/0060-platform-composition-and-generated-tooling.md)) assigns
every provider-owned `gap` row here to one `github` platform or one of eight
capabilities and reserves the Foundation extension points they need.

FT-15.04 then settled the two items it owned:
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md)
([ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md))
classifies the cutover as `forge-template` `0.5.0` with component-manifest
protocol `3` and a published `metadata_version`, every other axis and the
public facade unchanged, and closes the `needs a bounded issue` rows **by
reference to FT-17.03** — no new issue is filed. Those nine owner cells now
read `FT-15.03 → FT-17.03`; their `status`, `disposition` and `tier` are
untouched, so those capability-owned surfaces stay `gap` until FT-17.03 ships
them. FT-17.02 / ADR 0063 flipped the eleven `github`-owned rows to `shipped`;
`tests/test_parity_inventory.py` pins every `shipped` file row against a real
`library` (and, for the `github` rows, `library` + `github`) render.

## Validation

`tests/test_parity_inventory.py` derives the expected row set from
`copier.yml` and `template/**` and fails `uv run poe check` if a question or
templated file has no row. It also checks that every row carries a valid
disposition, tier and validation requirement, that every filed issue a row
cites is real (cross-checked against
`docs/roadmap-v3/github-issues/filing-manifest.json` and the Streamlit pack's
manifest — no invented numbers), and that each `shipped` file row matches
what a real `render_project()` call produces — a `library` render, unioned
with a `library` + `github` render for the `github`-owned rows.
