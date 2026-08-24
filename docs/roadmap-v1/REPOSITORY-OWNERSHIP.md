# Repository Ownership and Integration Model

> **Status:** Template/CLI ownership is current; ProjectSpec, component,
> composition-engine, and downstream-policy ownership is proposed. Those
> additions remain gated by
> [create-forge#41](https://github.com/Sandsy09/create-forge/issues/41).

The [canonical terminology](../terminology.md) defines the component kinds and
selection inputs referenced by this ownership model. The
[Foundation scope](../foundation-scope.md) defines the concern-level boundary
between that mandatory baseline and the components listed below. The
[Python support policy](../python-support.md) is owned here because its choices,
generated metadata, and validation are part of generated-project behaviour.

## `forge-template`

Owns **what a generated project is** and **how it is composed**.

It owns:

- Foundation and archetype templates;
- capability and platform components;
- profile and organisation-policy selection inputs;
- component manifests and compatibility metadata;
- the canonical ProjectSpec input contract;
- template variables and validation;
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
