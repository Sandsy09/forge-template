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
- [secret-handling.md](secret-handling.md) — neutral secret-ignore
  safeguards, the enforced placeholder-only example, and the optional
  scanning boundary.
- [supply-chain-provenance.md](supply-chain-provenance.md) — desired SBOM and
  release-provenance behaviour, named reference tooling, and the exit
  criteria implementation must satisfy.
- [github-action-pinning.md](github-action-pinning.md) — immutable remote
  workflow references and their reviewed automated or manual update paths.
- [project-spec.md](project-spec.md) — strict ProjectSpec protocol v1,
  effective selections, provenance, and schema boundaries for the future
  composition engine.
- [component-manifests.md](component-manifests.md) — strict TOML component
  metadata, compatibility, content ownership, dependencies, and conflicts.
- [composition-order.md](composition-order.md) — deterministic tier and
  within-tier application order, cross-tier dependency handling, cycle
  rejection, and content-path ordering for the future composition engine.
- [file-conflicts.md](file-conflicts.md) — output targets, dispositions,
  extension points, and collision-safety rules for the future composition
  engine.
- [adr/](adr/) — Architecture Decision Records: why this repo is shaped the
  way it is, not just what it currently looks like.
