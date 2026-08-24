# Forge Foundation Roadmap Pack — Two-Repository Edition

This roadmap models Forge as two independent repositories joined by an
explicit, versioned contract:

- **`forge-template`** owns generated content and, if the Stage 00 architecture
  decision adopts it, the component/composition engine.
- **`create-forge`** owns CLI input, presentation, and filesystem orchestration.

The `forge-template` issue drafts were reconciled against the working v0.1.x
baseline and filed on GitHub on 2026-08-23. Completed baseline work was not
backfilled as closed issues. The
[live issue index](github-issues/forge-template/ISSUE-INDEX.md) records evidence
for completed work and links every open epic and child issue; GitHub issue
bodies and native relationships are the source of truth for open work.

The [canonical terminology](../terminology.md) defines the architectural terms
and authority rules used throughout this roadmap without duplicating them in
individual stage documents.

The public engine/ProjectSpec model is the accepted target under
[create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md).
It is not implemented; the existing Copier baseline remains operational until
Stages 04–09 deliver the coordinated cutover.

## Structure

```text
docs/roadmap-v1/
├── README.md
├── REPOSITORY-OWNERSHIP.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── roadmap/<stage>/README.md
└── github-issues/
    ├── GITHUB-SETUP.md
    ├── CROSS-REPO-DEPENDENCIES.md
    └── forge-template/ISSUE-INDEX.md
```

Start with `REPOSITORY-OWNERSHIP.md`, then `ROADMAP.md`, then the live issue
index. Cross-repository work is represented by native GitHub dependencies,
not duplicated implementation tickets.
