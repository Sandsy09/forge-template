# 33. Migrate the Library archetype to the production catalogue

## Status

Accepted

## Context

[ADR 0031](0031-library-archetype-contract.md) accepted the Library
archetype contract without implementing it: "This decision changes no code,
template, schema, answer, generated output, public API, tag, or release."
FT-08.02 ([#41](https://github.com/Sandsy09/forge-template/issues/41)) is the
implementation, split into two sequenced pull requests on the same issue.

The first landed the protocol mechanism against fixtures only: manifest
protocol `2`'s discriminated contribution target, the implicit Foundation
content source (`forge_template.foundation_source`), rendered output paths
([ADR 0032](0032-render-component-content-paths.md)), option-schema protocol
`2` with `format`, and the discriminated `PlannedFile.owner` replacing
`owner_component_id`. That PR deliberately shipped no production content --
the installed catalogue stayed empty, so nothing in the mechanism was yet
exercised end-to-end against a real archetype.

This record covers the second: populating that mechanism with the actual
`library` production manifest and the actual Foundation content, and proving
the result builds real, installable, importable Python packages.

[create-forge#85 / CF-08.04](https://github.com/Sandsy09/create-forge/issues/85)
is blocked on this issue and needs a non-empty production catalogue to
exercise the public engine path end-to-end.

## Decision

Add `src/forge_template/foundation/` (`foundation.toml` plus `content/`:
`pyproject.toml.jinja`, `README.md.jinja`, `LICENSE.jinja`,
`CONTRIBUTING.md.jinja`, `SECURITY.md.jinja`, `.gitignore.jinja`,
`.gitattributes`, `.editorconfig`, `.python-version.jinja`) and
`src/forge_template/components/library/` (`component.toml` at manifest
protocol `2`, component version `1.0.0`; `options.schema.json` at
option-schema protocol `2` declaring `packaging_mode` and a
`pep440`-formatted `initial_version`; owned `src/<package_name>/` and
`tests/` content; five `extensions/` contributions).

Foundation publishes five extension points -- `pyproject-build-system`,
`pyproject-library-metadata`, `pyproject-build-configuration`,
`readme-project-shape`, and `gitignore-project-shape` -- one more than ADR
0031 named. `gitignore-project-shape` is additive: it is where Library
ignores the `_version.py` file `hatchling-vcs` mode generates at build time,
with no other accepted contract to attach it to.

`template/` and `copier.yml` are untouched. The new package content is
purely additive alongside the released Copier tree; `create-forge` continues
to consume only the Copier path until a later, separate cutover decision.

Content is rewritten, not copied, from the monolithic Copier scaffold: the
nested variable namespace (`project.*`, `python.*`, `options.*`), no
`repo_url`/`github_org` (ProjectSpec deliberately excludes both), and every
capability-conditional branch (`use_docs`, `changelog_tool`, `type_checking`,
`coverage_fail_under`, `dependency_updates`) dropped, since no capability
component exists in the production catalogue yet to own them. Foundation's
quality gate is fixed to `mypy` with no coverage threshold, an accepted
simplification pending a profile or options mechanism to reintroduce that
choice.

`forge_template.map_legacy_library_answers` is added as a public, pure
function implementing the documented legacy Copier answer mapping.

## Consequences

- The production catalogue now contains exactly `library`;
  `discover_components()`, `plan_generation`, and `render_project` compose it
  with Foundation end-to-end.
- `uv run poe archetype` (the `archetype` pytest marker) proves all three
  packaging modes build real wheels and sdists, install, import, and expose
  the requested version -- not merely rendered text.
- `template/`'s monolithic scaffold and this package-bound catalogue
  deliberately co-exist and duplicate concerns until a later cutover; this is
  a documented consequence, not an oversight, and CLAUDE.md invariant 3
  applies once that cutover moves any `template/` path.
- create-forge#85's native blocker on a non-empty production catalogue is
  cleared; its remaining blocker (a released `forge-template` distribution)
  is unaffected by this change.
- `forge-template` moves to package version `0.3.0`, carrying the
  `PlannedFile.owner` migration; `main` stays untagged, so no released engine
  range is affected.
- Known gaps against the Copier scaffold's output (no `.env.example`,
  secret scanning, coverage threshold, documentation site, or GitHub-specific
  files) are named in docs/library-archetype.md as deliberate, tracked
  absences rather than silently claimed parity.
