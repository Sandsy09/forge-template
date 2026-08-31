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
capability and GitHub platform contribution. Stage 06 now supplies the
composition mechanics; implementation remains deferred until the contract's
other exit criteria, including a generated-project release/publish path, hold.

The canonical
[GitHub Action pinning policy](../github-action-pinning.md) requires immutable
remote references in repository-owned and generated workflows while retaining
reviewed Renovate, Dependabot, and manual maintenance paths.

The canonical [ProjectSpec protocol](../project-spec.md) defines strict JSON
protocol v1 for effective generation requests, including provider-neutral
metadata, Python support, component selections, provenance, and namespaced
options.

The canonical
[organisation policy protocol](../organisation-policy.md) defines strict JSON
protocol v1 for downstream component-selection defaults and constraints,
including order-independent multi-policy conflict and future structured
failure semantics. Executable resolution remains later Stage 09 work. The
canonical [safe override and extension points](../extension-points.md)
contract, delivered by FT-09.02, publishes the complete sanctioned extension
surface and denies the `override` grant [file-conflicts.md](../file-conflicts.md)
reserved, closing the route to arbitrary file replacement a downstream
Blueprint-style client might otherwise reach for.

The canonical [Library archetype contract](../library-archetype.md) defines
the distributable-package additions composed over one implicit Foundation
source, implemented by FT-08.02. The canonical
[CLI Application archetype contract](../cli-application-archetype.md) defines
the optionless `cli` executable shape's package, dependency, command, and
Foundation-extension requirements, implemented by FT-08.04.

The canonical
[component manifest protocol](../component-manifests.md) defines strict TOML
protocols v1/v2 for bundled component identity, compatibility, owned content,
Foundation/component contribution targets, dependencies, and conflicts. Both
production manifests, Library and CLI, implement protocol 2.

The canonical [composition order contract](../composition-order.md) defines
the single deterministic tier and within-tier order a validated component
selection applies in, cross-tier dependency handling, and catalogue-wide
cycle rejection.

The canonical [file conflict and override rules](../file-conflicts.md) define
the output target each owned content path produces, the create/extend
dispositions protocol v1 grants, and the collision-safety rules an
unsupported target clash must fail under.

The canonical [template variable contract](../template-variables.md) defines
the rendered variable namespace a template author reads, the option-schema
format a component declares its own options through, and the
required/unknown-option rejection rules that resolution enforces before any
file operation.

The canonical [stable template-engine API](../template-engine-api.md) exposes
those contracts through typed, package-bound discovery, strict validation,
deterministic planning, in-memory rendering, and structured failures. Its
production catalogue held nothing before Stage 08; FT-08.02 populated it
with the Library archetype and FT-08.04 added the CLI Application archetype
beside it, so `discover_components()` now returns both.

The canonical
[generated-project validation contract](../generated-project-validation.md)
ensures each in-memory render exactly matches its plan, carries universal
ProjectSpec-aligned metadata, and contains no unresolved Forge extension
marker before a client receives it.

The public engine/ProjectSpec model is the accepted target under
[create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md).
ProjectSpec, component manifest protocols v1/v2, composition order, file
conflict and override rules, the template variable contract, the stable
`forge-template` `0.3.x` engine facade, and generated-project validation are
implemented, and FT-08.02 and FT-08.04 populated the production catalogue
with the Library and CLI Application archetypes' manifests, Foundation
source, and (for Library) option schema. `forge-template` released this
catalogue at `v0.3.0`; released `create-forge` consumes the compatible
`forge-template>=0.3.1,<0.4` range behind `--engine-preview`, while the
existing Copier baseline remains operational until a coordinated cutover.
The [Stage 08 composition review](../composition-architecture-review.md)
corrects the shared Foundation boundary in `forge-template` `0.3.2`;
`create-forge 0.2.1` implements dynamic lock finalisation without changing the
engine facade or protocols. Stage 08 is complete across both repositories.

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
