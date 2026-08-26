# Proposed Forge Two-Repository Architecture

> **Status:** This is the accepted target architecture under
> [create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md),
> not the v0.1.x implementation. The current CLI is a thin Copier client with
> a bundled registry, and `forge-template` exposes no
> ProjectSpec/component-engine API until the coordinated cutover.

The [canonical terminology](../terminology.md) defines the ecosystem,
composition, and authority terms used by this target.
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
