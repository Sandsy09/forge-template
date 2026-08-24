# Forge Foundation Two-Repository Roadmap

> **Architecture status:** The existing Copier-based Library scaffold remains
> the production baseline. The public-engine/ProjectSpec target is accepted by
> [create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md),
> and Stages 04–09 implement it in dependency order. Stage 08 keeps archetype two generic until
> [FT-08.03](https://github.com/Sandsy09/forge-template/issues/42) selects and
> defines it.

The roadmap remains one product roadmap, with implementation ownership split
between repository-local epics and issues.

| Stage | Theme | forge-template | create-forge | Integration intensity |
|---|---|---:|---:|---|
| 00 | Governance and Principles | 5 issues | 2 issues | High |
| 01 | Python Core | 5 issues | 2 issues | Medium |
| 02 | Developer Experience | 4 issues | 2 issues | Medium |
| 03 | Quality and CI | 6 issues | 3 issues | Medium |
| 04 | Runtime and Configuration | 5 issues | 1 issue | Medium |
| 05 | Security and Supply Chain | 5 issues | 2 issues | Medium |
| 06 | Extension and Composition Contract | 7 issues | 3 issues | High |
| 07 | Forge CLI Integration | 1 issue | 5 issues | High |
| 08 | Reference Archetype Validation | 5 issues | 3 issues | High |
| 09 | Blueprint Compatibility | 5 issues | 3 issues | High |

## Delivery rule

Create a stage epic only in repositories with remaining work for that stage.
Where both repositories have an epic, link the counterpart as related work.
Child issues stay with the implementation owner, and native GitHub
relationships express local and cross-repository blockers.

Stages 01 and 03 in `forge-template` were complete before roadmap import, so no
retrospective epics were filed. See the
[live issue index](github-issues/forge-template/ISSUE-INDEX.md) for the evidence
and current graph.
