# Forge Architectural Terminology

This document is the canonical vocabulary for Forge, its reference CLI, and
future downstream integrations such as Blueprint. It defines conceptual
boundaries and authority; it does not introduce a ProjectSpec schema,
component engine, or other public API.

The public engine model is the accepted target under
[create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md),
but it is not implemented. Where a term describes that future contract, it is
marked accordingly.

## Ecosystem terms

### Forge

Forge is the open-source project-generation ecosystem spanning the canonical
template and composition contract owned by `forge-template` and the
`create-forge` reference CLI. Forge is a generator: it does not become a
runtime framework dependency of the projects it creates.

### Blueprint

Blueprint is a future organisation-facing downstream integration that consumes
Forge contracts and applies organisation policy. It is not part of the current
two-repository implementation and must not become a generated-project runtime
dependency.

### Generated project

A generated project is Forge's output. After generation, it remains usable for
normal development, testing, building, and runtime operation without either
`forge-template` or `create-forge` installed.

## Composition terms

### Foundation

Foundation is the mandatory baseline contract received by every generated
project. It owns cross-archetype guarantees rather than a particular project
shape. Later layers may strengthen those guarantees or use documented
extension points, but may not weaken them.

The exact outcomes are defined by the canonical
[Foundation guarantees](foundation-guarantees.md), delivered through
[FT-00.01](https://github.com/Sandsy09/forge-template/issues/19). The
[Foundation scope](foundation-scope.md), delivered through
[FT-00.03](https://github.com/Sandsy09/forge-template/issues/21), defines which
concerns may belong in that baseline and how other concerns are routed. The
[Python support policy](python-support.md), delivered through
[FT-00.04](https://github.com/Sandsy09/forge-template/issues/22), defines the
supported interpreter environments in which those outcomes are provided.

### Archetype

An archetype is the single primary project shape composed over Foundation. It
owns structural choices that distinguish one kind of project from another,
such as the Library archetype's packaging and source layout. Every generated
project has exactly one archetype.

An archetype may refine documented Foundation extension points, but it may not
replace or weaken Foundation guarantees.

### Capability

A capability is an optional, reusable project concern that can apply across
archetypes. A project may select zero or more capabilities. Documentation,
changelog support, release provenance, or an optional editor bridge are
examples of concerns that can be modelled as capabilities when the composition
engine exists. Editor-specific integration follows the canonical
[editor integration strategy](editor-integration.md).

A capability contributes content it owns or participates through an explicit
extension point. It does not gain a general right to overwrite Foundation or
archetype content.

An archetype or capability that contributes configurable runtime behaviour
follows the canonical
[configuration ownership conventions](configuration-ownership.md): it owns a
stable typed fragment, while the runtime entrypoint assembles and injects
selected fragments explicitly. If that fragment accepts environment-backed
input, the [environment-variable conventions](environment-variables.md)
define its namespace, precedence, and local dotenv boundary.

### Platform

A platform adapts a project to an external hosting, delivery, deployment, or
runtime target. A GitHub Actions integration or a container platform adapter
is a platform concern, rather than a definition of the project's primary
shape.

Whether ProjectSpec permits one or several platform selections remains a Stage
06 schema decision. A platform follows the same no-implicit-overwrite rule as
other content-producing layers.

### Profile

A profile is an optional, named, non-enforcing bundle of default answers and
component selections. It is a convenience input, not a component and not an
authority boundary. Explicit user choices may replace profile defaults.

A profile is distinct from a developer's saved CLI identity or preferences:
the CLI may use those preferences to choose a profile, but they are not the
profile itself. Forge's default profile remains editor-neutral; other named or
organisation profiles may later default optional editor capabilities without
making those defaults mandatory.

### Organisation policy

Organisation policy is a downstream set of required, default, and forbidden
constraints applied to a generation request. Policy constrains or defaults
selection; it is not a component and does not render arbitrary files.

This definition establishes policy authority only. The policy schema,
validation errors, and safe extension mechanisms remain owned by Stage 09.

### Component

A component is a future machine-discoverable, composable unit in the accepted
public-engine target. Archetypes, capabilities, and platforms are component
kinds. Foundation is the mandatory baseline; profiles and organisation
policies are inputs that select or constrain components, not components
themselves.

Component manifests, compatibility metadata, and composition behaviour remain
Stage 06 work and do not exist in the v0.1.x implementation.

### ProjectSpec

ProjectSpec is the future serialisable description of a project-generation
request in the accepted public-engine target. It will carry project metadata and the selected archetype,
capabilities, platform information, and profile or policy inputs needed by a
future composition engine.

Its schema and public API are not defined here. Both remain Stage 06 work under
the ownership and compatibility boundary accepted by
[create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md).

## Composition and authority

The structural model is:

```text
Foundation
  + exactly one archetype
  + zero or more capabilities
  + platform selection (cardinality deferred to Stage 06)
```

Profiles and organisation policies influence the requested selection; they do
not form additional rendering layers. Defaults and constraints resolve in this
order, from lowest to highest authority:

```text
profile default
  < organisation-policy default
  < explicit user choice
  < required or forbidden organisation constraint
```

Foundation guarantees sit outside that configurable precedence and cannot be
weakened by any of those inputs.

The following rules are normative:

1. Foundation guarantees cannot be weakened.
2. Archetypes, capabilities, and platforms may contribute content they own or
   use documented extension points; implicit last-write-wins replacement is
   forbidden.
3. Explicit user choices override defaults, but not required or forbidden
   organisation constraints.
4. Organisation constraints cannot weaken Foundation guarantees.
5. Unsupported component collisions fail rather than silently overwriting
   content.

Stage 06 will define deterministic ordering and collision mechanics in
[FT-06.03](https://github.com/Sandsy09/forge-template/issues/34) and
[FT-06.04](https://github.com/Sandsy09/forge-template/issues/35). Stage 09 will
define safe downstream extension points in
[FT-09.02](https://github.com/Sandsy09/forge-template/issues/45).

## Composition examples

### Current Library scaffold, mapped conceptually

The v0.1.x Library scaffold is monolithic; it does not yet implement these as
components. Its existing choices can nevertheless be described consistently:

- Foundation is the future shared baseline beneath every archetype; its exact
  outcomes are defined by the
  [Foundation guarantees](foundation-guarantees.md).
- Library is the single archetype and owns the Python-library project shape.
- Optional documentation or changelog support are capability-shaped concerns.
- GitHub Actions support is a platform-shaped integration.
- A maintainer profile could default selections such as build backend,
  versioning, and documentation without enforcing them.
- An organisation policy could later require or forbid selections without
  replacing template files arbitrarily.

This mapping is explanatory only; it does not claim that the current files are
already separated into components.

### Neutral future composition

A future request could combine Foundation, `<archetype>`,
`<capability-a>`, and `<platform>`, with `<profile>` supplying convenient
defaults and `<organisation-policy>` constraining allowed selections. The
placeholders deliberately do not name or select the roadmap's second reference
archetype.

## Deferred decisions

This terminology does not decide:

- the ProjectSpec wire format or validation API;
- component manifest fields, ordering, merge, or collision algorithms;
- platform cardinality;
- organisation-policy schema or error types;
- the identity of the second reference archetype; or
- the concrete engine package range, ProjectSpec protocol number, and source
  resolution interface.

Those decisions remain with their Stage 04–09 roadmap issues. The current
v0.1.x thin Copier/bundled-registry implementation stays operational until the
accepted target is delivered as a coordinated cutover.
