# Supply-chain provenance

This is the canonical living contract for a future SBOM and release-provenance
capability in generated Forge projects. [ADR
0021](adr/0021-defer-sbom-and-release-provenance.md) records why Forge defines
this contract without implementing it yet.

Unlike [secret-handling safeguards](secret-handling.md), this decision changes
**no** generated output. It defines desired behaviour and required properties
so a future implementation has a contract to satisfy, and records the exit
criteria that must hold before that implementation begins.

## Scope and vocabulary

This repository already uses "provenance" for a different concern:
[Foundation's update and provenance
state](foundation-scope.md#forge-update-and-provenance-state) is the
version-controlled `.copier-answers.yml` state that identifies a generated
project's template origin and keeps `copier update` safe. That is
**generation-provenance** — evidence about how a project was created.

This document owns **release provenance** instead — evidence about a built
distribution artifact: which source commit, workflow, and builder produced it,
and an optional software bill of materials (SBOM) describing what it contains.
The two concerns are independent; a project can have one without the other.
Nothing below alters generation-provenance state.

## Why this is not Foundation

Applying [Foundation scope's inclusion conditions](foundation-scope.md#inclusion-rule):

- **Universal** fails: an archetype that ships no distributable artifact has
  nothing to attach an SBOM or provenance record to.
- **Provider-neutral** fails: attestation binds to a specific OIDC issuer,
  transparency log, and source host.
- **Stable and testable** fails today for a structural reason, not a
  preference one: [the generated project has no release or publish
  event](#current-library-evidence) to attach an outcome to, so there is
  nothing yet for Forge to validate.

The removal test confirms it: omitting SBOM and provenance generation today
breaks no guarantee and leaves a generated repository complete at handoff.

## Where it belongs

Applying [Foundation scope's routing table](foundation-scope.md#routing-non-foundation-concerns):
SBOM generation is a **capability** — an optional, reusable concern a project
may select. Attestation, signing, and a keyless publish path are a **GitHub
platform** contribution, since they bind to a specific host's OIDC and
transparency-log infrastructure. Whether an archetype wants either is a
**profile** input. This gives concrete substance to the "release provenance"
capability example already named in
[terminology.md](terminology.md#capability).

## Desired SBOM behaviour

A future SBOM capability must:

- derive its contents from the same resolved dependency set the artifact was
  actually built against — `uv.lock` is the source of truth, never a fresh
  re-resolution that could disagree with what shipped;
- scope to the distributed closure, excluding or explicitly marking
  development and test dependency groups;
- use a stable, machine-readable format; **CycloneDX** is named as the
  reference format;
- be emitted as a build output alongside `dist/` and attached to the release,
  **never committed to the repository** — it is derived state, and committing
  it invites drift between the file and the artifact it describes plus
  needless `copier update` merge noise; and
- be regenerable, so a consumer can independently verify it rather than merely
  trust it.

## Provenance and signing considerations

A future release-provenance capability must:

- record the source repository, commit, workflow, and builder identity that
  produced the artifact;
- prefer short-lived keyless identity over a long-lived signing key, so there
  is no secret to rotate or leak — this follows directly from
  [secret-handling safeguards](secret-handling.md), which already treats
  avoiding a stored credential as the safer default;
- be publicly verifiable without contacting the publisher; and
- be produced by the same job that produced the artifact, not a later or
  separate one.

Named GitHub platform contribution: `actions/attest-build-provenance` with
Sigstore. Named keyless publish path: **PyPI Trusted Publishing**, which
authenticates via OIDC instead of a stored API token.

**Permissions consequence.** Attestation requires `id-token: write` and
`attestations: write`. The generated workflow's current `permissions:
contents: read` deliberately does not grant either. Any future job that adds
them must scope them **at the job level, never the workflow level** —
preserving the least-privilege posture FT-05.02 already established.

## The reproducibility caveat

Provenance attests who built an artifact and where; it does not prove that
anyone else could independently rebuild it bit-for-bit.
[foundation-guarantees.md](foundation-guarantees.md#non-guarantees-and-deferred-decisions)
already lists "byte-identical generated trees or distribution artifacts" as a
non-guarantee, and this contract does not change that. A future
implementation must not claim reproducibility it does not have; raising
reproducibility to a guarantee would require its own ADR superseding the
guarantee contract.

## Why implementation stays deferred

Two structural facts, not a preference, block implementation today:

- the generated project has no release or publish workflow at all — see
  [Current Library evidence](#current-library-evidence) — so SBOM and
  provenance generation would attach to nothing; and
- the Stage 06 engine now supplies composition mechanics, but no production
  capability and platform manifests yet express this concern; that migration
  must not be folded into the monolithic template as an unconditional change.

Generating either now, ahead of a real release event and production component
migration, would produce exactly the failure [ADR
0008](adr/0008-remove-make-task-runner.md) already removed once: an untested
conditional guarding a workflow nobody runs.

## Current Library evidence

The v0.1.x Library scaffold's `template/.github/workflows/ci.yml.jinja`
contains one workflow. Its `build` job runs `uv build`, verifies metadata with
`twine check`, and uploads `dist/` as a CI artifact, under a workflow-level
`permissions: contents: read`. It does **not** tag, release, publish, sign, or
attest anything, and generates no SBOM.

## Exit criteria

Implementation should not begin until all of the following hold:

- [ ] A generated-project release or publish path exists and has an identified
  owner.
- [x] Stage 06 composition can express an optional capability plus its
  platform contribution, so this need not become an unconditional template
  change.
- [ ] The result is testable by this repository's own combo suite, not merely
  rendered and inspected by hand.
- [ ] Any elevated permissions it needs stay job-scoped, per the [permissions
  consequence](#provenance-and-signing-considerations) above.

## Deferred implementation mechanics

This contract adds no Copier question, no CI job, no runtime dependency, no
committed SBOM file, and no format lock-in beyond the named references above.
The Stage 06 engine supplies the composition mechanics that let a future
capability and platform contribution be selected and rendered in memory;
Stage 08-style production manifests and CLI filesystem orchestration are still
required before generation.
[`create-forge`](https://github.com/Sandsy09/create-forge) owns its own
release posture independently, via its own CF-05.x issues; this contract
governs generated projects only.
