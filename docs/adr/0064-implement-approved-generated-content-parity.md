# 64. Implement approved generated-content parity

Date: 2026-09-10

## Status

Accepted

Implements the capability half of the assignment accepted in
[ADR 0060](0060-platform-composition-and-generated-tooling.md) (platform
composition and generated-tooling parity) and pinned by
[platform-and-tooling-parity.md](../platform-and-tooling-parity.md). It does not
supersede ADR 0060; it ships the eight tooling capabilities, the two
`[dependency-groups]` Foundation extension points, and `api-reference` that
decision reserved. Third implementation issue of
[FT-EPIC-17](https://github.com/Sandsy09/forge-template/issues/142), after
[ADR 0062](0062-generation-metadata-and-manifest-protocol-3.md) (FT-17.01) and
[ADR 0063](0063-implement-the-github-platform.md) (FT-17.02).

## Context

[FT-17.03](https://github.com/Sandsy09/forge-template/issues/152) is the third
implementation issue of Stage 17. FT-17.02 gave a generated project a CI
workflow, `CODEOWNERS`, and issue/pull-request templates through the first
`kind = "platform"` component, but the direct-Copier scaffold still had no
engine owner for its pre-commit configuration, coverage gate, type-checker
choice, changelog, MkDocs site, `.env.example`, or dependency-update
automation. Fourteen provider-owned rows in
[engine-default-parity.md](../engine-default-parity.md) were still `gap`, and
five `copier.yml` questions (`type_checking`, `coverage_fail_under`,
`dependency_updates`, `use_docs`, `changelog_tool`) had no engine route.

ADR 0060 fixed the shape: eight capability components, one required
`organisation`-style option only where a value cannot be derived, the two
`[dependency-groups]` Foundation points so `documentation` can declare a real
`docs` group, and `api-reference` on `documentation`'s own content. It left
four calls to this issue, each confirmed with the maintainer before planning.

## Decision

Ship the eight capabilities and publish the reserved extension points. Record
the four confirmed calls here.

1. **`[tool.coverage]` and `[tool.pyright]` relocate to standalone files.**
   `coverage` owns `.coveragerc`; `pyright` owns `pyrightconfig.json`. Both are
   first-class tool-supported configuration locations. The gate value and the
   checking mode are preserved; only the file changes — a recorded,
   semantics-preserving relocation, the same class as ADR 0049's multi-line
   `check` array. Rejected: publishing a new `pyproject` tool-configuration
   extension point (a Foundation change beyond the two `[dependency-groups]`
   points ADR 0060 approved, for no parity benefit).

2. **`pyright` reaches CI through a dedicated `ci-jobs` job.** The `pyright`
   capability contributes a `type-check (pyright)` job through the `ci-jobs`
   point `github` already publishes, plus a local `typecheck:pyright` poe task
   and an aggregate-`check` entry. Foundation's `typecheck = "mypy ."` task and
   `github`'s own content are untouched (`github` stays `1.0.0`). This is a
   recorded narrowing against ADR 0006's single chained `typecheck` task: the
   task and pytest `addopts` are additive-only, not rewritable, so a chained
   task is not expressible — the CI gate coverage is equivalent. Copier's
   mypy-*less* `pyright` answer stays unreachable, as ADR 0060 already recorded.

3. **The archetypes are left untouched.** `library` / `cli` / `data-science`
   keep their content and versions (`1.0.1` / `1.0.1` / `1.0.0`). They do not
   fill `ci-jobs` — the Copier scaffold has no publish job, so there is no
   parity gap — and do not fill `api-reference`. `ci-jobs` is filled only by
   capabilities (`documentation`'s docs-build job, `pyright`'s type-check job);
   `documentation` self-fills its own `api-reference` page with
   `::: {{ project.package_name }}`, leaving the marker published for a later
   archetype fill. `library-archetype.md`'s forward reference is softened to a
   later child. Rejected: `library` filling `ci-jobs` with a PyPI
   trusted-publishing job and moving to `1.1.0` (adds generated CI behaviour
   beyond direct-Copier parity, and moves the regression digests).

4. **`documentation` requires `library`.** The manifest declares
   `requires = [{ id = "library", version = ">=1,<2" }]`, verbatim as
   `platform-and-tooling-parity.md` and the reference fixture state it.
   Selecting `documentation` with `cli` or `data-science` rejects before render
   as `invalid-component-selection` / `validate`. A docs site for the other
   archetypes is a separate future decision.

### What ships

| Component | `manifest_version` | Owns | Notable |
| --- | --- | --- | --- |
| `coverage` | 2 | `.coveragerc` | `fail_under` integer option; `coverage` task + check entry; `ci-steps` upload step |
| `pre-commit` | 2 | `.pre-commit-config.yaml` | contributes `pre-commit` to the dev group |
| `pyright` | 2 | `pyrightconfig.json` | `typecheck:pyright` task + check entry + `ci-jobs` job |
| `changelog` | **3** | `CHANGELOG.md`, `cliff.toml` | first shipped protocol-3 component: `[[regeneration]]` marks `CHANGELOG.md` `skip-if-exists` |
| `documentation` | 2 | `mkdocs.yml`, `docs/index.md`, `docs/reference.md`, two seed ADR files | `site_name` string option; publishes `api-reference`; `requires` `library`; uses the two `[dependency-groups]` points; `ci-jobs` docs job |
| `dotenv-example` | 2 | `.env.example` | placeholder-only per [secret-handling.md](../secret-handling.md) |
| `dependabot` | 2 | `.github/dependabot.yml` | `requires` `github`; `conflicts` `renovate` |
| `renovate` | 2 | `renovate.json` | `conflicts` `dependabot` |

`foundation.toml` gains `pyproject-named-dependency-groups` and
`pyproject-dependency-group-includes` (inventory 14 → 16), placed
**byte-neutral** on `content/pyproject.toml.jinja` so a render that fills
neither is byte-identical to before. The one deliberate, non-byte-neutral
Foundation change is `license-files = ["LICENSE"]` on the `pyproject.toml`
contribution — the "small addition … in FT-17.03" the parity contract assigned
here. It moves the `tests/fixtures/archetype_regression/digests.json` and
`tests/fixtures/generation_metadata/example-library.json` pins by one
`pyproject.toml` digest each; the diff was reviewed and is exactly that one
line.

`discover_components()` returns fourteen components. The `dependabot` /
`renovate` mutual `conflicts` is the first production use of a `conflicts`
edge; `dependabot → github` and `documentation → library` are the first
production cross-tier and same-adjacent `requires` edges. Every invalid
selection rejects with `operation` in `{parse, validate}` from both
`plan_generation` and `render_project`, never `render`.

### Recorded narrowings

- Copier's mypy-less `pyright` type-checking answer is unreachable (Foundation's
  mypy gate cannot be switched off).
- `pyright`'s CI check is a separate `ci-jobs` job and a `typecheck:pyright`
  task, not a step chained inside Foundation's `typecheck` task.
- Selecting `coverage` makes `poe check` run the suite twice (Foundation's
  plain `test` plus the `coverage` task), because Foundation's `test` task and
  pytest `addopts` are not extension points; the `fail_under` gate is a CI
  concern (the `copier.yml` help text says "in CI") enforced through the
  `coverage` task and the `ci-steps` upload.
- The generated `.github/dependabot.yml` / `renovate.json` drop the
  `use_docs`-conditional MkDocs version pins; a `documentation`-selected
  project pins them itself if needed.

## Consequences

- `discover_components()` → fourteen: three archetypes, ten capabilities, one
  platform. `tests/test_platform_composition.py`'s FT-ROADMAP-01-EX-03 tripwire
  is turned over to "ten capabilities"; its reserved-point tripwire is turned
  over — every point ADR 0060 reserved is now published.
- The fourteen provider-owned `gap` rows in
  [engine-default-parity.md](../engine-default-parity.md) flip to `shipped`,
  along with `license-files`. Every `copier.yml` question now has an engine
  route; `tests/test_parity_inventory.py`'s `gap_questions` set is empty.
- Component-manifest protocol `3` gains its first shipped user (`changelog`);
  protocol-`1` and protocol-`2` manifests are still accepted unchanged.
- Extension-point-inventory axis: Foundation 14 → 16, `api-reference` published
  on `documentation`. A backward-compatible addition under
  [compatibility-policy.md](../compatibility-policy.md); the package-version
  bump that document mandates for an observable Foundation change is FT-17.06's
  `0.5.0`.
- The catalogue content size re-baselines from 72 files / 48,350 bytes to 112
  files / 68,378 bytes;
  [composition-architecture-review.md](../composition-architecture-review.md)
  and [cross-repository-validation.md](../cross-repository-validation.md) move
  with the pin. The built wheel stays well under its ceiling.
- `library` / `cli` / `data-science` content and versions are unchanged; no
  `copier.yml` or `template/**` change; `main` stays `0.4.1` and untagged.
- New per-capability test modules
  (`tests/test_coverage_capability.py`, `tests/test_pre_commit_capability.py`,
  `tests/test_pyright_capability.py`, `tests/test_changelog_capability.py`,
  `tests/test_documentation_capability.py`,
  `tests/test_dotenv_example_capability.py`,
  `tests/test_dependency_updates_capabilities.py`); `scripts/check_wheel.py`,
  the discovery-literal test set, and the living documentation are updated.
- No public facade name, `EngineErrorCode`, `ProjectSpec` protocol integer,
  Copier answer, or release changes.
