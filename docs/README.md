# Documentation

This directory holds documentation about `forge-template` itself, as opposed
to the documentation the `library` archetype generates for scaffolded
projects (that lives under `template/{% if use_docs %}docs{% endif %}/`).

- [terminology.md](terminology.md) — canonical Forge architectural vocabulary
  and authority rules.
- [foundation-guarantees.md](foundation-guarantees.md) — mandatory outcomes
  every generated Forge project receives from Foundation.
- [foundation-scope.md](foundation-scope.md) — inclusion, exclusion, and
  routing rules that keep Foundation conservative and runtime-free.
- [python-support.md](python-support.md) — supported CPython window, generated
  project version semantics, and release-transition policy.
- [editor-integration.md](editor-integration.md) — editor-neutral Foundation
  policy and boundaries for future optional editor capabilities.
- [configuration-ownership.md](configuration-ownership.md) — owner-local typed
  runtime configuration and explicit assembly and injection conventions.
- [environment-variables.md](environment-variables.md) — owner-prefixed
  environment inputs, source precedence, and explicit local dotenv behaviour.
- [structured-logging.md](structured-logging.md) — owner-local events,
  process-wide configuration, structured envelope, and redaction boundaries.
- [paths-and-resources.md](paths-and-resources.md) — owner-local path and
  resource access, context-free runtime code, and explicit writable
  locations.
- [exception-ownership.md](exception-ownership.md) — owner-local exceptions,
  catch/wrap/log-once discipline, and the entrypoint's failure-translation
  boundary.
- [adr/](adr/) — Architecture Decision Records: why this repo is shaped the
  way it is, not just what it currently looks like.
