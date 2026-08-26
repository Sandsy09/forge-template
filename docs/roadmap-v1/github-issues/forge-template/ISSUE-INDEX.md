# forge-template Roadmap Issue Index

This is the live repository-local index for the Forge Foundation roadmap,
reconciled against the v0.1.x baseline and filed on GitHub on 2026-08-23.
GitHub issue bodies and native relationships are the source of truth for open
work; completed baseline items were not backfilled as closed issues.

| ID | GitHub issue / evidence | Status | Parent | Blocked by | Milestone |
|---|---|---|---|---|---|
| FT-EPIC-00 | [#11](https://github.com/Sandsy09/forge-template/issues/11) and [Stage 00 record](../../roadmap/00-governance-and-principles/README.md) | Complete | — | — | Foundation Contract — Stage 00 |
| FT-00.01 | [#19](https://github.com/Sandsy09/forge-template/issues/19), [guarantees](../../../foundation-guarantees.md), and [ADR 0011](../../../adr/0011-forge-foundation-guarantees.md) | Complete | [#11](https://github.com/Sandsy09/forge-template/issues/11) | — | Foundation Contract — Stage 00 |
| FT-00.02 | [#20](https://github.com/Sandsy09/forge-template/issues/20), [terminology](../../../terminology.md), and [ADR 0010](../../../adr/0010-forge-architectural-terminology.md) | Complete | [#11](https://github.com/Sandsy09/forge-template/issues/11) | — | Foundation Contract — Stage 00 |
| FT-00.03 | [#21](https://github.com/Sandsy09/forge-template/issues/21), [scope](../../../foundation-scope.md), and [ADR 0012](../../../adr/0012-conservative-foundation-scope.md) | Complete | [#11](https://github.com/Sandsy09/forge-template/issues/11) | [#20](https://github.com/Sandsy09/forge-template/issues/20) (complete) | Foundation Contract — Stage 00 |
| FT-00.04 | [#22](https://github.com/Sandsy09/forge-template/issues/22), [policy](../../../python-support.md), and [ADR 0013](../../../adr/0013-python-support-policy.md) | Complete | [#11](https://github.com/Sandsy09/forge-template/issues/11) | — | Foundation Contract — Stage 00 |
| FT-00.05 | ADR process and closed [#3](https://github.com/Sandsy09/forge-template/issues/3) | Complete before roadmap | — | — | — |
| FT-01.01 | Existing `src/{{ package_name }}` and smoke-test scaffold | Complete before roadmap | — | — | — |
| FT-01.02 | Existing generated `pyproject.toml` contract | Complete before roadmap | — | — | — |
| FT-01.03 | Existing `.python-version`, uv lock, and CI workflow | Complete before roadmap | — | — | — |
| FT-01.04 | Existing generated hygiene files | Complete before roadmap | — | — | — |
| FT-01.05 | Existing generated root documentation | Complete before roadmap | — | — | — |
| FT-EPIC-02 | [#12](https://github.com/Sandsy09/forge-template/issues/12) and [Stage 02 record](../../roadmap/02-developer-experience/README.md) | Complete | — | — | Foundation Baseline — Stages 01–03 |
| FT-02.01 | Existing Poe task and command contract | Complete before roadmap | — | — | — |
| FT-02.02 | Existing generated setup and first-check workflow | Complete before roadmap | — | — | — |
| FT-02.03 | Existing Poe orchestration and justified `verify-ci.sh` helper | Complete before roadmap | — | — | — |
| FT-02.04 | [#23](https://github.com/Sandsy09/forge-template/issues/23), [strategy](../../../editor-integration.md), and [ADR 0014](../../../adr/0014-editor-neutral-foundation.md) | Complete | [#12](https://github.com/Sandsy09/forge-template/issues/12) | — | Foundation Baseline — Stages 01–03 |
| FT-03.01 | Existing Ruff lint and format configuration | Complete before roadmap | — | — | — |
| FT-03.02 | Existing pytest baseline and smoke test | Complete before roadmap | — | — | — |
| FT-03.03 | Existing typing choices and ADR 0006 | Complete before roadmap | — | — | — |
| FT-03.04 | Existing generated pre-commit gate | Complete before roadmap | — | — | — |
| FT-03.05 | Existing generated and template-repository CI | Complete before roadmap | — | — | — |
| FT-03.06 | Existing coverage reporting and configurable threshold | Complete before roadmap | — | — | — |
| FT-EPIC-04 | [#13](https://github.com/Sandsy09/forge-template/issues/13) | Complete | — | — | Runtime & Security — Stages 04–05 |
| FT-04.01 | [#24](https://github.com/Sandsy09/forge-template/issues/24), [conventions](../../../configuration-ownership.md), and [ADR 0015](../../../adr/0015-owner-local-runtime-configuration.md) | Complete | [#13](https://github.com/Sandsy09/forge-template/issues/13) | [#21](https://github.com/Sandsy09/forge-template/issues/21) (complete) | Runtime & Security — Stages 04–05 |
| FT-04.02 | [#25](https://github.com/Sandsy09/forge-template/issues/25), [conventions](../../../environment-variables.md), and [ADR 0016](../../../adr/0016-owner-local-environment-inputs.md) | Complete | [#13](https://github.com/Sandsy09/forge-template/issues/13) | [#24](https://github.com/Sandsy09/forge-template/issues/24) (complete) | Runtime & Security — Stages 04–05 |
| FT-04.03 | [#26](https://github.com/Sandsy09/forge-template/issues/26), [contract](../../../structured-logging.md), and [ADR 0017](../../../adr/0017-owner-local-structured-logging.md) | Complete | [#13](https://github.com/Sandsy09/forge-template/issues/13) | [#21](https://github.com/Sandsy09/forge-template/issues/21) (complete) | Runtime & Security — Stages 04–05 |
| FT-04.04 | [#27](https://github.com/Sandsy09/forge-template/issues/27), [contract](../../../paths-and-resources.md), and [ADR 0018](../../../adr/0018-owner-local-paths-and-resources.md) | Complete | [#13](https://github.com/Sandsy09/forge-template/issues/13) | [#21](https://github.com/Sandsy09/forge-template/issues/21) (complete) | Runtime & Security — Stages 04–05 |
| FT-04.05 | [#28](https://github.com/Sandsy09/forge-template/issues/28), [conventions](../../../exception-ownership.md), and [ADR 0019](../../../adr/0019-owner-local-exceptions.md) | Complete | [#13](https://github.com/Sandsy09/forge-template/issues/13) | [#21](https://github.com/Sandsy09/forge-template/issues/21) (complete) | Runtime & Security — Stages 04–05 |
| FT-EPIC-05 | [#14](https://github.com/Sandsy09/forge-template/issues/14) | Open | — | — | Runtime & Security — Stages 04–05 |
| FT-05.01 | Existing Renovate/Dependabot/none template choices | Complete before roadmap | — | — | — |
| FT-05.02 | Existing explicit least-privilege workflow permissions | Complete before roadmap | — | — | — |
| FT-05.03 | [#29](https://github.com/Sandsy09/forge-template/issues/29) | Open | [#14](https://github.com/Sandsy09/forge-template/issues/14) | — | Runtime & Security — Stages 04–05 |
| FT-05.04 | [#30](https://github.com/Sandsy09/forge-template/issues/30), [contract](../../../secret-handling.md), and [ADR 0020](../../../adr/0020-generated-project-secret-safeguards.md) | Complete | [#14](https://github.com/Sandsy09/forge-template/issues/14) | — | Runtime & Security — Stages 04–05 |
| FT-05.05 | [#31](https://github.com/Sandsy09/forge-template/issues/31), [contract](../../../supply-chain-provenance.md), and [ADR 0021](../../../adr/0021-defer-sbom-and-release-provenance.md) | Complete | [#14](https://github.com/Sandsy09/forge-template/issues/14) | — | Runtime & Security — Stages 04–05 |
| FT-EPIC-06 | [#15](https://github.com/Sandsy09/forge-template/issues/15) | Open | — | — | Composition Contract — Stage 06 |
| FT-06.01 | [#32](https://github.com/Sandsy09/forge-template/issues/32) | Open | [#15](https://github.com/Sandsy09/forge-template/issues/15) | [create-forge#41](https://github.com/Sandsy09/create-forge/issues/41) (complete) | Composition Contract — Stage 06 |
| FT-06.02 | [#33](https://github.com/Sandsy09/forge-template/issues/33) | Open | [#15](https://github.com/Sandsy09/forge-template/issues/15) | [create-forge#41](https://github.com/Sandsy09/create-forge/issues/41) (complete) | Composition Contract — Stage 06 |
| FT-06.03 | [#34](https://github.com/Sandsy09/forge-template/issues/34) | Blocked | [#15](https://github.com/Sandsy09/forge-template/issues/15) | [#32](https://github.com/Sandsy09/forge-template/issues/32), [#33](https://github.com/Sandsy09/forge-template/issues/33) | Composition Contract — Stage 06 |
| FT-06.04 | [#35](https://github.com/Sandsy09/forge-template/issues/35) | Blocked | [#15](https://github.com/Sandsy09/forge-template/issues/15) | [#33](https://github.com/Sandsy09/forge-template/issues/33), [#34](https://github.com/Sandsy09/forge-template/issues/34) | Composition Contract — Stage 06 |
| FT-06.05 | [#36](https://github.com/Sandsy09/forge-template/issues/36) | Blocked | [#15](https://github.com/Sandsy09/forge-template/issues/15) | [#32](https://github.com/Sandsy09/forge-template/issues/32), [#33](https://github.com/Sandsy09/forge-template/issues/33) | Composition Contract — Stage 06 |
| FT-06.06 | [#37](https://github.com/Sandsy09/forge-template/issues/37) | Blocked | [#15](https://github.com/Sandsy09/forge-template/issues/15) | [#34](https://github.com/Sandsy09/forge-template/issues/34), [#35](https://github.com/Sandsy09/forge-template/issues/35), [#36](https://github.com/Sandsy09/forge-template/issues/36) | Composition Contract — Stage 06 |
| FT-06.07 | [#38](https://github.com/Sandsy09/forge-template/issues/38) | Blocked | [#15](https://github.com/Sandsy09/forge-template/issues/15) | [#32](https://github.com/Sandsy09/forge-template/issues/32)–[#37](https://github.com/Sandsy09/forge-template/issues/37) | Composition Contract — Stage 06 |
| FT-EPIC-07 | [#16](https://github.com/Sandsy09/forge-template/issues/16) | Blocked | — | — | CLI Scaffolding — Stage 07 |
| FT-07.05 | [#39](https://github.com/Sandsy09/forge-template/issues/39) | Blocked | [#16](https://github.com/Sandsy09/forge-template/issues/16) | [#38](https://github.com/Sandsy09/forge-template/issues/38) | CLI Scaffolding — Stage 07 |
| FT-EPIC-08 | [#17](https://github.com/Sandsy09/forge-template/issues/17) | Blocked | — | — | Reference Archetypes — Stage 08 |
| FT-08.01 | [#40](https://github.com/Sandsy09/forge-template/issues/40) | Blocked | [#17](https://github.com/Sandsy09/forge-template/issues/17) | [#38](https://github.com/Sandsy09/forge-template/issues/38) | Reference Archetypes — Stage 08 |
| FT-08.02 | [#41](https://github.com/Sandsy09/forge-template/issues/41) | Blocked | [#17](https://github.com/Sandsy09/forge-template/issues/17) | [#40](https://github.com/Sandsy09/forge-template/issues/40), [#38](https://github.com/Sandsy09/forge-template/issues/38) | Reference Archetypes — Stage 08 |
| FT-08.03 | [#42](https://github.com/Sandsy09/forge-template/issues/42) | Blocked | [#17](https://github.com/Sandsy09/forge-template/issues/17) | [#38](https://github.com/Sandsy09/forge-template/issues/38) | Reference Archetypes — Stage 08 |
| FT-08.04 | Repurposed [#4](https://github.com/Sandsy09/forge-template/issues/4) | Blocked | [#17](https://github.com/Sandsy09/forge-template/issues/17) | [#41](https://github.com/Sandsy09/forge-template/issues/41), [#42](https://github.com/Sandsy09/forge-template/issues/42) | Reference Archetypes — Stage 08 |
| FT-08.05 | [#43](https://github.com/Sandsy09/forge-template/issues/43) | Blocked | [#17](https://github.com/Sandsy09/forge-template/issues/17) | [#41](https://github.com/Sandsy09/forge-template/issues/41), [#4](https://github.com/Sandsy09/forge-template/issues/4), [create-forge#52](https://github.com/Sandsy09/create-forge/issues/52) | Reference Archetypes — Stage 08 |
| FT-EPIC-09 | [#18](https://github.com/Sandsy09/forge-template/issues/18) | Blocked | — | — | Blueprint Compatibility — Stage 09 |
| FT-09.01 | [#44](https://github.com/Sandsy09/forge-template/issues/44) | Blocked | [#18](https://github.com/Sandsy09/forge-template/issues/18) | [#38](https://github.com/Sandsy09/forge-template/issues/38) | Blueprint Compatibility — Stage 09 |
| FT-09.02 | [#45](https://github.com/Sandsy09/forge-template/issues/45) | Blocked | [#18](https://github.com/Sandsy09/forge-template/issues/18) | [#35](https://github.com/Sandsy09/forge-template/issues/35), [#38](https://github.com/Sandsy09/forge-template/issues/38) | Blueprint Compatibility — Stage 09 |
| FT-09.03 | [#46](https://github.com/Sandsy09/forge-template/issues/46) | Blocked | [#18](https://github.com/Sandsy09/forge-template/issues/18) | [#44](https://github.com/Sandsy09/forge-template/issues/44), [#45](https://github.com/Sandsy09/forge-template/issues/45) | Blueprint Compatibility — Stage 09 |
| FT-09.04 | [#47](https://github.com/Sandsy09/forge-template/issues/47) | Blocked | [#18](https://github.com/Sandsy09/forge-template/issues/18) | [create-forge#41](https://github.com/Sandsy09/create-forge/issues/41) (complete), [#38](https://github.com/Sandsy09/forge-template/issues/38) | Blueprint Compatibility — Stage 09 |
| FT-09.05 | [#48](https://github.com/Sandsy09/forge-template/issues/48) | Blocked | [#18](https://github.com/Sandsy09/forge-template/issues/18) | [#46](https://github.com/Sandsy09/forge-template/issues/46), [#47](https://github.com/Sandsy09/forge-template/issues/47) | Blueprint Compatibility — Stage 09 |

## Standalone backlog

Issues [#1](https://github.com/Sandsy09/forge-template/issues/1),
[#6](https://github.com/Sandsy09/forge-template/issues/6),
[#7](https://github.com/Sandsy09/forge-template/issues/7), and
[#8](https://github.com/Sandsy09/forge-template/issues/8) remain outside the
roadmap epics. Issues #1, #6, and #7 are explicitly deferred; #8 remains an
independent packaging bug.
