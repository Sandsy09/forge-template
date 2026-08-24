# 11. Outcome-based Forge Foundation guarantees

## Status

Accepted

## Context

The canonical Forge terminology defines Foundation as the mandatory baseline
contract every generated project receives and says later layers cannot weaken
its guarantees. It deliberately left the guarantees themselves to FT-00.01.

The current v0.1.x Library scaffold already provides uv locking, static type
checking, pytest, Ruff, Poe tasks, pre-commit hooks, and GitHub Actions. Making
those exact tools the architectural contract would conflate an implementation
with the outcomes it exists to provide, constrain future archetypes, and make a
platform-specific workflow part of Foundation despite the agreed component
boundaries.

The contract also needs a precise limit. A committed lock can make dependency
selection repeatable from declared inputs, but the current project does not
claim bit-for-bit reproducible artifacts, offline installation, or universal
operating-system support.

## Decision

Adopt [the Forge Foundation guarantees](../foundation-guarantees.md) as the
canonical living contract for every successfully generated Forge project.

Define guarantees as mandatory outcomes rather than permanent tool choices.
Foundation guarantees a reproducible development and validation environment,
committed dependency lock state with drift detection, static type checking,
automated testing, linting, deterministic formatting, a provider-neutral CI
contract, and independence from Forge during normal project operation.

Reproducibility means that committed metadata and lock state restore dependency
selection and validation behaviour in a clean supported environment with
documented prerequisites. It does not mean byte-identical output or offline
operation. A Library project's development lock does not override the
compatible dependency ranges offered to its consumers.

Treat uv, Poe, Ruff, pytest, mypy or pyright, pre-commit, and GitHub Actions as
the current Library implementation of those outcomes. They may be replaced if
the replacement preserves the contract. A CI platform integration must execute
the same underlying quality concerns used locally rather than introduce a
separate standard.

The guarantees constrain output produced by Forge and future compositions.
They do not prevent a project owner from changing an independent generated
repository after handoff, and they do not install an enforcement runtime into
that repository. Template updates may use Copier and the template source, but
normal development, testing, building, and runtime operation may not depend on
either Forge repository or package.

Semantic changes to these outcomes require a new ADR that supersedes this one.
The living reference may gain mappings or clarifications that preserve the
decision.

## Consequences

- Future archetypes, capabilities, platforms, profiles, and organisation
  policies may strengthen Foundation but may not remove its quality gates.
- Forge can change implementation tools without redefining Foundation, as long
  as replacement behaviour preserves every mandatory outcome.
- Coverage thresholds, typing strictness, expanded test matrices, offline
  operation, and byte-reproducible artifacts remain optional strengthening or
  future work rather than unsupported implied promises.
- FT-00.03 still decides what concerns belong in Foundation, FT-00.04 still
  decides Python support policy, and Stage 06 still owns composition
  enforcement.
- Existing Library output, Copier answers, schemas, APIs, and runtime behaviour
  do not change as a result of this documentation decision.
