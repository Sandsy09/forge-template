# 40. Prove the organisation-policy protocol with a test-only reference fixture

## Status

Accepted

## Context

[ADR 0038](0038-organisation-policy-selection-model.md) defined organisation
policy protocol `1` as prose: strict wire format, resolution authority order,
merge semantics, and 17 named structured-failure detail codes. [ADR
0039](0039-deny-policy-file-overrides.md) closed the companion question --
what content a policy may extend -- also as prose. Neither ADR added an
executable parser or resolver; both left that to
[FT-09.03](https://github.com/Sandsy09/forge-template/issues/46), which this
ADR resolves.

Two things follow from where this issue sits: Stage 09 is the final stage in
roadmap v1, so no later issue is scheduled to ship a resolver -- if one isn't
built now, none is currently planned at all. And the production catalogue
(`library`, `cli`) has zero capabilities or platforms, so it alone cannot
demonstrate every rule kind organisation-policy.md defines; the fixture
catalogue at `tests/fixtures/component_manifests/` can, but a fixture-only
proof would never show a policy-resolved selection actually rendering a real
project.

## Decision

Implement a **test-only reference resolver**,
`tests/organisation_policy_contract.py`, parsing and resolving policy
documents against the public `forge_template` facade
(`discover_components()` for catalogue checks). It is not
`src/forge_template` code: no public export, no new `EngineErrorCode`, no
package-version change. This follows [ADR 0028](0028-composition-contract-fixtures.md)'s
precedent exactly -- `tests/composition_contract.py` was kept out of `src/`
for the identical reason, preserving one future issue's undivided ownership
of whatever public surface eventually ships.

Two implementation constraints, both deliberate:

- **Hand-written validation, not pydantic delegation.** The fixture exists to
  make organisation-policy.md's own 17 detail codes reachable; delegating to
  pydantic would surface pydantic's error taxonomy instead of the documented
  one.
- **A local `PolicyError`, never `forge_template.ForgeEngineError`.** Mirrors
  the documented category/`code`/`path`/`message` shape without touching the
  public error surface, which stays exactly where CLAUDE.md and
  organisation-policy.md leave it.

Five checked-in placeholder policy documents live at
`tests/fixtures/organisation_policies/`, every ID `example-`-prefixed. Four
resolve against the fixture catalogue, covering the full
archetype/capability/platform rule matrix (including the documented
delivery/quality merge example and its irreconcilable restricted-delivery
counterpart). One, `example-production-library`, resolves against the real
installed catalogue and is carried through `parse_project_spec` and
`render_project` end-to-end -- the one proof that a policy-resolved selection
is directly `ProjectSpec`-shaped and produces a real rendered project.
Negative/invalid documents stay inline in the test module, matching ADR
0028's invalid-catalogue split: on-disk fixtures are the publishable
artefact a downstream author copies, and a deliberately broken document is
not worth publishing.

`tests/test_organisation_policy_fixture.py` exercises the resolver against
these fixtures: the authority order (profile default < policy default <
explicit choice < required/forbidden validation), order-independent merge,
all 17 detail codes, the policy/content-extension boundary from
[extension-points.md](../extension-points.md), the end-to-end render, and
that the checked-in fixtures themselves carry no organisation-specific
values.

`docs/organisation-policy-fixtures.md` documents the methodology, following
`docs/composition-fixtures.md`'s shape.

## Consequences

- Organisation-policy protocol `1` now has an executable proof it is
  internally consistent and that every documented failure is reachable, not
  just prose.
- **A shipped, public resolver is unscheduled in roadmap v1.** Stage 09 is
  its final stage; no issue here or in create-forge currently commits to
  building one. Client-side resolution against this reference -- as
  create-forge's [CF-09.01](https://github.com/Sandsy09/create-forge/issues/53)
  already does -- is the operative architecture until a future ADR changes
  it.
- `forge_template`'s public facade, `EngineErrorCode`, and package version
  (`0.3.2`) are unchanged. `ForgeEngineError` is not raised by this fixture
  under any circumstance.
- No ProjectSpec or manifest protocol change: `SelectionProvenance.policies`
  already carried policy-ID provenance and needed no addition.
- The reference resolver's `no-permitted-archetype` handling covers the case
  it can itself produce -- no archetype resolves from any tier -- not every
  path organisation-policy.md's prose could be read to imply. A future
  shipped resolver may need to cover more; this fixture proves the
  documented rules compose, not that every edge case is enumerated.
- No template, Copier answer, package dependency, generated output, or
  runtime behaviour changes. The fixture ships in no wheel.
