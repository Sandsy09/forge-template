# 42. Validate no-copy downstream inheritance

## Status

Accepted

## Context

Stages 06–08 established a package-bound Foundation source, bundled component
catalogue, deterministic public composition engine, and two independent
archetypes. Stage 09 then constrained organisation policy to selection,
published the sanctioned extension surface, proved policy resolution with a
test-only reference fixture, and defined the compatibility policy a
Blueprint-style client may rely on.

Those individual contracts did not yet prove the architectural outcome they
were intended to enable: a second client should be able to reuse Forge output
without copying Foundation or component source, importing `create-forge`, or
reaching into private engine modules. Nor did they demonstrate that policy
provenance is output-neutral or that additive organisation choices remain
within selected-component ownership and published extension points.

The production catalogue intentionally contains no capability or platform.
It can prove the public, package-bound no-copy path, but it cannot by itself
demonstrate additive capability/platform composition. The existing private
fixture catalogue can demonstrate that second property, but exposing its test
override as client API would contradict ADR 0029 and ADR 0039.

## Decision

Publish [no-copy-inheritance.md](../no-copy-inheritance.md) as the living
contract and validate it with a test-only Blueprint-style harness.

The public proof resolves the existing `example-production-library` policy
against the real installed catalogue and compares it with a directly
constructed equivalent Library ProjectSpec. Planning and rendering must be
byte-identical; only policy provenance may differ. Foundation and Library
ownership metadata must remain intact, and generated runtime dependencies
must name neither Forge package.

Use the existing private fixture catalogue only for a separate additive
composition proof. Add the neutral `example-no-copy-inheritance` policy,
selecting `library-v2`, `coverage`, and `github`, and prove that every output
delta is either an owned component file or a declared contribution to a
published extension point. The downstream harness itself imports engine
behavior only from the top-level `forge_template` facade and reuses the
existing test-only organisation-policy resolver.

Do not add a public resolver, catalogue injection, plugin/registry mechanism,
production component, or arbitrary file replacement path. Organisation-
specific executable content continues to require a reviewed engine
distribution or fork until a future decision accepts a public distribution
mechanism.

## Consequences

- The no-copy model is now executable across the real package-bound catalogue
  and the existing additive composition fixtures rather than remaining an
  architectural assertion.
- Equivalent effective ProjectSpecs are proven to produce equivalent plans
  and bytes even when policy provenance differs.
- Downstream policy trust, explicit-choice tracking, policy resolution,
  ProjectSpec construction, compatibility presentation, staging, and
  finalisation remain client-owned; no engine content is duplicated to fulfil
  them.
- Private catalogue/Foundation overrides remain test-only and unsupported.
  The proof cannot be cited as a plugin or external-registry contract.
- `forge-template` stays at `0.3.2`. The public facade, ProjectSpec, manifest,
  option-schema, Foundation, and organisation-policy protocols do not change.
- No template, Copier answer, generated output, runtime dependency, tag, or
  release changes as a result of this decision.
