# Exception ownership conventions

This is the canonical living contract for exception handling in generated
Forge projects. It extends the
[configuration ownership conventions](configuration-ownership.md), which
assign runtime settings to the archetype or capability consuming them, and
completes the catch, wrap, log-once, and re-raise rules that the
[structured logging capability](structured-logging.md) deferred here. [ADR
0019](adr/0019-owner-local-exceptions.md) records why Forge adopted this
contract.

The contract describes generated-project behaviour that future archetypes and
capabilities must preserve. It does not add exception handling to the current
v0.1.x Library scaffold or define a ProjectSpec or component manifest field.

## Exceptions have a runtime owner

Foundation supplies no base exception, shared error hierarchy, error-code
registry, or runtime dependency. The archetype or capability contributing
runtime behaviour owns the failures it can raise, their names, their meanings,
and their documentation. A project that raises nothing of its own defines
nothing.

## When an owner defines its own base exception

An owner defines one package-level base exception when it raises more than one
owner-defined failure mode across a public API, or when callers reasonably
need to catch the owner's whole failure surface at once. A single narrow
failure that a standard-library exception already states precisely —
`ValueError`, `FileNotFoundError`, `KeyError`, and similar — needs no
owner-defined type. An empty base class added for uniformity, with no second
failure mode and no caller who needs it, is not justified by this contract.

An owner-defined base subclasses `Exception`, never `BaseException`: bypassing
`Exception` would let a caller's `except Exception:` boundary miss it, which
defeats the point of defining a catchable surface. A specific owner-defined
type may additionally inherit a standard-library exception where that
parentage genuinely describes the failure, for example a validation failure
that is also a `ValueError`.

