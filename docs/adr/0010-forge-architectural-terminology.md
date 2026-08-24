# 10. Canonical Forge architectural terminology

## Status

Accepted

## Context

The Forge Foundation roadmap uses terms including Foundation, archetype,
capability, platform, profile, organisation policy, component, and ProjectSpec.
Without normative definitions, later issues could give those terms conflicting
meanings or accidentally treat every concept as an unrestricted rendering
overlay.

The current v0.1.x implementation is still a monolithic Library Copier
template consumed by a thin `create-forge` client. The public ProjectSpec and
component-engine model is proposed rather than implemented, and remains gated
by [create-forge#41](https://github.com/Sandsy09/create-forge/issues/41).
Terminology therefore needs to guide future decisions without presenting the
proposal as an existing API.

## Decision

Adopt [the Forge architectural terminology reference](../terminology.md) as
the canonical vocabulary shared by Forge and future Blueprint integrations.

Foundation is the mandatory baseline whose guarantees cannot be weakened.
Every project composes exactly one archetype over Foundation, may add zero or
more capabilities, and may add platform integration. Archetypes, capabilities,
and platforms are content-producing component kinds in the proposed model, but
they may only contribute owned content or use explicit extension points.
Implicit last-write-wins replacement is forbidden.

Profiles and organisation policies are selection inputs, not rendering
components. A profile supplies non-enforcing defaults. Organisation policy
supplies defaults plus required and forbidden constraints. Authority resolves
from profile defaults, to organisation-policy defaults, to explicit user
choices, to required or forbidden organisation constraints. None may weaken
Foundation guarantees.

Use `Forge` for the open-source generation ecosystem, `Blueprint` for a future
organisation-facing downstream policy consumer, and `generated project` for
the independent output that needs neither Forge repository at development or
runtime. Treat Component and ProjectSpec as gated proposal terms until the
architecture gate and Stage 06 define their implementation contracts.

The living reference may gain examples or clarifications that preserve these
semantics. A semantic change requires a new ADR that supersedes this one.

## Consequences

- Both repositories and future downstream integrations have one vocabulary to
  link to instead of maintaining copies.
- Stage 06 composition work starts with explicit authority boundaries and may
  not implement accidental last-write-wins behaviour.
- Stage 09 can design policy schemas and extension mechanics without reopening
  what policy means or turning it into an arbitrary file overlay.
- Existing Library behaviour, Copier data, schemas, and public APIs do not
  change as a result of this decision.
- The second reference archetype remains unnamed, and the public engine remains
  gated by create-forge#41.
