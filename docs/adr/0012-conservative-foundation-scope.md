# 12. Keep Forge Foundation conservative and runtime-free

## Status

Accepted

## Context

The canonical terminology defines Foundation as the mandatory baseline under
every archetype, and ADR 0011 defines the outcomes that baseline guarantees.
Neither decision establishes what additional repository concerns may be placed
in Foundation. Without an explicit boundary, generally useful Python
conventions could accumulate there simply because they are cross-cutting.

The current Library scaffold is monolithic and emits quality tooling, packaging
configuration, root documentation, GitHub integrations, optional documentation
and changelog behaviour, an environment example, and repository hygiene from
one template. Treating every current file or convention as Foundation would
freeze that implementation, force Library-specific and provider-specific
choices on future archetypes, and risk creating a shared generated runtime
framework.

At the same time, restricting Foundation only to the guarantees would leave no
owner for universal neutral handoff material and the state required for safe
template maintenance.

## Decision

Adopt [the Forge Foundation scope](../foundation-scope.md) as the canonical
living boundary.

A concern belongs in Foundation only when it is mandatory for every archetype,
is necessary for a Foundation guarantee, neutral independent handoff, or safe
Forge update/provenance behaviour, and also satisfies the documented
universality, neutrality, runtime-free, stability, and testability conditions.
Use the removal test: a concern is not foundational when omitting it would
preserve every guarantee, a complete independent handoff, and safe universal
update/provenance behaviour.

Foundation owns neutral project identity and metadata, licensing, root
guidance, security guidance, repository hygiene, and update/provenance state in
addition to the mandatory guarantee outcomes. It owns concerns rather than
whole files; later composition may place Foundation and component contributions
in the same generated file through explicit extension points.

Foundation supplies no generated configuration module, logging package,
resource helper, base exception, application framework, or other shared
runtime layer. The archetype or capability contributing runtime behaviour owns
those conventions and dependencies. Foundation may retain neutral safeguards,
such as ignoring common secret-bearing local files, without owning environment
schemas or examples.

Route primary project shape to an archetype, optional reusable concerns to
capabilities, and external-provider integrations to platforms. Profiles and
organisation policies remain selection inputs rather than content owners. A
disputed concern stays outside Foundation unless its proposer demonstrates
every inclusion condition; semantic changes require a superseding ADR.

Treat the current Library mapping as conceptual. This decision moves no file,
changes no Copier question or generated output, and introduces no ProjectSpec,
component manifest, engine API, or runtime package.

## Consequences

- Foundation cannot become a collection of generally useful Python defaults or
  a runtime framework shared by generated projects.
- Existing Library concerns such as packaging and versioning map to its
  archetype; coverage, pre-commit feedback, documentation, changelog support,
  dependency updates, and configuration examples map to capabilities; and
  GitHub-specific files map to a platform.
- A future default profile may preserve today's opinionated generated
  experience without making every selected concern foundational.
- Mixed generated files require concern-level ownership and explicit Stage 06
  composition rules rather than whole-file labels or implicit overwrite.
- Stage 04 can define owner-specific runtime conventions without adding a
  universal Foundation module.
- The exact Python policy, composition mechanics, integration architecture, and
  second archetype remain with their existing roadmap decisions.
