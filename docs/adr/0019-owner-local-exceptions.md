# 19. Keep exceptions owner-local and handle them once

## Status

Accepted

## Context

[ADR 0012](0012-conservative-foundation-scope.md) keeps Foundation
runtime-free, supplies no generated base exception, and assigns exception
conventions to Stage 04. [ADR 0015](0015-owner-local-runtime-configuration.md)
assigns owner-local typed interfaces to the archetype or capability consuming
them and requires the runtime entrypoint to assemble them once. [ADR
0017](0017-owner-local-structured-logging.md) defines structured logging's
redaction boundary but explicitly deferred catch, wrap, log-once, re-raise,
and duplicate-handling rules to this decision. [ADR
0018](0018-owner-local-paths-and-resources.md) similarly deferred the
exception types a path or resource owner raises on failure.

Neither extreme serves those boundaries well. A universal Foundation base
exception would recreate the runtime layer ADR 0012 rejects, and would force
every caller that wants to catch a project's own failures to import something
from Forge — a breach of the independent-operation guarantee that lets a
generated project run without a Forge dependency once installed. Leaving the
area completely undefined is not neutral either: without a shared convention,
generated code accumulates bare `except:` clauses that swallow
`KeyboardInterrupt`, wrapping that discards the original cause, and the same
failure logged once per stack frame as it propagates — exactly the kind of
inconsistency the structured-logging and configuration-ownership contracts
already avoid for their own concerns.

The current Library scaffold has almost no exception-handling behaviour: its
package defines no exception type, and its only handling is one narrow
`except PackageNotFoundError` around an `importlib.metadata.version` lookup
with a documented fallback. A decision can therefore define the future
generated-project contract without changing current output.

## Decision

Adopt the [exception ownership conventions](../exception-ownership.md) as the
canonical living contract.

The archetype or capability contributing runtime behaviour owns the failures
it raises. An owner defines its own base exception only when it raises more
than one owner-defined failure mode across a public API or callers need to
catch its whole surface at once; a single failure a standard-library exception
already states precisely needs no owner-defined type, and an empty base added
for uniformity is not justified. A defined base subclasses `Exception`, never
`BaseException`, and is part of the owner's public interface — catching it
never requires a Forge import.

Wrapping preserves the cause with `raise ... from exc`, reserving
`from None` for a deliberate, documented suppression; the generated project's
existing ruff `B` selection already enforces this as B904. Code catches only
what it can handle — bare `except:` and `except BaseException:` are invalid,
and `except Exception:` is reserved for a documented process or task boundary.
An exception is always handled, re-raised, or translated, never silently
discarded. The code that handles a failure without re-raising it logs that
failure exactly once, through the structured logging contract's redacted
representation; code that re-raises does not also log. The runtime entrypoint
is the one place that translates an escaped exception into a process outcome
and documents its own mapping, without a Forge-mandated exit-code table.
Exception messages identify what failed without echoing secret-bearing
values, mirroring the boundary already stated for environment and path
validation errors. A documented exception type and what raises it form part of
the owner's compatibility surface, evolved with the same discipline as a
documented logging event. Generated-project exceptions are a distinct surface
from the errors `forge-template`'s own engine raises during generation, which
remain owned by Stage 06.

This decision changes no current template file, Copier answer, generated
output, ProjectSpec, component manifest, runtime dependency, schema, public
API, or CLI behaviour.

## Consequences

- Runtime owners gain a predictable, portable way to define, wrap, catch, and
  log their own failures without a shared Foundation exception hierarchy.
- Callers can always catch a project's own failures without importing
  anything from Forge, preserving independent operation once installed.
- Duplicate log records for a single failure, and silently swallowed
  failures, become contract violations rather than an unaddressed grey area.
- The runtime entrypoint gains the same clear translation responsibility for
  escaped exceptions that ADR 0015 already gives it for configuration
  assembly.
- Component authors must document which exception types are part of their
  public surface and evolve them under the same compatibility discipline as a
  documented configuration field or logging event.
- Stage 06 retains composition and collision mechanics, along with the
  template engine's own distinct error surface.
- Stage 04's `forge-template`-owned runtime series is now complete: owner-local
  contracts exist for configuration, environment inputs, structured logging,
  paths and resources, and exceptions, with no Foundation runtime layer
  introduced by any of them.
- The current Library scaffold remains unchanged until later roadmap work
  selects and implements an owning component.
