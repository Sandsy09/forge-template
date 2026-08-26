# Repository Ownership and Integration Model

> **Status:** Template/CLI ownership is current and ProjectSpec protocol v1 is
> now defined. Component discovery, composition/rendering, the stable engine
> facade, and downstream-policy integration remain the accepted target under
> [create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md),
> but remains unimplemented until the coordinated cutover.

The [canonical terminology](../terminology.md) defines the component kinds and
selection inputs referenced by this ownership model. The
[ProjectSpec protocol](../project-spec.md) defines their strict serialised
request and preserves the one-way client-to-engine boundary. The
[Foundation scope](../foundation-scope.md) defines the concern-level boundary
between that mandatory baseline and the components listed below. The
[Python support policy](../python-support.md) is owned here because its choices,
generated metadata, and validation are part of generated-project behaviour.
The [editor integration strategy](../editor-integration.md) assigns future
editor-specific bridges to optional `forge-template` capabilities while
keeping canonical commands independent of editor state.
The [configuration ownership conventions](../configuration-ownership.md)
define the generated-project runtime contract that future composition must
preserve without creating a Foundation settings module.
The [environment-variable conventions](../environment-variables.md) define
the owner-local names, precedence, examples, and local dotenv boundary that
environment-backed components must preserve.
The [structured logging capability](../structured-logging.md) defines the
generated runtime event and process-configuration contract; provider exporters
remain platform contributions.
The [path and resource ownership conventions](../paths-and-resources.md)
define the generated-project path and resource access contract that future
composition must preserve without creating a Foundation path helper.
The [exception ownership conventions](../exception-ownership.md) define the
generated-project exception contract that keeps failures owner-local,
catchable without a Forge import, and handled exactly once.
The [secret-handling safeguards](../secret-handling.md) define the neutral
ignore and pre-commit safeguards Foundation applies to secret-bearing files
and the boundary of the optional secret-scanning capability future
composition may add.
The [supply-chain provenance contract](../supply-chain-provenance.md) defines
the SBOM and release-provenance behaviour a future capability and GitHub
platform contribution must satisfy, and the exit criteria that must hold
before either is generated.
The [GitHub Action pinning policy](../github-action-pinning.md) defines how
this repository and its generated GitHub platform contributions consume and
maintain remote workflow dependencies.

## `forge-template`

Owns **what a generated project is** and **how it is composed**.

It owns:

- Foundation and archetype templates;
- capability and platform components;
- optional editor capabilities and their project-scoped contributions;
- profile and organisation-policy selection inputs;
- component manifests and compatibility metadata;
- the canonical ProjectSpec input contract;
- template variables and validation;
- owner-local runtime configuration, environment-input, structured-logging,
  path/resource ownership, exception ownership, and secret-handling
  safeguard conventions;
- GitHub platform workflow pins and their generated maintenance configuration;
- composition, merge/conflict and override rules;
- rendering/generation logic;
- structured engine errors and generated-project validation;
- deterministic generation tests.

It does **not** own interactive prompts, command-line parsing, terminal output or target-directory UX.

## `create-forge`

Owns **how a user describes and requests a project**.

It owns:

- CLI commands and flags;
- interactive prompts;
- user-facing validation and error presentation;
- construction of the canonical ProjectSpec;
- component discovery for CLI choices via the forge-template API;
- filesystem orchestration and safe target handling;
- CLI diagnostics/version reporting;
- end-to-end scaffolding tests.

It does **not** own copies of templates, a second component catalogue, compatibility rules, or rendering/composition logic.

## Dependency direction

```text
User
  ↓
create-forge
  ↓  ProjectSpec / public engine API
forge-template
  ↓
Generated repository
```

The preferred dependency is one-way: `create-forge` consumes `forge-template`. `forge-template` must not import or depend on `create-forge`.

## Cross-repository issue rule

If an issue is blocked by the other repository, link that external issue under **Cross-repository dependencies**. Do not create a second ticket that implements the same responsibility in both repositories.
