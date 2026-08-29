# Proposed Forge Two-Repository Architecture

> **Status:** This is the accepted target architecture under
> [create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md),
> not the current CLI implementation. ProjectSpec, component manifest protocol
> v1, composition order, file conflict and override rules, the template
> variable contract, and the stable `forge-template` `0.2.x` engine API are
> implemented. Its production catalogue remains empty until Stage 08, and the
> current CLI remains a thin Copier client with a bundled registry until the
> coordinated cutover.

The [canonical terminology](../terminology.md) defines the ecosystem,
composition, and authority terms used by this target.
The [ProjectSpec protocol](../project-spec.md) defines the strict,
engine-owned request passed across this boundary, while leaving CLI
construction and filesystem orchestration with `create-forge`.
The [component manifest protocol](../component-manifests.md) defines the
strict engine-owned metadata and compatibility for every future bundled
archetype, capability, and platform.
The [Library archetype contract](../library-archetype.md) defines the first
production archetype and the implicit package-bound Foundation source it will
extend. Its manifest v2, option-schema v2, discriminated planning owner, and
`0.3.0` engine facade are accepted requirements for FT-08.02, not current
behaviour.
The [composition order contract](../composition-order.md) defines the single
deterministic order that future bundled selection applies in.
The [file conflict and override rules](../file-conflicts.md) define the
output target, disposition, and collision-safety rules that composed
selection resolves against.
The [template variable contract](../template-variables.md) defines the
rendered variable namespace and the component option vocabulary declared
through `options_schema`.
The [stable template-engine API](../template-engine-api.md) is the typed,
side-effect-free boundary for discovery, validation, planning, and in-memory
rendering. The
[generated-project validation contract](../generated-project-validation.md)
checks the immutable result before it crosses that boundary. Target-directory
orchestration remains with clients.
The [Foundation guarantees](../foundation-guarantees.md) define the
provider- and tool-neutral outcomes every successfully generated project must
receive regardless of whether this proposed composition model is adopted.
The [Foundation scope](../foundation-scope.md) limits that baseline to
universal guarantee, neutral handoff, and update/provenance concerns and keeps
generated runtime behaviour with its owning archetype or capability.
The [Python support policy](../python-support.md) defines the rolling CPython
window in which the generated-project guarantees are claimed.
The [editor integration strategy](../editor-integration.md) keeps Foundation
and Forge's default profile vendor-neutral while routing future editor bridges
to optional capabilities.
The [configuration ownership conventions](../configuration-ownership.md)
assign typed runtime settings to the archetype or capability consuming them
and require explicit entrypoint assembly and injection.
The [environment-variable conventions](../environment-variables.md) extend
that owner-local model with namespacing, source precedence, and an explicit
local dotenv boundary.
The [structured logging capability](../structured-logging.md) keeps event
vocabularies owner-local while assigning process-wide configuration,
formatting, redaction, and provider-neutral stream handling to one runtime
owner.
The [path and resource ownership conventions](../paths-and-resources.md) keep
runtime path and resource access owner-local and free of implicit process
context such as the current working directory or a discovered project root.
The [exception ownership conventions](../exception-ownership.md) keep
exceptions owner-local, require a failure to be handled once, and assign
translation of an escaped failure into a process outcome to the runtime
entrypoint.
The [secret-handling safeguards](../secret-handling.md) keep secret-bearing
files out of version control and enforce a placeholder-only tracked example,
while leaving broader scanning as an optional capability or platform
contribution.
The [supply-chain provenance contract](../supply-chain-provenance.md) defines
desired SBOM and release-provenance behaviour as a future capability and
platform contribution, deferred until a generated-project release/publish
path exists.
The [GitHub Action pinning policy](../github-action-pinning.md) applies
immutable, updater-readable references to the current GitHub platform
integration without making GitHub Actions a Foundation requirement.

```text
┌─────────────────────────────┐
│        create-forge         │
│ CLI / prompts / flags       │
│ ProjectSpec construction    │
│ filesystem orchestration    │
└──────────────┬──────────────┘
               │ versioned public contract
               ▼
┌─────────────────────────────┐
│       forge-template        │
│ ProjectSpec validation      │
│ component discovery         │
│ composition / rendering     │
│ generated output validation │
│ generated project content   │
└──────────────┬──────────────┘
               ▼
        Generated Project
```

If adopted, the boundary lets CLI UX evolve independently from
generated-project architecture and leaves room for future clients, including
Blueprint, to consume the same engine directly.

## Critical invariant

Generated projects require neither `forge-template` nor `create-forge` for normal development or runtime operation. Forge is a generator, not an application framework dependency.
