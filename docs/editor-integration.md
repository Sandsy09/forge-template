# Forge Editor Integration Strategy

This document defines how editor-specific integration fits into Forge without
making an editor part of the generated-project contract. It complements the
[Foundation guarantees](foundation-guarantees.md),
[Foundation scope](foundation-scope.md), and
[canonical terminology](terminology.md).

This is an ownership and policy decision only. It introduces no editor
selection, component manifest, ProjectSpec field, prompt, serialised answer,
template output, or migration.

## Editor-neutral Foundation

Foundation remains editor-neutral. Its text and repository conventions must
work across editors and without one:

- `.editorconfig` remains Foundation repository hygiene because it expresses
  vendor-neutral text conventions. It is not an IDE integration.
- `pyproject.toml`, Poe tasks, pre-commit, and the provider-neutral project
  commands remain authoritative for formatting, linting, typing, testing, and
  builds.
- `uv run poe check`, the selected type checker, and the test suite must work
  without editor-specific files, extensions, or workstation state.
- Foundation generates no `.vscode`, `.idea`, workspace, extension, or other
  vendor-specific configuration.

Forge's default profile remains neutral too. When profiles and composition
exist, the default profile will not select an editor capability. A generated
project therefore requires no editor choice and receives no editor-specific
files merely by accepting Forge defaults.

Foundation does not add blanket `.vscode/` or `.idea/` ignore rules. A future
capability may intentionally version selected team-safe files in one of those
paths, so ownership must be precise rather than hidden by a global ignore.

## Optional editor capabilities

Each editor family may be represented by an independent optional capability
when the composition engine exists. A project may select zero or more editor
capabilities. This decision selects no editor, defines no capability
identifier, and creates no adapter implementation commitment.

A named profile or an organisation profile may provide overridable defaults
that include editor capabilities. Those defaults retain normal profile
authority: an explicit user choice may replace them, subject to organisation
policy. Profiles select capabilities; they do not own or render the
editor-specific files themselves.

Capability identifiers, manifests, ProjectSpec fields, ordering, extension
points, and collision mechanics are now defined by
[component-manifests.md](component-manifests.md),
[composition-order.md](composition-order.md), and
[file-conflicts.md](file-conflicts.md); discovery and a stable rendering API
remain Stage 06 work (FT-06.07). Until those contracts exist, editor-specific
files are not added to the generated scaffold.

## Permitted contributions

A future editor capability may provide only a thin, project-scoped bridge to
the project's canonical commands and configuration. It may contribute:

- version-controlled, deterministic settings that are safe and useful for the
  whole project team;
- advisory extension recommendations that do not install software
  automatically;
- editor tasks or debug entries that delegate to existing project commands and
  tool configuration;
- documentation for the optional editor workflow; and
- precise ignore entries for user-local artifacts within paths owned by that
  capability.

An editor capability may not:

- duplicate, replace, or weaken lint, formatting, typing, testing, or build
  policy;
- introduce a competing developer-command workflow;
- add a generated runtime dependency solely to support an editor;
- commit credentials, absolute machine paths, user identity, caches, history,
  telemetry state, or other workstation-local data;
- make an editor necessary for project validation; or
- overwrite another component's content implicitly.

Multiple editor capabilities may coexist when their owned paths and declared
extension points do not collide. Unsupported collisions fail rather than
silently overwrite content, following the composition authority defined in
the [canonical terminology](terminology.md#composition-and-authority).

## Development environments are separate

Devcontainers, Codespaces, and other local or remote development environments
are outside this decision. They manage an execution environment rather than a
thin editor bridge and require a separate future decision about capability or
platform ownership. This strategy neither classifies nor commits Forge to
generating them.

## Current Library scaffold evidence

The v0.1.x Library scaffold is already editor-independent:

- `template/.editorconfig` supplies neutral line-ending, whitespace, charset,
  and indentation conventions;
- no vendor-specific editor directory, workspace, extension recommendation,
  or settings file is generated;
- generated `pyproject.toml` configuration and Poe commands can be invoked
  directly; and
- local validation, pre-commit, and GitHub Actions do not read or require
  editor configuration.

These facts are acceptance evidence for the current implementation. They do
not turn the present monolithic scaffold into a component engine or select a
future editor capability.

## Deferred decisions

[component-manifests.md](component-manifests.md),
[composition-order.md](composition-order.md),
[file-conflicts.md](file-conflicts.md), and
[template-variables.md](template-variables.md) now define the component,
composition, and variable mechanics an editor capability would declare
through; only a stable discovery and rendering API (FT-06.07) remains open.
A later proposal may define a concrete adapter only after that remaining
contract exists and must identify its owned paths, extension points,
declared options, validation, and collision behaviour per
[file-conflicts.md](file-conflicts.md) and
[template-variables.md](template-variables.md). Any development-environment
integration requires its own classification decision.
