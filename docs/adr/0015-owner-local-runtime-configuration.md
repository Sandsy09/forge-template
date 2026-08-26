# 15. Keep runtime configuration owner-local and explicitly injected

## Status

Accepted

## Context

ADR 0012 keeps Foundation runtime-free and assigns configuration to the
archetype or capability contributing the behaviour that consumes it. That
boundary prevents a universal settings package, but it does not yet tell
independent runtime owners how to expose configuration, how a generated
project assembles multiple owners, or how schemas and defaults stay separate
from secret values.

A fixed global module would make configuration-light projects carry unused
runtime structure and would allow later capabilities to compete for one
implicit namespace. Independent loaders or import-time environment reads would
also make validation order, testing, and cross-owner dependencies difficult to
reason about. Stage 06 will define component metadata and composition
mechanics, but it needs a generated-project convention to target.

The current Library scaffold has no configuration module or settings runtime
dependency. Its inert `.env.example` placeholder is not consumed by generated
code and therefore does not itself create a runtime configuration contract.

## Decision

Adopt the
[configuration ownership and extension conventions](../configuration-ownership.md)
as the canonical living contract.

The archetype or capability contributing configurable runtime behaviour owns
a stable, documented, typed configuration fragment for that behaviour. Forge
does not prescribe the fragment's module path, object name, validation
library, loader, or serialization format. Owners that need no runtime
configuration omit it entirely.

The owner of a generated project's runtime entrypoint validates and assembles
the selected owner fragments once at startup and injects each fragment
explicitly. An entrypoint-owned aggregate may group fragments without taking
ownership of them. Import-time environment reads, mutable global configuration
singletons, implicit process-wide dictionaries, and service locators are not
the Forge convention.

Cross-owner configuration access uses the provider's documented public
interface and explicit injection. An owner cannot reopen another owner's
schema or defaults, and unsupported ownership collisions fail rather than
using implicit last-write-wins replacement. Stage 06 remains responsible for
manifest declarations, extension-point representation, ordering,
compatibility, and collision algorithms.

Owners may version schemas, validation rules, documentation, safe
placeholders, and non-sensitive defaults with the project. Secret values are
runtime inputs and must not be committed, generated into source or defaults,
placed in examples, or exposed by diagnostics. FT-04.02 owns environment
sources and naming, while FT-04.05 owns exception and wrapping conventions.

This decision changes no current template file, Copier answer, generated
output, schema, ProjectSpec, public engine API, or runtime dependency.

## Consequences

- Configuration-light libraries remain first-class generated outcomes rather
  than receiving empty runtime infrastructure.
- Multiple runtime owners can coexist without sharing an untyped global
  namespace or silently replacing one another's settings.
- Startup assembly has one explicit validation boundary, while consuming code
  receives only the typed fragment it needs and is easier to test.
- Component authors must document their public configuration surface and
  secret-bearing inputs, but retain freedom to select appropriate
  implementation tools.
- Stage 04 can define environment, logging, resource, and exception conventions
  against explicit owners without turning Foundation into a runtime framework.
- Stage 06 must represent owner dependencies and conflicts without weakening
  these boundaries.
- The current Library scaffold and its inert `.env.example` remain unchanged
  until later roadmap work assigns and migrates their component ownership.
