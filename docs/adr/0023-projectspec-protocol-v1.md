# 23. Define strict ProjectSpec protocol v1

## Status

Accepted

## Context

The accepted public-engine architecture assigns canonical generation-request
types and validation to `forge-template`, while `create-forge` and future
clients construct those requests. Stage 00 defined the vocabulary and
authority order but deliberately left the ProjectSpec wire format, platform
cardinality, metadata boundary, and policy representation to Stage 06.

Without a concrete schema, component manifests, template variables,
composition ordering, contract tests, and the stable engine API cannot share
one typed request. Reusing the current flat Copier answers would also preserve
provider-specific fields at the top level and give future clients no explicit
protocol compatibility check.

## Decision

Adopt the canonical [ProjectSpec protocol v1](../project-spec.md) implemented
by frozen, strict Pydantic v2 models in `forge_template.project_spec`.

Protocol v1 uses snake-case JSON, requires integer `protocol_version` `1`,
forbids unknown fields and implicit coercion, and derives JSON Schema from the
models. It carries provider-neutral project metadata, a validated CPython
minimum/development pair, exactly one archetype, zero or more capabilities,
zero or more platforms, optional profile/policy provenance, and
JSON-compatible options namespaced by selected component identifiers.

Identifiers are unversioned lower-case kebab-case. The installed,
version-constrained engine release and future manifests own component versions
and compatibility. Set-like selections are unique and canonically sorted for
serialisation, but that ordering does not define composition order.

ProjectSpec contains effective selections. Profiles and organisation policies
are recorded as provenance only after their defaults and constraints have
been applied. Stage 09 retains ownership of policy documents and resolution.
The schema permits multiple platforms because compatible repository, delivery,
deployment, and runtime adapters may contribute distinct concerns.

The models are importable from their defining module, but this decision does
not expose the stable top-level engine facade, rendering functions, structured
engine errors, or a supported `create-forge` integration line. FT-06.07 and
the coordinated cutover retain those responsibilities.

## Consequences

- Later Stage 06 issues can target one executable, versioned request rather
  than inventing parallel mappings.
- Provider-specific repository data moves into its platform namespace instead
  of contaminating core project metadata.
- Python support-window drift is detected against the current Copier choices,
  while the tested matrix remains derived rather than caller-controlled.
- Profile and policy provenance remains observable without giving either
  arbitrary rendering or code-execution authority.
- Pydantic v2 becomes a bounded runtime dependency of the future engine
  package; generated projects acquire no dependency.
- Component existence, option catalogues, ordering, collision behaviour,
  rendering, and structured engine errors remain deliberately incomplete.
- Protocol 1 is defined but is not yet a supported CLI/engine pair. The
  current direct-Copier path and its generated output remain unchanged.