The base and its documented subclasses are part of the owner's public
interface under [owner-local public interface](configuration-ownership.md#owner-local-public-interface).
Catching them must not require importing a private module, and must never
require importing anything from Forge itself.

## Domain and framework exceptions stay with their owner

A domain failure belongs to the domain owner, not to a shared or generic type.
A provider SDK's or framework's exception types stay behind the boundary of
the component that took that dependency; other owners do not need to import
that provider to handle the failure. An owner does not re-export another
library's exception as its own public surface, and does not force other
owners to depend on it merely to catch its failures.

## Wrapping preserves the cause

Wrapping one exception in another uses `raise OwnerError(...) from exc`, never
a bare `raise OwnerError(...)` that discards the original traceback and cause.
`raise ... from None` is reserved for a deliberate, documented suppression —
for example, when the original exception's detail would leak an implementation
the owner does not want to expose — not a default.

Wrap to add meaning at a boundary or to keep an internal implementation detail
out of a public failure type, not merely to rename an exception that already
says enough. The generated project's ruff configuration already selects `B`
(flake8-bugbear), whose **B904** rule enforces `raise ... from` at the linter
level; this contract states the same rule as the reason, not a new mechanism.

## Catch narrowly

Catch the specific exception type or types the surrounding code can actually
recover from or meaningfully translate. Bare `except:` and
`except BaseException:` are invalid: both swallow `KeyboardInterrupt` and
`SystemExit`, which must keep propagating.

`except Exception:` is permitted only at a documented process or task boundary
— the kind described in
[the runtime entrypoint translates escaped failures](#the-runtime-entrypoint-translates-escaped-failures)
below — that logs the failure once and translates it into a defined outcome,
never as a routine substitute for catching the specific type expected.

## Never fail silently

An exception is always handled, re-raised, or translated into a documented
outcome; it is never discarded. `except SomeSpecificError: pass` is valid only
with a narrow type, a documented reason the failure is safe to ignore, and a
correct continuation afterward. An empty `except Exception: pass` is never
valid under this contract.

## Log once, where the failure is handled

Code that raises or re-raises an exception does not also log it — that
produces duplicate records as the exception propagates through multiple
frames. The code that handles a failure without re-raising it is the code that
logs it, exactly once, using the
[structured logging capability](structured-logging.md#the-portable-level-meanings-are)'s
`ERROR` or `CRITICAL` meaning as appropriate and its structured, redacted
exception representation rather than string-interpolating the exception into
a message.

## The runtime entrypoint translates escaped failures

The runtime entrypoint is the one place that converts an exception which
escapes all owner-level handling into a process outcome — an exit code, an
HTTP response, a job failure status — logs it once, and documents its own
mapping from exception type to outcome. Forge does not mandate a universal
exit-code table, HTTP status scheme, or job-status vocabulary; that mapping is
the entrypoint owner's documented interface, in the same sense that
[assemble once and inject explicitly](configuration-ownership.md#assemble-once-and-inject-explicitly)
makes configuration assembly the entrypoint's job. A project with no runtime
entrypoint performs no translation.

## Messages and diagnostics carry no secrets

Exception messages, `args`, and string representations reach logs,
tracebacks, and CI output through paths this contract does not control.
Diagnostic text identifies what failed — a field name, a variable name, a
path, a configuration source — without echoing secret-bearing values. This
mirrors the boundary already stated for
[environment-variable validation errors](environment-variables.md#safe-examples-and-user-documentation)
and [path validation errors](paths-and-resources.md#path-values-and-interfaces),
and is reinforced, not replaced, by structured logging's defensive redaction:
redaction is defence in depth for values that reach a log record, not a
licence to embed a secret in an exception message on the assumption that
redaction will catch it. Broader secret-file safeguards and optional scanning
remain owned by [FT-05.04](https://github.com/Sandsy09/forge-template/issues/30).

## Exception compatibility

A documented exception type, the documented fact that a public operation can
raise it, and its documented attributes form part of the owning component's
compatibility surface — the same sense in which structured logging's
documented event identifiers form a compatibility surface. Adding a new
subclass under an existing documented base is compatible. Changing what a
documented public operation raises, removing a documented type, or moving a
type out from under its documented base requires versioning and migration
guidance appropriate to that owner. An undocumented, internal-only exception
carries no compatibility promise.

## Generated-project exceptions are not engine errors

This contract governs exceptions raised by generated-project runtime code. The
errors `forge-template` itself raises while validating a generation request
and composing a project are the distinct
[stable template-engine error surface](template-engine-api.md#structured-failures),
listed under this repository's
[structured engine errors and generated-project validation](roadmap-v1/REPOSITORY-OWNERSHIP.md)
ownership. A generated project never catches an engine error at runtime, and
the engine never raises a generated project's exception types at generation
time. Presenting an engine error to a CLI user remains `create-forge`'s
responsibility.

## Current Library evidence

The v0.1.x Library scaffold remains free of exception-handling behaviour
beyond one narrow, already-necessary case:

- its package defines no exception class or hierarchy of its own;
- its only exception handling is a single narrow
  `except PackageNotFoundError` around the `importlib.metadata.version` lookup,
  with a documented `"0.0.0"` fallback
  ([`__init__.py.jinja`](https://github.com/Sandsy09/forge-template/blob/main/template/src/%7B%7Bpackage_name%7D%7D/__init__.py.jinja));
- generated runtime dependencies are empty, so no framework or provider
  exception types are present to wrap or re-export; the generated ruff
  configuration already selects `B` (flake8-bugbear), so B904 already applies
  to any wrapping a future owner adds; and
- Copier offers no exception-related question or answer.

This decision changes no template file, Copier answer, generated output,
runtime dependency, schema, public API, or CLI behaviour.

## Deferred implementation mechanics

This contract does not define a concrete base exception class name or module
path, an error-code registry, a universal exit-code table, a retry or
circuit-breaking policy, a traceback-formatting library, a ProjectSpec field,
a component manifest, or a migration. Stage 06 owns composition and collision
mechanics, and owns the template engine's own error surface referenced above.
Lint enforcement beyond the ruff `B` selection already present in the
generated project — for example dedicated exception-discipline rule sets —
is a separate template change and not part of this decision.
