# 58. Inventory default-Copier parity and assign ownership

Date: 2026-09-09

## Status

Accepted

## Context

`forge-template 0.4.1` ships a five-component composition engine catalogue,
but `create-forge` still generates by default through direct Copier over
`copier.yml` and `template/`, with the engine hidden behind
`--engine-preview`. The
[Engine-Default Cutover roadmap](../roadmap-v3/README.md)
([FT-EPIC-15](https://github.com/Sandsy09/forge-template/issues/141)) plans to
make the engine the default.

That plan needs a written account of what the engine does not yet do.
[FT-15.01](https://github.com/Sandsy09/forge-template/issues/146), the stage's
first and only initially actionable child, is a `type:decision` issue: it must
inventory every supported default-Copier behaviour and assign each to the
provider, the client, or an explicit exclusion, so that FT-15.02, FT-15.03 and
FT-15.04 — and all of Stage 17 — have a real scope.

The gap is concrete. Direct Copier emits up to 30 files from 23 questions. The
engine's implicit Foundation source plus its catalogue emit 13 files for the
`library` compatibility shape, from a `ProjectSpec` and the `library`
component's two packaging options. Whole categories exist only on the Copier
side: GitHub Actions CI, CODEOWNERS, issue and pull-request templates,
`.pre-commit-config.yaml`, `CHANGELOG.md`, Renovate/Dependabot,
the MkDocs site, `.env.example`, and the `.copier-answers.yml` provenance
state that makes `copier update` possible. Seven questions (`github_org`,
`codeowners_team`, `type_checking`, `coverage_fail_under`,
`dependency_updates`, `use_docs`, `changelog_tool`) have no `ProjectSpec`
route at all.

Four choices had to be made about how to record the inventory, without
pre-empting the design decisions the later children own.

## Decision

Publish the responsibility matrix as a living contract,
[engine-default-parity.md](../engine-default-parity.md), and record here the
choices that govern it.

1. **The matrix is pinned by a test that derives its expected rows from
   source.** `tests/test_parity_inventory.py` enumerates the `copier.yml`
   question keys and every `template/**` path and fails `uv run poe check` if
   any has no row. A future question or templated file cannot be added without
   an accompanying disposition. The test also rejects a row that cites an
   issue number absent from the filed roadmap manifests, and checks every
   `shipped` file row against a real `library` `render_project()` result.

2. **Optional tooling is provider-owned and tiered, not dropped.**
   Pre-commit configuration, coverage gating, MkDocs documentation, changelog
   generation, dependency-update automation, `.env.example` and the GitHub
   platform files are all assigned to the provider. Each `gap` row carries a
   tier: `cutover-blocking` (a generated repository is incomplete or unsafe
   without it — CI, CODEOWNERS, dependency automation, `.env.example`,
   pre-commit configuration, and the provenance/update state) or `deferred`
   (rebuilt as an optional concern after the engine becomes the default — the
   MkDocs site, the coverage gate, the changelog tool, and the issue and
   pull-request templates). Nothing is excluded by attrition.

3. **A gap with no filed implementation child is flagged, not filed.** Rows
   whose delivery does not fit a filed Stage 17 child carry the literal marker
   `needs a bounded issue` and no invented number. FT-15.04's acceptance
   criteria already require it to reconcile Stage 17 scope; it is the
   designed place to file those issues. FT-15.01 creates no GitHub issues.

4. **The roadmap pack under `docs/roadmap-v3/` is not edited by cutover
   work.** `scripts/check_roadmaps.py` hash-pins every issue body to its filed
   GitHub body, requires an unticked acceptance checklist to remain, and
   requires `status:blocked` to match the recorded blockers. Completion
   bookkeeping — ticking boxes, dropping `status:needs-decision`, unblocking
   successors, closing with completion evidence — happens on GitHub only. The
   mirror records the filed state.

Only exclusions the inventory itself makes: `_min_copier_version` and the
`{% if %}name{% endif %}` conditional-filename mechanic are Copier-runtime
specifics with no engine analogue and are marked `excluded`. Every other
Copier behaviour is provider or client.

This decision changes no runtime code, no generated content, no protocol
integer, no component or package version, and no `copier.yml` question. It
adds one living contract, this record, one test module, and the wiring that
links them.

## Consequences

- Stage 15's remaining children inherit a bounded, source-checked scope:
  FT-15.02 owns the provenance metadata and reproducible-update inputs,
  FT-15.03 owns the platform and capability assignments and the extension
  points they need, and FT-15.04 owns the compatibility classification and
  the bounded issues the flagged rows require.
- The `cutover-blocking` tier is the gate FT-15.04 binds its release criteria
  to; the `deferred` rows can follow the engine-default switch.
- `create-forge`'s Stage 16 contract work (`CF-EPIC-16`) can proceed against
  the published matrix once FT-15.04 completes the provider contract set.
- The GitHub platform component, still unbuilt, is now explicitly on the
  critical path rather than an implicit assumption.
- `tests/test_parity_inventory.py` will fail if a later contributor adds a
  `copier.yml` question or a `template/` file without updating the matrix,
  keeping the two paths' divergence visible until the cutover closes it.
- No template, Copier answer, component resource, engine module, dependency,
  golden digest, tag, or release changes.
