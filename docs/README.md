# Documentation

This directory holds documentation about `forge-template` itself, as opposed
to the documentation the `library` archetype generates for scaffolded
projects (that lives under `template/{% if use_docs %}docs{% endif %}/`).

- [invariants.md](invariants.md) — the six hard rules governing changes
  under `template/` and `copier.yml`.
- [terminology.md](terminology.md) — canonical Forge architectural vocabulary
  and authority rules.
- [foundation-guarantees.md](foundation-guarantees.md) — mandatory outcomes
  every generated Forge project receives from Foundation.
- [foundation-scope.md](foundation-scope.md) — inclusion, exclusion, and
  routing rules that keep Foundation conservative and runtime-free.
- [library-archetype.md](library-archetype.md) — the distributable Python
  package contract and accepted requirements for the Stage 08 migration.
- [cli-application-archetype.md](cli-application-archetype.md) — the selected
  second reference archetype's package, dependency, command, and future
  composition contract.
- [data-science-archetype.md](data-science-archetype.md) — the accepted
  package-plus-notebooks shape and ownership boundary for the future third
  production archetype.
- [data-science-capabilities.md](data-science-capabilities.md) — the accepted
  optionless Jupyter tooling and optional Scientific Python dependency
  contracts, including the production Jupyter implementation on `main`.
- [notebook-data-and-model-safeguards.md](notebook-data-and-model-safeguards.md)
  — fail-closed notebook validation order, deterministic failure identifiers,
  safe diagnostics, and the prose-only working-tree guidance for the future
  Data Science archetype.
- [data-science-compatibility-and-acceptance.md](data-science-compatibility-and-acceptance.md)
  — the versioned-axis classification, executable acceptance matrix, valid and
  invalid selections, and cross-repository release gates for the `0.4.0` Data
  Science engine line.
- [roadmap-v2/](roadmap-v2/) — the Stage 10–14 two-repository roadmap for a
  package-backed Data Science archetype and reusable optional capabilities.
- [roadmap-v1/](roadmap-v1/) — the completed historical Foundation roadmap
  for Stages 00–09.
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
- [organisation-policy.md](organisation-policy.md) — strict JSON policy
  protocol v1, deterministic selection precedence, conflict rules, and future
  structured failure semantics.
- [organisation-policy-fixtures.md](organisation-policy-fixtures.md) — the
  test-only reference resolver and placeholder policy documents proving that
  protocol executably.
- [no-copy-inheritance.md](no-copy-inheritance.md) — the executable boundary
  proving downstream clients reuse package-bound Forge content without
  copying it or importing private engine modules.
- [component-manifests.md](component-manifests.md) — strict TOML component
  metadata, compatibility, content ownership, dependencies, and conflicts,
  plus the implicit Foundation content source and manifest protocol `2`'s
  discriminated Foundation/component contribution target.
- [composition-order.md](composition-order.md) — deterministic tier and
  within-tier application order, cross-tier dependency handling, cycle
  rejection, and content-path ordering for the future composition engine.
- [file-conflicts.md](file-conflicts.md) — output targets, dispositions,
  extension points, and collision-safety rules for the future composition
  engine.
- [extension-points.md](extension-points.md) — the complete sanctioned
  extension surface, the denial of any `override` grant, and the published,
  versioned content extension-point inventory, now eleven entries after
  FT-11.01 added three Foundation points for capability tooling.
- [template-variables.md](template-variables.md) — the rendered
  template-variable namespace, component option declarations, and
  resolution/rejection rules for the future composition engine.
- [composition-fixtures.md](composition-fixtures.md) — golden composed-output
  fixtures, invalid-catalogue scenarios, and the determinism guarantee they
  prove for the composition, file-conflict, and template-variable contracts
  together.
- [template-engine-api.md](template-engine-api.md) — supported typed discovery,
  strict ProjectSpec validation, deterministic planning, in-memory rendering,
  extension markers, and structured engine failures.
- [generated-project-validation.md](generated-project-validation.md) — the
  side-effect-free plan/output, `pyproject.toml`, and template-completion checks
  every successful engine render passes.
- [composition-architecture-review.md](composition-architecture-review.md) —
  the two-archetype duplication, Foundation-boundary, quality, and client
  finalisation review that closes Stage 08.
- [compatibility-policy.md](compatibility-policy.md) — the Forge-Blueprint
  compatibility policy: every versioned engine axis, compatible ranges,
  deprecation windows, and unsupported-version reporting requirements.
- [adr/](adr/) — Architecture Decision Records: why this repo is shaped the
  way it is, not just what it currently looks like.
