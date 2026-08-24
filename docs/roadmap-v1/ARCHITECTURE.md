# Proposed Forge Two-Repository Architecture

> **Status:** This is the Stage 06 target architecture, not the v0.1.x
> implementation. The current CLI is a thin Copier client with a bundled
> registry, and `forge-template` exposes no ProjectSpec/component-engine API.
> [create-forge#41](https://github.com/Sandsy09/create-forge/issues/41) decides
> whether this proposal supersedes the accepted baseline ADRs.

The [canonical terminology](../terminology.md) defines the ecosystem,
composition, and authority terms used by this proposal.
The [Foundation guarantees](../foundation-guarantees.md) define the
provider- and tool-neutral outcomes every successfully generated project must
receive regardless of whether this proposed composition model is adopted.

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
