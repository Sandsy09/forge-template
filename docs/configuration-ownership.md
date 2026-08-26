# Configuration ownership and extension conventions

This is the canonical living contract for runtime configuration in generated
Forge projects. [ADR 0015](adr/0015-owner-local-runtime-configuration.md)
records why Forge adopted it.

The contract describes generated-project behaviour that future archetypes and
capabilities must preserve. It does not add a configuration API to the current
v0.1.x Library scaffold or define the future component-engine schema.

## Configuration has a runtime owner

Runtime configuration belongs to the archetype or capability that contributes
the behaviour consuming it. That owner defines the fields, validation,
non-sensitive defaults, public interface, documentation, and any runtime
dependency needed for its concern.

Foundation supplies no configuration module, schema, loader, registry,
singleton, service locator, or runtime dependency. A generally useful setting
does not become foundational merely because several components might need it.
Each owner either exposes its own setting or consumes another owner's
documented public interface explicitly.

An archetype or capability that needs no runtime configuration supplies none.
In particular, a configuration-light Library project is a complete outcome;
Forge does not add an empty settings object or dependency for uniformity.

## Owner-local public interface

Every configuration owner publishes a stable, typed interface for its
validated configuration fragment. Its user and contributor documentation must
identify:

- the owning archetype or capability and the behaviour being configured;
- the public import path or other supported access point;
- the fields, types, required values, and non-sensitive defaults;
- which inputs are secret-bearing and therefore require redaction; and
- how callers construct the fragment and pass it to the consuming behaviour.

The interface is stable in the same sense as the owner's other documented
public surfaces: callers do not need to import private implementation details.
Forge does not mandate a module path, class name, settings library, loader, or
serialization format. Those choices stay with the owner and may differ when
project shapes have genuinely different needs.

## Assemble once and inject explicitly

The owner of the generated project's runtime entrypoint coordinates
configuration assembly. At startup it validates the selected owners' inputs,
constructs one typed fragment per owner, and passes each fragment explicitly
to the behaviour that consumes it.

An entrypoint-owned aggregate may group those fragments for convenience, but
it does not take ownership of their fields. It must preserve the fragment
boundaries and cannot permit one owner to mutate another owner's schema or
defaults.

Configuration must not be discovered through import-time environment reads, a
mutable global singleton, an implicit process-wide dictionary, or a service
locator. Code that needs another owner's configuration receives that owner's
documented interface through an explicit parameter. A project with no runtime
entrypoint and no configuration owner performs no assembly.

## Extension between owners

An owner may extend only content it owns or a documented extension point.
When one component depends on configuration published by another:

1. the provider retains ownership of its typed fragment;
2. the consumer depends on the provider's public interface rather than copying
   or reopening its schema;
3. the runtime entrypoint passes the dependency explicitly; and
4. unsupported or ambiguous ownership collisions fail rather than using
   implicit last-write-wins replacement.

Stage 06 will define how component manifests declare such dependencies,
extension points, ordering, compatibility, and collision errors. This contract
defines the generated-project convention those mechanics must support; it does
not pre-empt their API.

## Defaults, schemas, and secrets

An owner may commit its configuration schema, validation rules,
non-sensitive defaults, safe placeholders, and explanatory documentation.
Secret values are runtime inputs. They must never be committed, embedded in
generated source or defaults, placed in examples, or exposed through
diagnostics and representations.

Environment-backed fragments follow the canonical
[environment-variable and local dotenv conventions](environment-variables.md),
which define owner-prefixed names, source precedence, safe examples, and
provider-neutral environment identity. Runtime owners that log follow the
[structured logging capability contract](structured-logging.md). Exception
types, wrapping, and log-once behaviour remain with
[FT-04.05](https://github.com/Sandsy09/forge-template/issues/28).

Profiles and organisation policies may select components or supply generation
defaults and constraints under the
[canonical authority rules](terminology.md#composition-and-authority). They do
not become runtime configuration owners or inject arbitrary secret values into
generated files.

## Current Library evidence

The v0.1.x Library scaffold remains configuration-light:

- its package `__init__.py` exposes version metadata and no configuration
  interface;
- its generated runtime dependencies contain no settings or configuration
  library;
- `.env.example` is an inert placeholder in the current monolithic scaffold,
  is not imported or read by generated code, and does not establish a Library
  runtime configuration contract; and
- `.env` is ignored by the neutral secret-file safeguard in `.gitignore`.

The canonical environment contract now assigns future example entries to
their runtime owners and targets conditional assembly into one root
`.env.example`. Later component migration remains responsible for changing the
current file. This decision does not move or remove it, add a Copier question,
or change generated output.

## Deferred decisions

This contract deliberately does not define:

- a settings library, fixed module path, class name, or wire format;
- exception hierarchies or log-once and wrapping behaviour;
- ProjectSpec fields, component manifests, dependency declarations, ordering,
  extension-point representation, or collision algorithms; or
- the identity or runtime shape of the second reference archetype.

Those decisions remain with their existing Stage 04, Stage 06, and Stage 08
roadmap issues.
