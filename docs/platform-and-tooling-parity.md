# Platform composition and generated-tooling parity

This is the provider-owned assignment required by
[FT-15.03](https://github.com/Sandsy09/forge-template/issues/148), the third
child of the [Engine-Default Cutover](roadmap-v3/README.md) roadmap
([FT-EPIC-15](https://github.com/Sandsy09/forge-template/issues/141)). It takes
every optional-tooling and host-integration concern that
[engine-default-parity.md](engine-default-parity.md) tiered `cutover-blocking`
or `deferred` and left for this issue, and assigns each to a catalogue
component — one `github` platform or one of eight capabilities — together with
the Foundation extension points those components need.

Its review obligations are **FT-ROADMAP-01-AC-03** (platform selection and
composition stay manifest- and catalogue-owned, exposed only through public
path-free descriptors — shared with
[FT-17.02](https://github.com/Sandsy09/forge-template/issues/151)) and
**FT-ROADMAP-01-EX-03** (no Streamlit or other new archetype).
[ADR 0060](adr/0060-platform-composition-and-generated-tooling.md) records the
decisions.

This document decided no runtime behaviour, and added no component, no
`EngineErrorCode` value, no public name, no protocol increment, and no
`copier.yml` change. Its extension points were **reserved**;
[FT-17.02](https://github.com/Sandsy09/forge-template/issues/151) /
[ADR 0063](adr/0063-implement-the-github-platform.md) then shipped the `github`
platform (`1.0.0`) and published five of them — `pyproject-project-urls`,
`contributing-project-shape`, `security-project-shape`, `ci-jobs`, `ci-steps`
(Foundation inventory 11 → 14) — and
[FT-17.03](https://github.com/Sandsy09/forge-template/issues/152) /
[ADR 0064](adr/0064-implement-approved-generated-content-parity.md) shipped the
eight capabilities and published the last three — `pyproject-named-dependency-groups`,
`pyproject-dependency-group-includes` (inventory 14 → 16) and `api-reference` on
`documentation`. `foundation_version` stays `1` throughout. Every assignment
below is now live.

## Why this exists

The engine's `ProjectSpec` accepts a `platforms` tuple, but at FT-15.03 time
`discover_components()` returned
`("cli", "data-science", "jupyter", "library", "scientific-python")` — three
archetypes, two capabilities, and no platform. So the direct-Copier scaffold's
CI workflow, CODEOWNERS, issue and pull-request templates, pre-commit
configuration, coverage gate, changelog, MkDocs site, `.env.example`, and
dependency-update automation had no owner in the engine path. Twenty-six
provider-owned `gap` rows in `engine-default-parity.md` point here (FT-17.02 /
ADR 0063 flipped eleven of them to `shipped`); until each
has an owner, [Stage 17](roadmap-v3/README.md) cannot implement and the cutover
cannot be scoped.

The routing is not re-decided here.
[foundation-scope.md](foundation-scope.md#routing-non-foundation-concerns)
already assigns *"GitHub Actions, issue and pull-request templates, CODEOWNERS,
and other GitHub-specific adapters"* to a **GitHub platform contribution**, and
*"coverage reporting, pre-commit feedback, documentation, changelog support,
dependency-update automation, configuration examples"* to **capabilities**.
This contract makes that concrete.

## Scope and boundary

The provider owns:

- one `github` platform component, its single option, and the two CI extension
  points it publishes;
- eight capability components and the tooling content each contributes;
- five new Foundation extension points that carry host-scoped links and one
  optional named dependency group;
- the required and conflicting selections that keep every invalid combination
  rejected before rendering.

The client owns, unchanged from **FT-ROADMAP-01-EX-01**: Git initialisation and
the initial commit, hook installation and execution, lock resolution, CLI
prompting and `--yes`, destination staging and filesystem application, and all
error presentation. The provider renders CI *content*, hook *configuration*,
documentation *content* and dependency-maintenance *content* in memory; it
never runs any of it.

Foundation stays framework-, host- and CI-neutral. Every host-specific value
reaches a Foundation-owned file only as a `github` platform contribution
through a reviewed extension point, never as a Foundation default.

## The `github` platform

One component, `kind = "platform"`, selected through `ProjectSpec.components.
platforms`. It adapts a generated project to GitHub and nothing else; a future
GitLab or Forgejo platform is a separate component, not an option on this one.

### The single option

`github` declares exactly one option, `organisation`, a required string. The
existing `github` reference fixture
(`tests/fixtures/component_manifests/github/options.schema.json`) already
declares precisely this. Everything else the Copier path asks as a separate
question is **derived inside the platform's own templates**:

| Copier question | Engine source |
| --- | --- |
| `github_org` | the `organisation` option, verbatim |
| `repo_url` | `https://github.com/<organisation>/<project.repository_name>` |
| `codeowners_team` | `@<organisation>/<project.repository_name>-maintainers` |

Option-schema protocol `2` makes `default` mutually exclusive with `required`
and cannot reference another field, so a "derived but overridable" option is
not expressible without a protocol increment this stage forbids. A free-text
`codeowners_team` override and a non-`github.com` `repo_url` are therefore
**recorded parity narrowings**: a project that needs a literal team handle or
an enterprise host URL edits the two generated files after handoff. FT-17.02
may add an optional override only with fresh maintainer approval and a stated
rule for reading an option that resolves to an omitted key.

### Files it owns

| Target | Tier | Copier source |
| --- | --- | --- |
| `.github/workflows/ci.yml` | cutover-blocking | lint / type-check / test-matrix / build / docs jobs |
| `.github/CODEOWNERS` | cutover-blocking | review routing |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | deferred | bug report form |
| `.github/ISSUE_TEMPLATE/config.yml` | deferred | issue chooser config |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | deferred | feature request form |
| `.github/pull_request_template.md` | deferred | PR checklist |

The CI workflow's test matrix is `PythonSelection.tested_versions` — the value
`engine-default-parity.md` records as already delivered, with only its CI
consumer missing. Generation itself stays OS-neutral (proven on Windows by
`poe combos` / `poe archetype`); the workflow reproduces the direct-Copier
scaffold's Linux-only job matrix, closing the `operating-systems` row. Remote
actions are pinned per
[github-action-pinning.md](github-action-pinning.md) — a full 40-character SHA
with the release tag in a same-line comment.

### Extension points it publishes

| Point | Granularity | A contribution supplies |
| --- | --- | --- |
| `ci-jobs` | a whole workflow job | a named job block, e.g. an archetype's build-and-publish job |
| `ci-steps` | a step inside an existing job | a step block, e.g. a coverage upload |

Both names already exist in the living documentation at these two
granularities: `library-archetype.md` names `ci-jobs`;
[file-conflicts.md](file-conflicts.md#resolving-contributions) and
[no-copy-inheritance.md](no-copy-inheritance.md) describe a `coverage`-style
capability contributing one *step* into `ci-steps`. Publishing both keeps every
existing document accurate.

### Foundation content it contributes into

| Foundation point | New? | What `github` contributes |
| --- | --- | --- |
| `pyproject-project-urls` | published FT-17.02 | `[project.urls]` Repository / Issues (a Documentation URL is the `documentation` capability's) |
| `contributing-project-shape` | published FT-17.02 | host-scoped links in `CONTRIBUTING.md` |
| `security-project-shape` | published FT-17.02 | the vulnerability-report URL in `SECURITY.md` |
| `readme-project-shape` | existing | clone and install URLs in `README.md` |

## Path-free descriptors and deterministic selection

Every selection and composition rule stays in the manifest and the catalogue,
per **FT-ROADMAP-01-AC-03**:

- the public `ComponentDescriptor` for `github` carries `id`, `name`,
  `description`, `kind`, `version`, `projectspec_protocols`, `requires_python`,
  `requires`, `conflicts`, and `options` — no filesystem path, exactly as
  `tests/test_capability_composition.py` already pins for every capability
  descriptor;
- a client selects `platforms=["github"]` and supplies
  `component_options.github.organisation`; it never names a file, a path, or a
  rendered value;
- [composition-order.md](composition-order.md) is unchanged: Foundation, then
  the archetype, then every capability, then every platform. The
  `dependabot → github` `requires` edge below is a cross-tier *selection*
  constraint and does not reorder the tiers — the platform still applies after
  every capability.

Multiple platforms remain valid whenever their extension-point contributions do
not collide ([file-conflicts.md](file-conflicts.md)); the catalogue ships one.

## The capability set

Eight capability components. Three IDs — `coverage`, `changelog`,
`documentation` — already exist in the reference fixture catalogue; the other
five are new. Each is independently selectable; the Forge default profile
selects none of them, keeping the engine's current output the floor.

| Capability | Owns | Uses / publishes | Options |
| --- | --- | --- | --- |
| `coverage` | `.coveragerc` | `pyproject-development-dependencies` (`pytest-cov`), `pyproject-task-definitions`, `pyproject-aggregate-check`, `ci-steps` | `fail_under` (integer) |
| `pre-commit` | `.pre-commit-config.yaml` | `pyproject-development-dependencies` (`pre-commit`) | none |
| `pyright` | `pyrightconfig.json` | `pyproject-development-dependencies` (`pyright`), `pyproject-task-definitions`, `pyproject-aggregate-check` | none |
| `changelog` | `CHANGELOG.md`, `cliff.toml` | `pyproject-development-dependencies` (`git-cliff`), `pyproject-task-definitions` | none |
| `documentation` | `mkdocs.yml`, `docs/index.md`, `docs/reference.md`, `docs/adr/0001-record-architecture-decisions.md`, `docs/adr/README.md` | publishes `api-reference`; uses `pyproject-named-dependency-groups`, `pyproject-dependency-group-includes`, `pyproject-task-definitions`, `readme-project-shape` | `site_name` (string) |
| `dotenv-example` | `.env.example` | `readme-project-shape` | none |
| `dependabot` | `.github/dependabot.yml` | — | none |
| `renovate` | `renovate.json` | — | none |

`coverage`'s `[tool.coverage.*]` configuration and the `--cov` pytest `addopts`
that the Copier scaffold places in `pyproject.toml`, and `pyright`'s
`[tool.pyright]` block, are **relocated to the tools' own standalone
configuration files** (`.coveragerc`, `pyrightconfig.json`) — both first-class
supported locations for those tools. The gate value and the checking mode are
preserved; only the file changes. This is a recorded, semantics-preserving
relocation, the same kind ADR 0049 made when the aggregate `check` array became
multi-line. Whether a later release instead publishes a `pyproject` tool-config
extension point is
[FT-17.03](https://github.com/Sandsy09/forge-template/issues/152)'s call, with
its own maintainer approval.

`changelog` owns `CHANGELOG.md` with the `skip-if-exists` regeneration
disposition [generation-provenance.md](generation-provenance.md) already
reserves for it: the flag travels with whoever owns the content.

## Required and conflicting selections

| Rule | Owner declares | Rejected when |
| --- | --- | --- |
| `dependabot` needs GitHub | `requires = [{ id = "github", version = ">=1,<2" }]` | `dependabot` selected without `github` |
| One updater at a time | `dependabot` and `renovate` each `conflicts` the other | both selected together |
| `documentation` needs a package to document | `requires = [{ id = "library", version = ">=1,<2" }]` (as the fixture already declares) | selected without `library` |

Every rejection is validation-first: `ForgeEngineError.operation` is `parse` or
`validate`, from both `plan_generation` and `render_project`, **never**
`render`. This is the first production use of a `conflicts` edge, and the
concrete instance of the cross-tier `requires` case
[composition-order.md](composition-order.md#cross-tier-dependencies) documents.
Selecting neither `dependabot` nor `renovate` reproduces Copier's
`dependency_updates == none`.

## Extension points: all published

### Published by FT-17.02 / ADR 0063

| Point | Owner | A contribution supplies |
| --- | --- | --- |
| `pyproject-project-urls` | Foundation `content/pyproject.toml.jinja` | `[project.urls]` entries |
| `contributing-project-shape` | Foundation `content/CONTRIBUTING.md.jinja` | host-scoped links |
| `security-project-shape` | Foundation `content/SECURITY.md.jinja` | the vulnerability-report URL |
| `ci-jobs` | `github` (own CI content) | a whole workflow job |
| `ci-steps` | `github` (own CI content) | a step inside the test job |

The first three reversed
[extension-points.md](extension-points.md#the-published-inventory)'s statement
that `CONTRIBUTING.md.jinja` and `SECURITY.md.jinja` are sole-owner content
with no extension point — additive, exactly as ADR 0049 grew the inventory from
eight points to eleven. `.editorconfig`, `.gitattributes`,
`.python-version.jinja` and `LICENSE.jinja` stay sole-owner. Each marker is
placed so a render that does not select `github` is byte-identical to before
(ADR 0063). `ci-jobs` and `ci-steps` are the first points a shipped component
publishes on its own content; the `documentation` and `pyright` capabilities
fill `ci-jobs` (a docs-build job and a pyright job) and `coverage` fills
`ci-steps` (a coverage upload).

### Published by FT-17.03 / ADR 0064

| Point | Owner file | A contribution supplies |
| --- | --- | --- |
| `pyproject-named-dependency-groups` | Foundation `content/pyproject.toml.jinja` | a `name = [ ... ]` group under `[dependency-groups]` |
| `pyproject-dependency-group-includes` | Foundation `content/pyproject.toml.jinja` | an `{ include-group = "name" }` line in the `dev` group |
| `api-reference` | `documentation` (own content) | an mkdocstrings API page |

The two Foundation points (inventory 14 → 16) **reverse ADR 0049's stated
limitation** that "a capability still cannot declare its own named dependency
group". They let `documentation` declare a real `docs` group that
`uv sync --group docs` resolves and that Foundation's `dev` group includes —
matching the Copier scaffold, whose `docs` group is both separately installable
and part of `dev`. Both markers are placed byte-neutral, so a render that does
not select `documentation` is byte-identical to before (ADR 0064).
`api-reference` is self-filled by `documentation` with `::: <package_name>`; the
marker stays published for a later archetype fill.

## Generated tooling versus client execution

Per **FT-ROADMAP-01-EX-01**, restated at each concrete row:

| Concern | Provider renders (in memory) | Client executes |
| --- | --- | --- |
| CI | `ci.yml` content, matrix, pinned action SHAs | nothing — GitHub runs it |
| Pre-commit | `.pre-commit-config.yaml` content | `pre-commit install`, hook runs, `commit-msg` enforcement |
| Documentation | `mkdocs.yml`, `docs/` pages, the `docs` group | `mkdocs build` / `mkdocs serve` |
| Changelog | `CHANGELOG.md` seed, `cliff.toml`, the `changelog` task | running git-cliff, tagging |
| Dependency updates | `dependabot.yml` / `renovate.json` content | nothing — the host service runs it |
| Coverage | `.coveragerc`, the `coverage` task, its `check` entry | running `pytest --cov` |

The engine spawns no process, initialises no repository, and installs no hook.

## Explicit exclusions

Per **FT-ROADMAP-01-EX-03** and this issue's own exclusion list:

- the archetype set stays exactly `cli`, `data-science`, `library`. This
  contract adds **no archetype**. A Streamlit archetype is
  [roadmap-v4](roadmap-v4/README.md) Stages 19–21 and begins only after the
  cutover contracts are accepted;
- Copier's mypy-less `pyright` type-checking answer is unreachable, because
  Foundation's mypy gate cannot be disabled — a recorded narrowing, not a
  rebuilt option;
- Copier's free-text `codeowners_team` override is a recorded narrowing;
- no arbitrary remote component registry, and no plugin execution during
  planning or rendering;
- no new shared Forge runtime dependency for generated projects — every
  capability's contributions are development-time only, and no generated
  project imports `forge_template`.

## Where the remaining unrouted questions land

[engine-default-parity.md](engine-default-parity.md) left open *"which unrouted
questions become metadata versus a component option"*, and
[generation-provenance.md](generation-provenance.md) deferred the same list to
this issue. The answer: **every one becomes a selection or a component option,
none becomes a generation-metadata field.**

| Question | Becomes |
| --- | --- |
| `github_org` | the `github` platform's `organisation` option |
| `repo_url`, `codeowners_team` | derived inside `github` templates |
| `python_matrix` | already delivered as `PythonSelection.tested_versions`; the `github` CI job consumes it |
| `type_checking` | selecting the `pyright` capability, or not |
| `coverage_fail_under` | the `coverage` capability's `fail_under` option |
| `dependency_updates` | selecting `dependabot`, `renovate`, or neither |
| `use_docs` | selecting the `documentation` capability, or not |
| `changelog_tool` | selecting the `changelog` capability, or not |

Generation metadata is unaffected: it already embeds the effective
`ProjectSpec` — `component_options` included — verbatim, so a selection or an
option is captured without adding a metadata field.

## Provider-owned parity rows and their owners

Every provider-owned `gap` row in
[engine-default-parity.md](engine-default-parity.md) that is not a
[FT-15.02](https://github.com/Sandsy09/forge-template/issues/147) provenance
row, and the component this contract assigns it to. `tests/
test_platform_composition.py` derives the left column from that document and
fails if a row is unassigned here.

| Parity row | Owner |
| --- | --- |
| `github_org` | `github` |
| `repo_url` | `github` |
| `codeowners_team` | `github` |
| `python_matrix` | `github` |
| `type_checking` | `pyright` |
| `coverage_fail_under` | `coverage` |
| `dependency_updates` | `dependabot` / `renovate` |
| `use_docs` | `documentation` |
| `changelog_tool` | `changelog` |
| `template/.github/workflows/ci.yml` | `github` |
| `template/.github/CODEOWNERS` | `github` |
| `template/.github/dependabot.yml` | `dependabot` |
| `template/renovate.json` | `renovate` |
| `template/.pre-commit-config.yaml` | `pre-commit` |
| `template/.env.example` | `dotenv-example` |
| `template/.github/ISSUE_TEMPLATE/bug_report.yml` | `github` |
| `template/.github/ISSUE_TEMPLATE/config.yml` | `github` |
| `template/.github/ISSUE_TEMPLATE/feature_request.yml` | `github` |
| `template/.github/pull_request_template.md` | `github` |
| `template/CHANGELOG.md` | `changelog` |
| `template/docs/index.md` | `documentation` |
| `template/docs/reference.md` | `documentation` |
| `template/docs/adr/0001-record-architecture-decisions.md` | `documentation` |
| `template/docs/adr/README.md` | `documentation` |
| `template/mkdocs.yml` | `documentation` |
| `operating-systems` | `github` |

## What this contract does not decide

Reserved for other owners:

- the concrete manifest bytes, content trees, component versions, option
  descriptions, and CI matrix shape — FT-17.02 (the `github` platform) and
  FT-17.03 (the eight capabilities);
- whether a `pyproject` tool-configuration extension point is published instead
  of relocating `[tool.coverage]` / `[tool.pyright]` to standalone files
  ([FT-17.03](https://github.com/Sandsy09/forge-template/issues/152));
- whether any protocol or package compatibility line must move, and the
  migration and rollback expectations
  ([FT-15.04](https://github.com/Sandsy09/forge-template/issues/149));
- whether the `needs a bounded issue` rows — now all resolving to
  `documentation` or the `dependabot` / `renovate` pair — can be closed by
  reference or still need filed issues
  ([FT-15.04](https://github.com/Sandsy09/forge-template/issues/149));
- the Streamlit archetype and its layout ([roadmap-v4](roadmap-v4/README.md)).

FT-15.04 settled its two items:
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md)
([ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md))
classifies the cutover as `forge-template` `0.5.0`, component-manifest
protocol `3` and a published `metadata_version`, with the five reserved
Foundation points and `ci-jobs` / `ci-steps` / `api-reference` an additive,
package-bumped change to the extension-point-inventory axis; and it closed the
`needs a bounded issue` rows **by reference to FT-17.03** — no new issue.
[FT-17.03](https://github.com/Sandsy09/forge-template/issues/152) /
[ADR 0064](adr/0064-implement-approved-generated-content-parity.md) then shipped
the eight capabilities and flipped every one of those rows to `shipped`.

## Validation

`tests/test_platform_composition.py` runs under `uv run poe check`. Following
FT-11.04's precedent, four synthetic components under
`tests/fixtures/platform_composition/` — `reference-host` (a platform),
`host-ci-extension`, `host-bound-updates`, and `host-free-updates` — overlay a
copy of the real production catalogue with the real Foundation source live.
They are deliberately not named for the decided catalogue. The tests prove:

- every provider-owned row in `engine-default-parity.md` (excluding the
  FT-15.02 provenance rows), whether a `gap` or flipped to `shipped` by FT-17.02
  or FT-17.03, appears in the ownership table above with an owner from the
  decided set — a row gaining no owner fails;
- every extension point this contract calls *existing* is really in the live
  `foundation.toml`;
- **tripwire turned over:** every point ADR 0060 reserved is now published —
  the three host-link points by FT-17.02 / ADR 0063 and the two
  `[dependency-groups]` points by FT-17.03 / ADR 0064 — and this file fails if
  any is walked back;
- **FT-ROADMAP-01-EX-03 tripwire:** `discover_components()` still returns
  exactly three archetypes — `cli`, `data-science`, `library` — plus ten
  capabilities and one platform (`github`), and no new archetype;
- the synthetic platform's public descriptor carries no filesystem path, and
  its option schema declares exactly one option;
- a capability's contribution into the synthetic platform's `ci-steps` resolves
  as a `PlannedExtension` on the platform-owned target, even though the
  capability tier applies first;
- the cross-tier `requires` edge and the `conflicts` edge each reject as a
  structured `ForgeEngineError` with `operation` in `{parse, validate}` from
  both planning and rendering;
- composition is deterministic across capability and platform input order, and
  the platform tier still applies after every capability.
