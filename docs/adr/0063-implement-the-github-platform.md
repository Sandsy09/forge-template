# 63. Implement the GitHub platform

Date: 2026-09-10

## Status

Accepted

Implements the assignment accepted in
[ADR 0060](0060-platform-composition-and-generated-tooling.md) (platform
composition and generated-tooling parity) and pinned by
[platform-and-tooling-parity.md](../platform-and-tooling-parity.md). It does not
supersede ADR 0060; it ships the `github` platform and the three Foundation
host-link points that decision reserved. Second implementation issue of
[FT-EPIC-17](https://github.com/Sandsy09/forge-template/issues/142), after
[ADR 0062](0062-generation-metadata-and-manifest-protocol-3.md).

## Context

[FT-17.02](https://github.com/Sandsy09/forge-template/issues/151) is the second
Stage 17 provider-implementation issue. The engine's `ProjectSpec` already
accepts a `platforms` tuple and every composition, descriptor, and discovery
path is wired for `kind = "platform"`, but `discover_components()` ships zero
platforms — so a generated project has no owner for its CI workflow,
`CODEOWNERS`, issue and pull-request templates, or any host-scoped link
(`repo_url`, `[project.urls]`, clone URLs, the vulnerability-report URL).
Twenty-six provider-owned `gap` rows in
[engine-default-parity.md](../engine-default-parity.md) wait on Stage 17;
eleven of them are the `github` platform's.

FT-15.03 / ADR 0060 fixed the design: one `github` platform, one required
`organisation` option, the two CI extension points it publishes, the files it
owns and their tiers, and the three new Foundation extension points that carry
host-scoped links. FT-15.04 /
[cutover-compatibility-and-acceptance.md](../cutover-compatibility-and-acceptance.md)
gave FT-17.02 two acceptance-matrix rows and held every axis but the three the
cutover moves. This ADR records the choices made turning ADR 0060's assignment
into shipped content.

The stage exclusions forbid package publication (FT-17.06 owns it), CLI flags
or client configuration, engine-owned Git or destination writes, any remote
component registry, and any new shared Forge runtime dependency for generated
projects. The public facade may grow only additively; the eight capabilities,
the two `[dependency-groups]` Foundation points, and `api-reference` are
[FT-17.03](https://github.com/Sandsy09/forge-template/issues/152)'s.

## Decision

Confirmed with the maintainer before this record.

1. **One `github` platform, and only the platform.** `dependabot` and
   `renovate` name `github` in their `requires` / `conflicts` edges, but they
   are two of FT-17.03's eight capabilities and are not shipped here. The
   `dependabot`→`github` requires edge and the `dependabot`⇔`renovate` conflict
   that [cutover-compatibility-and-acceptance.md](../cutover-compatibility-and-acceptance.md)
   lists "first required at FT-17.02" are proven now by the four synthetic
   fixtures under `tests/fixtures/platform_composition/`
   (`host-bound-updates` requires `reference-host` and conflicts
   `host-free-updates`) and re-proven against the real catalogue at FT-17.03.
   `github` itself declares no `requires` and no `conflicts`. Rejected: pulling
   `dependabot` / `renovate` forward (contradicts ADR 0060's consequence that
   "FT-17.03 inherits the eight-capability set" and leaves FT-17.03's issue
   body claiming all eight).

2. **`github` is `manifest_version = 2` and publishes `ci-jobs` / `ci-steps`
   on its own content.** It contributes into Foundation (needs the protocol-`2`
   `target.kind = "foundation"` shape) and is the first shipped component to
   declare `[[extension_points]]` on content it owns rather than only
   contributing into Foundation's. It declares no `[[renames]]` /
   `[[regeneration]]`, so protocol `3` is not needed. Both `ci-jobs` and
   `ci-steps` mark the one owned `ci.yml.jinja`; each appears exactly once and
   renders zero bytes unfilled. Rejected: a protocol-`3` manifest (nothing here
   needs a rename or a non-`replace` disposition); one CI point (ADR 0060
   decision 9 fixes both, so `library-archetype.md`'s `ci-jobs` reference and
   `file-conflicts.md`'s `ci-steps` reference both stay accurate).

3. **`ci-jobs` ships published-but-unfilled; no archetype moves a version.**
   The platform owns all four CI jobs (`lint`, `typecheck`, `test`, `build`)
   unconditionally, with a full-history checkout (`fetch-depth: 0`) on every
   job. That keeps the workflow neutral to an archetype's packaging mode —
   Copier only sets `fetch-depth: 0` for `library`'s `hatchling-vcs` mode, and
   a platform template must not branch on an archetype option (the leakage
   [ADR 0056](0056-three-archetype-composition-boundary-review.md) removed). A
   full clone is always correct, only slightly slower, and is a recorded parity
   narrowing. `library` fills `ci-jobs` (a build-and-publish job) and
   `api-reference` together at FT-17.03, moving `1.0.1` → `1.1.0` once;
   `library` / `cli` / `data-science` all stay put here. This mirrors FT-11.01,
   which published three extension points before anything filled them. Rejected:
   `library` contributing the build job now (leaves `cli` / `data-science`
   projects with no CI build job, and moves `library`'s regression digests in
   this PR); omitting `fetch-depth` (a real `hatchling-vcs` defect, not a
   narrowing).

4. **CI jobs run the generated `poe` tasks**, not direct `ruff` / `mypy` /
   `pytest` invocations. `poe lock:check` / `poe format:check` / `poe lint` /
   `poe typecheck` / `poe test` are Foundation-defined and unconditional, so
   when a capability later chains a task (`pyright` onto `typecheck`, `coverage`
   into the aggregate `check`) CI picks it up with no `ci-steps` contribution
   and no platform change. Semantics are preserved; this is the same class of
   recorded relocation as ADR 0060's move of `[tool.coverage]` to `.coveragerc`.
   Rejected: mirroring Copier's direct tool calls (hard-codes the toolchain
   into the workflow and diverges silently from what `poe check` runs).

5. **The three new Foundation points are byte-neutral when unfilled.**
   `pyproject-project-urls` on `content/pyproject.toml.jinja`,
   `contributing-project-shape` on `content/CONTRIBUTING.md.jinja`, and
   `security-project-shape` on `content/SECURITY.md.jinja` are each a single
   column-anchored `[[forge:extension …]]` line placed so that removing it
   (the line and its trailing newline) restores the exact prior bytes —
   verified by `tests/fixtures/archetype_regression/digests.json` staying
   unchanged across all eight `library` / `cli` selections. `foundation_version`
   stays `1` (ADR 0060, ADR 0061): the points are content, not a change to the
   source's TOML shape. README host links reuse the existing
   `readme-project-shape`. No Foundation file names "GitHub" — the point ids
   are host-neutral and
   `test_capability_composition.py::test_foundation_source_names_no_capability_or_domain_tool`
   is the guard. Rejected: rewriting Foundation prose so links weave inline
   (needs more points than ADR 0060 reserved, moves every archetype's bytes,
   forces a `digests.json` regeneration and version bumps).

6. **The eleven `github`-owned rows in
   [engine-default-parity.md](../engine-default-parity.md) flip to `shipped`
   now.** `github_org`, `repo_url`, `codeowners_team`, `python_matrix`, the six
   `template/.github/**` file rows, and `operating-systems` become `shipped`;
   `tests/test_parity_inventory.py`'s reference render gains
   `platforms: ["github"]` so `test_shipped_file_rows_match_a_real_library_render`
   proves the flip against a real render. Capability-owned rows stay `gap` for
   FT-17.03. Rejected: leaving them `gap` until FT-17.05 (the inventory would
   claim a gap the catalogue has closed, and nothing forces the later flip).

7. **`get_engine_info()` needs no field.** `discover_components()` already
   returns the `github` `ComponentDescriptor` — `id`, `name`, `description`,
   `kind`, `version`, `projectspec_protocols`, `requires_python`, `requires`,
   `conflicts`, `options` — and clients select `platforms=["github"]` plus
   `component_options.github.organisation`. No public name is added;
   `forge_template.__all__` is unchanged.

8. **`project.version` stays `0.4.1` and `main` stays untagged.** FT-17.06
   bumps to `0.5.0` and runs the protected release workflow, exactly as FT-17.01
   / ADR 0062 decision 7 and the FT-12.01 precedent. Merging is not releasing.

## Consequences

- `discover_components()` returns six components — `cli`, `data-science`,
  `github`, `jupyter`, `library`, `scientific-python`, lexical order — one of
  them a platform. Every hard-coded five-id test literal gains `"github"`.
- The published Foundation extension-point inventory grows eleven → fourteen
  (`pyproject-project-urls`, `contributing-project-shape`,
  `security-project-shape`), plus `ci-jobs` / `ci-steps` on the `github`
  platform's own content. Additive only; `foundation_version` stays `1`. This
  is the increment ADR 0060 and ADR 0061 anticipated; the package-version bump
  they tie it to is FT-17.06's `0.5.0`.
- `content/CONTRIBUTING.md.jinja` and `content/SECURITY.md.jinja` are no longer
  sole-owner content — they join `content/pyproject.toml.jinja` and
  `content/README.md.jinja` as extensible. `.editorconfig`, `.gitattributes`,
  `.python-version.jinja` and `LICENSE.jinja` stay sole-owner.
- The two `tests/test_platform_composition.py` tripwires are turned over: the
  discovery check now asserts three archetypes, two capabilities and **one**
  platform, and the reserved-Foundation-point set drops the three this issue
  publishes (FT-17.03's two remain). The four synthetic fixtures stay — they
  cover the `conflicts` edge and the unsatisfied-`requires` branch the shipped
  catalogue still cannot reach.
- `tests/test_composition_architecture_review.py`'s package-size pin is
  re-baselined to include the `github` tree and the Foundation marker lines;
  the prose figures in
  [composition-architecture-review.md](../composition-architecture-review.md)
  and [cross-repository-validation.md](../cross-repository-validation.md) move
  with it. ADR 0056's and ADR 0057's measurements stand as the pre-cutover
  historical record. FT-17.03 moves the pin again.
- Recorded parity narrowings: the derived, non-overridable `repo_url` (always
  `github.com`) and `codeowners_team` (`@<organisation>/<repository_name>-maintainers`);
  Copier's mypy-less `pyright` type-checking answer (Foundation's mypy gate
  cannot be disabled); and the pull-request template's "Docs updated" checklist
  line, which is unconditional here (no `use_docs`, and no extension point on
  that file).
- No generated content for `library` / `cli` / `data-science` changes, no
  `copier.yml` change, no `template/**` change, no package version bump, no
  release. `main` stays on `0.4.1` and untagged until FT-17.06.
