# Forge Foundation Scope

This document defines which concerns belong in Forge Foundation and how work
outside that boundary is assigned. It complements the
[canonical architectural terminology](terminology.md) and the
[Foundation guarantees](foundation-guarantees.md): those references define the
layers and mandatory outcomes, while this one limits what Foundation may own.

The boundary applies to concerns, not whole files. A generated file such as
`pyproject.toml` may eventually contain contributions owned by Foundation and
an archetype without making every setting in that file part of Foundation.
The current Library scaffold remains monolithic; the mapping below is
conceptual and does not claim that a component engine or file-level separation
already exists.

## Inclusion rule

A concern belongs in Foundation only when it is mandatory for every supported
archetype and satisfies at least one of these purposes:

1. it is necessary to provide a
   [Foundation guarantee](foundation-guarantees.md#mandatory-guarantees);
2. it is necessary for a complete, independent handoff through neutral project
   identity and metadata, licensing, root guidance, security guidance, or
   repository hygiene; or
3. it is necessary to preserve safe Forge update or generation-provenance
   behaviour across every project shape.

It must also satisfy every condition below:

- **Universal:** every archetype needs the concern, and users cannot disable
  the mandatory outcome.
- **Shape-neutral:** the contract can be stated without knowing the project's
  packaging, source layout, execution model, or domain.
- **Provider-neutral:** the concern does not require a particular source host,
  CI system, delivery service, cloud, or runtime platform.
- **Framework- and organisation-neutral:** it introduces no application
  framework, domain model, or organisation policy.
- **Runtime-free:** it does not create a shared Foundation module, base class,
  service, or third-party runtime dependency in generated projects.
- **Stable and testable:** its outcome has an explicit contract that Forge can
  validate without workstation-specific state.

The removal test provides a concise check: if omitting a concern would not
break a guarantee, make the repository incomplete at handoff, or make universal
Forge update/provenance behaviour unsafe, the concern does not belong in
Foundation.

Tooling may be part of the current Foundation implementation when it delivers
an included concern. That does not make the tool itself permanent; replacements
must preserve the outcome and the boundary above.

## Included concerns

### Mandatory generated-project outcomes

Foundation owns the cross-archetype quality and independence outcomes in the
[guarantee contract](foundation-guarantees.md). These include declared and
locked development environments, automated lock-drift detection, configured
formatting, linting, typing and testing gates, an aggregate non-interactive
quality contract, and independence from Forge during normal project operation.

Foundation owns the underlying provider-neutral commands and outcomes. A
platform component may invoke them, but the platform does not redefine them.
An archetype supplies shape-specific source and test targets through declared
extension points while preserving every gate.

### Neutral handoff material

Every generated repository needs enough provider-neutral material to be
understood, maintained, and governed independently. Foundation therefore owns:

- project identity and generally applicable metadata;
- a selected licence and neutral licence material;
- root README, contribution, and security-reporting starters;
- documented project prerequisites and the first validation workflow; and
- base repository hygiene such as line-ending, ignore, and editor-neutral text
  conventions, including the boundary defined by the
  [editor integration strategy](editor-integration.md).

Later layers may add owned sections through explicit extension points. They may
not silently replace the neutral handoff material. Provider-specific links or
instructions within otherwise neutral guidance are supplied by the relevant
platform contribution.

### Forge update and provenance state

The generated repository retains the version-controlled state required to
identify its template origin and perform supported template maintenance. In the
current Copier implementation, `.copier-answers.yml` provides that state.
Copier and the template source remain maintenance-time dependencies rather than
normal development or runtime dependencies.

## Explicit exclusions

A concern is outside Foundation when any of the following applies:

- it is optional or exists primarily as a preference or convenience;
- it defines the project's primary structure, packaging, build behaviour, or
  execution model;
- it integrates with a source host, CI provider, delivery system, deployment
  environment, or runtime platform;
- it introduces generated runtime code, a shared base type, an application
  framework, or a domain dependency;
- it is specific to an organisation's required, default, or forbidden policy;
- it is experimental, disputed, or lacks evidence that every archetype needs
  it; or
- its benefit is consistency alone and its removal would pass the removal
  test.

Cross-cutting does not mean foundational. A concern may apply to several
archetypes and still be an optional capability.

## Routing non-Foundation concerns

Use the smallest owner that accurately describes the concern:

| Question | Owner |
| --- | --- |
| Does it define the primary project shape, packaging, build, or runtime structure? | The selected **archetype**. |
| Is it an optional concern reusable across project shapes? | A **capability**. |
| Does it adapt the project to an external host, CI, delivery, deployment, or runtime target? | A **platform**. |
| Does it provide non-enforcing default selections? | A **profile** input. |
| Does it require, default, or forbid selections for an organisation? | An **organisation-policy** input. |

Profiles and policies select or constrain components; they do not gain file
ownership. A provider-specific adapter used by a capability is still a platform
contribution, even when it enables the capability.

### Runtime ownership

Foundation supplies no generated configuration module, logging package,
resource helper, or base exception. The archetype or capability that
contributes runtime behaviour owns its configuration schema, environment
names, logging behaviour, resource access, and exception hierarchy. Runtime
settings follow the canonical
[configuration ownership and extension conventions](configuration-ownership.md),
which keep typed interfaces owner-local and assembly explicit. Owners that use
environment-backed inputs also follow the canonical
[environment-variable conventions](environment-variables.md). Runtime owners
that log follow the canonical
[structured logging capability contract](structured-logging.md), which assigns
event vocabulary to emitters and process-wide configuration to the runtime
entrypoint. Runtime owners that read or write files follow the canonical
[path and resource ownership conventions](paths-and-resources.md), which keep
path and resource access owner-local and free of implicit process context such
as the current working directory or a discovered project root.

Foundation may provide neutral safeguards without taking over the runtime
concern. For example, base ignore rules protect common secret-bearing local
files such as `.env`, while an `.env.example`, variable names, and a
configuration schema belong to the component that consumes them.

## Resolving disputed placement

A proposal to add or promote a Foundation concern must document:

- the guarantee, handoff requirement, or update/provenance requirement it is
  necessary to satisfy;
- why every supported archetype needs it and why an opt-out is invalid;
- its provider, framework, domain, organisation, and runtime dependencies;
- the stable outcome and validation that would enforce it; and
- why an archetype, capability, or platform cannot own it more narrowly.

The proposer carries the burden of proof. Until every inclusion condition is
demonstrated, the concern remains outside Foundation or is deferred. A semantic
change to this boundary requires a new accepted ADR that supersedes
[ADR 0012](adr/0012-conservative-foundation-scope.md); the living reference may
gain examples or clarifications that preserve the decision.

Stage 06 owns component manifests, extension points, composition ordering, and
file-conflict mechanics. This document assigns conceptual ownership but does
not define those APIs or algorithms.

## Current Library scaffold mapping

The v0.1.x Library scaffold emits one combined template. Its current concerns
map to the future layers as follows:

| Current concern | Conceptual owner |
| --- | --- |
| Declared development environment, lock state, formatting, linting, typing, testing, and aggregate quality commands | **Foundation**, as the current implementation of mandatory outcomes. |
| Project identity, neutral metadata, licence, root README/contribution/security starters, base repository hygiene, secret-file ignore safeguards, and Copier update state | **Foundation**, as neutral handoff or update/provenance material. |
| `src/` package layout, distributable-package metadata, build backend, versioning, typed-package marker, build/release behaviour, and the Library-specific smoke target | **Library archetype**. |
| Coverage reporting, pre-commit feedback, documentation, changelog support, dependency-update automation, configuration examples, and editor-specific integration | **Capabilities**; a future profile may select them, while the Forge default profile remains editor-neutral. |
| Runtime configuration, logging/observability, path/resource behaviour, and exception conventions | The **archetype or capability that contributes the runtime behaviour**; Foundation adds no shared runtime layer, configuration follows the [owner-local convention](configuration-ownership.md), logging follows the [structured capability contract](structured-logging.md), and path/resource access follows the [path and resource ownership conventions](paths-and-resources.md). |
| GitHub Actions, issue and pull-request templates, CODEOWNERS, and other GitHub-specific adapters | **GitHub platform** contributions. Provider-specific files used by a capability are supplied through that platform integration. |

This mapping does not move files, alter questions, or change generated output.
Future composition work may split contributions within a file, and must do so
through the explicit merge and extension contracts owned by Stage 06.

## Deferred decisions

This scope contract does not decide:

- the supported interpreter window and lifecycle defined by the canonical
  [Python support policy](python-support.md);
- exception conventions owned by the remaining Stage 04 work; runtime
  configuration, environment inputs, logging, and path/resource access are
  defined by the [ownership](configuration-ownership.md),
  [environment-variable](environment-variables.md),
  [structured-logging](structured-logging.md), and
  [paths-and-resources](paths-and-resources.md) conventions;
- the ProjectSpec schema, component manifest, extension points, ordering, or
  conflict algorithms owned by Stage 06;
- the implementation details of the public-engine target accepted by
  [create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md),
  including its first package and protocol versions; or
- the identity of the second reference archetype.
