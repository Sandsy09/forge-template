# 14. Keep Foundation and the default profile editor-neutral

## Status

Accepted

## Context

The current Library scaffold includes vendor-neutral `.editorconfig` text
conventions but no editor-specific settings. Its generated quality commands
work directly through project-owned configuration and do not depend on an
editor. Forge needs to preserve that portability while leaving room for teams
that want shared editor tasks, settings, or recommendations.

Putting vendor-specific files in Foundation would make a preference mandatory
for every project. Blanket ignores would create the opposite problem by
preventing future opt-in capabilities from tracking selected team-safe files.
The accepted composition model can eventually represent optional concerns,
but its component and ProjectSpec mechanics remain Stage 06 work.

## Decision

Adopt the [Forge editor integration strategy](../editor-integration.md) as the
canonical living contract.

Retain `.editorconfig` in Foundation as vendor-neutral repository hygiene.
Project-owned configuration, Poe tasks, pre-commit, and CI remain authoritative
for quality and build behaviour, and all required validation must work without
editor-specific files, extensions, or workstation state.

Foundation and Forge's default profile generate no vendor-specific editor
configuration. Do not add blanket editor-directory ignores to Foundation.

Model each future editor family as an independent optional capability. Named
or organisation profiles may provide overridable editor-capability defaults,
while projects may select zero or more capabilities. A capability may provide
only a thin, deterministic, project-scoped bridge to canonical commands and
configuration. It may not duplicate policy, create a competing workflow,
introduce editor-only runtime dependencies, commit workstation-local data,
make validation editor-dependent, or overwrite another component implicitly.

Select no concrete editor and file no adapter implementation issue as part of
this decision. Defer identifiers, manifests, ProjectSpec fields, discovery,
ordering, extension points, and collision mechanics to Stage 06. Treat
devcontainers, Codespaces, and other development environments as a separate
future classification decision.

## Consequences

- Generated projects remain portable across editors and usable without one.
- Teams may later opt into more than one editor bridge without changing
  Foundation or Forge's neutral defaults.
- Tracked editor settings must be deterministic, team-safe, and owned by their
  capability; user-local artifacts stay excluded precisely.
- Existing project commands and tool configuration remain the single source of
  truth for local and automated validation.
- Unsupported editor-component collisions will fail under the future Stage 06
  composition rules rather than resolve through implicit overwrites.
- This decision changes no template, Copier schema, generated output,
  ProjectSpec, application code, public API, or runtime behaviour.
