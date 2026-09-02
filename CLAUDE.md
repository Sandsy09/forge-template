# CLAUDE.md — forge-template

Guidance for Claude Code working in this repository.

## What this is

A [Copier](https://copier.readthedocs.io/) template and public composition
engine that scaffold modern Python projects. The engine catalogue contains
independent **library** and **CLI Application** archetypes; the direct-Copier
compatibility path remains Library-only.

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
from the top-level package, at package version `0.3.2`. ADR 0037's Stage 08
review corrects Foundation ownership and generated quality/lock behavior
without changing the `0.3.x` public facade. The
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
Forge extension rendering before a result is returned. **The production
catalogue now holds two independent reference archetypes**: FT-08.02
populated it with `library`
([contract](docs/library-archetype.md)/[ADR 0033](docs/adr/0033-migrate-library-production-catalogue.md)),
and FT-08.04 added `cli`
([contract](docs/cli-application-archetype.md)/[ADR 0035](docs/adr/0035-implement-cli-application-archetype.md)),
both alongside the implicit Foundation source at `src/forge_template/foundation/`
— proven by `uv run poe archetype` building real wheels/sdists for Library
across all three packaging modes and for CLI's fixed packaging mode, plus a
real installed console script and `python -m` invocation. `discover_components()`
now returns `("cli", "library")`. Neither archetype inherits from or reads
resources from the other; a ProjectSpec selects exactly one. These
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

Working: Library and CLI Application archetypes, all four combos green
locally and in CI, update merge validated, root and template
`.gitattributes` both in place, no byte-empty template files remain,
`task_runner`/`make` removed (it was the one untested, 100%-broken
conditional — see Deferred). **`v0.3.2` is the latest tagged release**,
carrying the reviewed Stage 08 boundary corrections. `v0.3.0` first carried
the production
engine catalogue (both `library` and `cli`) alongside the direct-Copier
template. Root repo hygiene is done:
root
`pyproject.toml`, `.pre-commit-config.yaml`, and real content for `LICENSE`,
`README.md`, `CONTRIBUTING.md`, `SECURITY.md` all exist; `src/forge_template`
holds checks for `copier.yml` itself (layout, computed-value defaults, the
`versioning`/`versioning_resolved` indirection), exercised by `tests/` and run
via `uv run poe check`, which the `lint` CI job now calls directly.
`docs/adr/` holds contiguous ADRs through 0044 recording the rationale behind
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
