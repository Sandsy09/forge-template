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
