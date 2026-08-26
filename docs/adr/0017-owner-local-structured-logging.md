# 17. Keep structured logging owner-local and configure it once

## Status

Accepted

## Context

[ADR 0012](0012-conservative-foundation-scope.md) keeps Foundation runtime-free
and assigns logging to the archetype or capability contributing runtime
behaviour. [ADR 0015](0015-owner-local-runtime-configuration.md) requires the
runtime entrypoint to assemble and validate owner-local configuration once,
while [ADR 0016](0016-owner-local-environment-inputs.md) defines how an owner
may receive environment-backed settings.

Those boundaries do not yet give independent runtime owners a common emission
API, level meaning, structured record envelope, compatibility promise, or safe
integration point for process-wide formatting and provider exporters. If each
owner configured its own handlers, a composed project could emit duplicate
records, apply inconsistent thresholds, or overwrite another component's
configuration. A universal Foundation logging package would avoid neither the
runtime dependency nor the ownership conflict and would make logging mandatory
for projects that do not need it.

The current Library scaffold contains no logging code, runtime logging
dependency, configuration, or Copier selection. A decision can therefore
define the future generated-project contract without changing current output.

## Decision

Adopt the [structured logging capability contract](../structured-logging.md)
as the canonical living reference.

The archetype or capability contributing runtime behaviour owns its event
vocabulary and fields. Reusable owners emit through module loggers obtained
with `logging.getLogger(__name__)`; they do not configure the root logger,
process-wide levels, formatters, or emitting handlers. An optional
structured-logging capability owns cross-component configuration, rendering,
defensive redaction, and provider-neutral stderr handling. The runtime
entrypoint validates and activates that configuration once.

The portable configuration uses the five standard levels with an `INFO`
default and supports explicit `console` and `json` formats with a `console`
default. Environment identity never selects either setting. Every rendered
record contains the flat `timestamp`, `level`, `logger`, and `event` envelope;
owner fields are JSON-compatible and cannot collide with canonical or
`LogRecord` keys. Documented INFO-and-higher events are a versioned
observability surface, while DEBUG diagnostics carry no compatibility promise.

Emitters exclude secrets and unsafe configuration or environment data. The
capability applies defensive redaction before any rendering or export and
never falls back to a raw value after a redaction failure. Exception
information follows the same safety boundary, but FT-04.05 retains the rules
for catch, wrap, log-once, re-raise, and duplicate handling. Provider exporters
remain platform contributions attached through future Stage 06 extension
points.

This decision changes no template file, Copier answer, generated output,
runtime dependency, ProjectSpec, component manifest, schema, public API, or
CLI behaviour.

## Consequences

- Configuration-light projects and reusable libraries remain free of a
  mandatory logging runtime layer.
- Runtime owners share a predictable Python emission convention and event
  envelope without sharing a domain schema.
- One entrypoint-owned configuration prevents competing handlers, levels, and
  duplicate delivery in a composed process.
- Operational event consumers receive an explicit compatibility promise,
  while owners retain freedom to evolve DEBUG diagnostics.
- Structured fields become useful for human and machine consumers without
  weakening the rule that sensitive values are excluded at their source.
- Platform adapters can add vendor delivery without making a provider part of
  the capability's neutral contract.
- Stage 06 must represent logging contributions and reject handler or field
  collisions, and FT-04.05 must complete the exception-handling boundary.
- The current Library scaffold remains unchanged until later roadmap work
  selects and implements an owning component.
