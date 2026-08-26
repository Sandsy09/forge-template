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

The canonical
[configuration ownership conventions](../configuration-ownership.md) define
how runtime-owning archetypes and capabilities expose, assemble, and inject
typed settings without adding a Foundation runtime module.

The canonical
[environment-variable conventions](../environment-variables.md) define
owner-prefixed runtime inputs, deterministic source precedence, and explicit
local dotenv behaviour for the owners that need it.

The canonical
[structured logging capability](../structured-logging.md) defines owner-local
event vocabularies, one entrypoint-owned process configuration, a portable
event envelope, and redaction boundaries without adding Foundation runtime
code.

The canonical
[path and resource ownership conventions](../paths-and-resources.md) keep
runtime path and resource access owner-local, forbid implicit process context
such as the current working directory or a discovered project root, and route
packaged reads through `importlib.resources` without adding a Foundation path
helper.

The canonical
[exception ownership conventions](../exception-ownership.md) keep exceptions
owner-local, require a failure to be handled, re-raised, or translated exactly
once, and assign translation of an escaped failure into a process outcome to
the runtime entrypoint, without adding a Foundation base exception.

The canonical
[secret-handling safeguards](../secret-handling.md) broaden the neutral
ignore rules Foundation already applies to `.env`, enforce a placeholder-only
tracked `.env.example`, and define the properties an optional secret-scanning
capability must have without generating one.

The canonical
[supply-chain provenance contract](../supply-chain-provenance.md) defines
desired SBOM behaviour and provenance/signing considerations for a future
capability and GitHub platform contribution, deferred until a generated-project
release/publish path and Stage 06 composition mechanics both exist.

The canonical
[GitHub Action pinning policy](../github-action-pinning.md) requires immutable
remote references in repository-owned and generated workflows while retaining
reviewed Renovate, Dependabot, and manual maintenance paths.

The canonical [ProjectSpec protocol](../project-spec.md) defines strict JSON
protocol v1 for effective generation requests, including provider-neutral
metadata, Python support, component selections, provenance, and namespaced
options.

The public engine/ProjectSpec model is the accepted target under
[create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md).
ProjectSpec protocol v1 is implemented, but discovery, composition, rendering,
the stable engine facade, and CLI consumption are not; the existing Copier
baseline remains operational until Stages 06–09 deliver the coordinated
cutover.

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
