# 21. Defer SBOM and release provenance to an optional capability

## Status

Accepted

## Context

[ADR 0012](0012-conservative-foundation-scope.md) keeps Foundation
conservative and runtime-free. [ADR
0020](0020-generated-project-secret-safeguards.md) set the immediately
preceding precedent for this kind of decision: define an optional
supply-chain concern as a contract with named reference tooling, and generate
none of it until a real integration exists to test. [ADR
0008](0008-remove-make-task-runner.md) records the cost of the alternative —
`make` shipped as a `task_runner` choice with a byte-empty `Makefile` because
nothing in the validation suite ever exercised it.

The decisive fact here is structural, not a matter of taste: **the generated
project has no release or publish workflow.**
`template/.github/workflows/ci.yml.jinja` contains one workflow, whose `build`
job runs `uv build`, verifies metadata with `twine check`, and uploads `dist/`
as a CI artifact — nothing tags, releases, signs, or publishes. An SBOM and a
release-provenance attestation both attach to a release/publish event. Without
one, generating either now would produce an untested conditional guarding a
workflow that does not exist, exactly the failure ADR 0008 already removed
once.

The argument cuts both ways. Generating an SBOM step or attestation job now
would bind Forge to a specific format and tool before any publish use case
requires one, and before Stage 06's composition mechanics exist to express it
as an optional capability rather than an unconditional template change. But
leaving the concern entirely undocumented is also wrong:
[terminology.md](../terminology.md#capability) already names "release
provenance" as a capability example, and
[secret-handling.md](../secret-handling.md#deferred-implementation-mechanics)
already forward-references this issue by name — both claims were unsupported
until this decision.

## Decision

Adopt [supply-chain-provenance.md](../supply-chain-provenance.md) as the
canonical living contract for a future SBOM and release-provenance capability,
and change nothing else:

- classify SBOM generation as a **capability** and attestation, signing, and a
  keyless publish path as a **GitHub platform** contribution, per [Foundation
  scope's routing table](../foundation-scope.md#routing-non-foundation-concerns);
- name **CycloneDX** as the reference SBOM format, sourced from `uv.lock`;
  name `actions/attest-build-provenance` with **Sigstore** as the reference
  GitHub platform contribution; and name **PyPI Trusted Publishing** as the
  reference keyless publish path;
- require that any future implementation scope elevated permissions
  (`id-token: write`, `attestations: write`) at the job level, never the
  workflow level, preserving FT-05.02's least-privilege posture;
- record the reproducibility caveat: provenance attests who built an artifact
  and where, not that it is independently rebuildable — this does not change
  [foundation-guarantees.md's existing non-guarantee](../foundation-guarantees.md#non-guarantees-and-deferred-decisions)
  covering byte-identical distribution artifacts; and
- record four exit criteria that must hold before implementation begins: a
  release/publish path exists in generated projects, Stage 06 composition can
  express this as an optional capability plus platform contribution, the
  result is testable by this repository's combo suite, and elevated
  permissions stay job-scoped.

This decision adds no Copier question, template change, CI job, runtime
dependency, or committed SBOM file. It governs generated projects only;
`forge-template`'s own release process and `create-forge`'s CF-05.x posture
are out of scope and remain free to decide independently.

## Consequences

- Generated output is unchanged, so this decision carries no `copier update`
  surface and needs no combo or update-scenario validation.
- `terminology.md`'s "release provenance" capability example and
  `secret-handling.md`'s forward reference to this issue both now resolve to
  a real contract instead of an unsupported claim.
- The reproducibility non-guarantee in `foundation-guarantees.md` is now
  explicitly linked from a contract that depends on it, rather than sitting
  unconnected to any concrete use.
- Stage 05's supply-chain story is complete on paper for `forge-template`,
  with implementation openly deferred rather than silently missing; FT-05.03
  (#29) remains the one still-open Stage 05 item.
- A future implementation must satisfy the four exit criteria above and
  record its own ADR when it adds a capability, platform contribution, or
  Copier question; this record does not pre-approve that later work.
