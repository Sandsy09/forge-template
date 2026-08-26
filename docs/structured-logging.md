# Structured logging capability

This is the canonical living contract for structured logging in generated
Forge projects. It extends the
[configuration ownership conventions](configuration-ownership.md), which
assign runtime settings to the archetype or capability consuming them and
require the runtime entrypoint to assemble them once. [ADR
0017](adr/0017-owner-local-structured-logging.md) records why Forge adopted
this contract.

The contract describes generated-project behaviour that future archetypes and
capabilities must preserve. It does not add logging to the current v0.1.x
Library scaffold or define a ProjectSpec or component manifest field.

## Logging has a runtime owner

Foundation supplies no logging package, configuration, handler, formatter,
global logger, or runtime dependency. The archetype or capability contributing
runtime behaviour owns the events that behaviour emits, their meanings, and
their owner-defined fields. A project with no logging owner needs no logging
configuration or supporting dependency.

An optional structured-logging capability may provide cross-component
configuration, formatting, defensive redaction, and provider-neutral stream
handling. An archetype may instead own equivalent behaviour when logging is
intrinsic to its primary runtime shape. Neither placement promotes logging to
Foundation or gives one owner authority over another owner's event vocabulary.

## Emit through module loggers

Runtime owners emit through Python's standard logging API and obtain module
loggers with `logging.getLogger(__name__)`. Reusable packages do not call
`logging.basicConfig`, configure the root logger, set process-wide levels, or
install an emitting handler. A package may install a package-level
`logging.NullHandler`; that is the only handler a reusable emitter owns.

Emitters supply a stable event identifier and structured fields. They do not
pre-render those fields into an opaque sentence or depend on a particular
console, JSON, or provider exporter. The runtime entrypoint remains the one
place that activates process logging.

## Configure once at the runtime entrypoint

The runtime entrypoint validates the selected logging owner's typed
configuration and applies one process-wide baseline exactly once. The minimum
configuration provides:

- `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL` as the portable levels;
- `INFO` as the non-sensitive default threshold;
- an explicit `console` or `json` format setting, with `console` as the
  non-sensitive default; and
- stderr as the provider-neutral destination for both formats, leaving stdout
  available for intentional program output and machine-readable command
  results.

Invalid levels or formats fail startup validation. Custom levels are outside
the portable contract. An environment identity must never select or imply a
level or format. When the logging owner exposes environment-backed settings,
they follow the canonical
[environment-variable conventions](environment-variables.md), including
owner-prefixed names, source precedence, and explicit dotenv loading.

The portable level meanings are:

| Level | Meaning |
| --- | --- |
| `DEBUG` | Detailed developer diagnostics that may change between versions. |
| `INFO` | Expected lifecycle progress or a normal operational milestone. |
| `WARNING` | An unexpected or degraded condition from which the operation can continue or recover. |
| `ERROR` | The current operation failed, although the process may remain able to handle other work. |
| `CRITICAL` | The process or primary runtime cannot continue safely. |

An emitting component chooses the level that describes its own event. It does
not change the configured process threshold to make an event visible.

## Common structured-event envelope

Every rendered record has this flat provider-neutral envelope:

| Key | Contract |
| --- | --- |
| `timestamp` | Formatter-supplied UTC timestamp in RFC 3339 form. |
| `level` | One canonical uppercase severity name. |
| `logger` | The standard-library logger name. |
| `event` | A stable lower-snake-case event identifier supplied by the emitter. |

Owner-defined fields sit beside these keys and use JSON-compatible scalar,
array, object, or null values. They must not collide with the four canonical
keys or the standard `logging.LogRecord` attributes. A collision is invalid;
formatters and future composition must reject it rather than silently replace
either value.

The console and JSON formats are two views of the same structured record.
Console output may optimise the presentation for a human, while JSON output is
one UTF-8 JSON object per line. Switching format must not change event meaning,
drop owner fields, or introduce a second event schema.

Forge defines no universal business, request, tracing, deployment, or domain
schema. Each runtime owner documents the event vocabulary and fields needed by
its behaviour. A provider integration may faithfully adopt an external
standard through its own adapter without turning that standard into a
Foundation requirement.

## Event compatibility

Documented `INFO`, `WARNING`, `ERROR`, and `CRITICAL` event identifiers and
field meanings form the emitting owner's observability compatibility surface.
Adding a new event or an optional field is compatible. Renaming or removing an
event, or changing a field's type or meaning, requires versioning and migration
guidance appropriate to that owner.

`DEBUG` events are deliberately unstable diagnostics. Consumers must not rely
on their identifiers or fields as a compatibility contract. Promoting a DEBUG
event to the documented operational surface requires documenting its stable
identifier, fields, and level meaning.

## Sensitive fields and defensive redaction

Emitters must not log secrets, credentials, tokens, private keys, raw
environment values, or whole configuration or environment dumps. Personal or
domain-sensitive data is included only when its owner documents an operational
need and a minimal safe representation.

The structured-logging capability applies defensive redaction before console
rendering, JSON serialization, or provider export. Redaction covers all
owner-defined fields and any supplied exception information. A redaction
failure must never fall back to the original raw value; an implementation may
replace or omit the unsafe value, but must preserve that safety boundary.

Defensive redaction does not transfer responsibility away from emitters. An
unknown secret embedded in an opaque string cannot be made safe reliably, so
owners must structure permitted values and exclude sensitive content at the
source. Broader secret-file safeguards and optional scanning remain owned by
[FT-05.04](https://github.com/Sandsy09/forge-template/issues/30).

## Exceptions and provider integrations

When an owner supplies exception information, the selected logging capability
preserves it as structured, redacted information rather than requiring string
interpolation. The rules for catching, wrapping, logging once, re-raising, and
avoiding duplicate or silent handling remain owned by
[FT-04.05](https://github.com/Sandsy09/forge-template/issues/28).

Network exporters, vendor SDKs, hosted log delivery, and deployment-specific
handlers are platform contributions. They attach through declared extension
points and may not silently replace the provider-neutral stderr handler or add
duplicate delivery. Stage 06 owns the manifest declarations, ordering,
compatibility, and collision errors required to compose these contributions.

## Current Library evidence

The v0.1.x Library scaffold remains logging-light and unchanged:

- its package exposes version metadata and no logging behaviour;
- generated runtime dependencies are empty and include no logging library;
- generated source has no logging imports, handlers, formatters, or
  configuration; and
- Copier offers no structured-logging selection or answer.

The current scaffold therefore implements neither the optional capability nor
an archetype-owned logging contract. This decision changes no template file,
Copier answer, generated output, runtime dependency, schema, public API, or CLI
behaviour.

## Deferred implementation mechanics

This contract does not define a concrete configuration class, formatter,
redaction library, exporter API, context-propagation mechanism, component
identifier, ProjectSpec field, manifest, or migration. Stage 06 owns the
composition mechanics, while FT-04.05 owns exception-handling and log-once
rules.
