# Stage 10 — Data Science Architecture Contract

## Epic

[FT-EPIC-10 / forge-template#96](https://github.com/Sandsy09/forge-template/issues/96)
defines the contract before any component is implemented.

## Dependencies

This epic has no open native blocker. The roadmap begins only after completed
`create-forge#91` and the completed Foundation roadmap provide its accepted
engine and client baseline.

## Child sequence

1. [FT-10.01 / #101](https://github.com/Sandsy09/forge-template/issues/101)
   is complete: the canonical [Data Science contract](../../../data-science-archetype.md)
   defines the fixed package-plus-notebooks shape and ownership.
2. [FT-10.02 / #102](https://github.com/Sandsy09/forge-template/issues/102)
   is complete: the canonical [initial capability
   contracts](../../../data-science-capabilities.md) define optionless
   `jupyter` and `scientific-python` components and bounded dependency lines.
3. [FT-10.03 / #103](https://github.com/Sandsy09/forge-template/issues/103)
   is complete: the canonical [notebook, data, and model
   safeguards](../../../notebook-data-and-model-safeguards.md) define the
   fail-closed `notebook:check` validation order, deterministic failure
   identifiers, safe diagnostics, and the prose-only working-tree guidance.
4. [FT-10.04 / #104](https://github.com/Sandsy09/forge-template/issues/104)
   is complete: the canonical [compatibility and acceptance
   contract](../../../data-science-compatibility-and-acceptance.md) classifies
   every versioned axis for the `0.4.0` line, fixes the executable acceptance
   matrix and its owners, and states the cross-repository release gates.

Each child was blocked by the preceding item. All four are complete; the epic
is ready to close and Stage 11 is unblocked.

## Entry criteria

- Forge Foundation Stages 00–09 are complete.
- Library and CLI Application prove independent production archetypes.
- create-forge #91 has completed engine-native option prompting.

## Outcomes

- Define the minimal package-plus-notebooks project shape.
- Assign every concern to Foundation, archetype, capability, platform,
  profile, organisation policy, or client orchestration.
- Define dependency-selection criteria rather than selecting tools by trend.
- Define data, model, secret, path, environment, and generated-artifact
  safeguards.
- Define Python, lock, packaging, notebook-validation, and maintenance
  expectations.
- Classify all protocol, public API, component, engine, and client
  compatibility impacts.

## Exit criteria

The four accepted decisions make the shape, capability boundaries,
safeguards, compatibility impact, and acceptance strategy implementation-ready.
All four are accepted, so this exit criterion is met.

## Non-goals

No production component, dependency, generated output, CLI behavior, tag, or
release is introduced in this stage.
