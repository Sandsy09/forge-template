# 24. Define strict bundled component manifest protocol v1

## Status

Accepted

## Context

ProjectSpec protocol v1 names one archetype and optional capabilities and
platforms, but identifiers alone do not tell the future engine what a component
is, which request and Python ranges it supports, what reviewed content it owns,
or which components it requires or conflicts with. Keeping that metadata in
`create-forge` would recreate the bundled-registry duplication that the accepted
public-engine architecture is intended to remove.

The format must be executable enough for later composition and discovery work
without prematurely migrating the monolithic Library scaffold, choosing a
second archetype, or deciding ordering, collision, option-schema, and stable
engine-API contracts assigned to later roadmap issues.

## Decision

Adopt the canonical [component manifest protocol v1](../component-manifests.md)
as strict, human-authored `component.toml` backed by frozen Pydantic models in
`forge_template.component_manifest`.

Every manifest declares protocol version `1`, a globally unique lower-case
kebab-case ID, separate human-facing name and description, one of the
archetype/capability/platform kinds, a canonical PEP 440 component version, a
required owned content root, optional future option-schema resource,
ProjectSpec protocol and complete generated-Python-range compatibility, and
unordered hard dependency and conflict references with optional PEP 440
component-version constraints.

Normal manifests ship inside the reviewed engine release. They do not declare
a redundant engine range and cannot introduce remote registries or arbitrary
plugins. The manifest and ProjectSpec protocol versions, component version, and
engine package version remain separate compatibility axes.

Validate resource containment, global identity, reference existence and
version matching before selection. A valid effective ProjectSpec must use the
declared component kinds, satisfy compatibility, name every required component
explicitly, and contain no selected conflict. The engine will reject missing
dependencies rather than mutate ProjectSpec silently.

Treat lexical reference and validator return order as canonical inspection
order only. Leave dependency-cycle handling and composition order to FT-06.03,
file operations and collisions to FT-06.04, option-schema meaning to FT-06.05,
contract fixtures to FT-06.06, and discovery plus stable errors and rendering
to FT-06.07.

Define models, a TOML/resource loader, and provisional validation helpers now,
but add only test fixtures. Do not create a production Library manifest or move
current template assets before the Stage 08 migration.

## Consequences

- `forge-template` becomes the executable owner of component identity,
  compatibility, dependencies, conflicts, and reviewed source-content roots.
- Future clients can display names and descriptions while persisting canonical
  IDs and consuming compatibility only through the engine.
- The complete selected Python range is protected rather than checking only its
  minimum or development endpoint.
- Hard dependencies remain visible in effective ProjectSpec instead of being
  silently auto-selected.
- PEP 440 parsing adds `packaging` as a bounded direct runtime dependency of the
  future engine package; generated projects gain no dependency.
- Strict containment rejects missing, empty, traversal, absolute, and symlink-
  escaping resource paths before rendering.
- Cycles, output operations, option validation, discovery, stable error shapes,
  and production component migration remain deliberately incomplete.
- The current v0.1.x Copier path, template tree, generated output, and CLI
  behaviour do not change.
