# Organisation-policy reference fixture

This document describes what the organisation-policy compatibility fixture
proves, why it uses a test-only resolver rather than a shipped one, and how a
downstream client can use it as a worked example. Delivered by
[FT-09.03](https://github.com/Sandsy09/forge-template/issues/46) through
[`tests/organisation_policy_contract.py`](../tests/organisation_policy_contract.py)
and
[`tests/test_organisation_policy_fixture.py`](../tests/test_organisation_policy_fixture.py),
this document is adopted by
[ADR 0040](adr/0040-organisation-policy-reference-fixture.md).

## Scope

This is a test methodology and a worked example, not a new normative
contract. [organisation-policy.md](organisation-policy.md) already defines
the strict wire protocol, resolution semantics, and 17 structured-failure
detail codes; [extension-points.md](extension-points.md) already defines that
policy is selection-only. Nothing here changes either. What was missing is
proof: an executable resolver against real placeholder data, showing the
documented rules actually compose and that every documented failure is
reachable.

## Why a test-only resolver

`tests/organisation_policy_contract.py` implements the protocol's parsing,
merge, and resolution rules against the public
[`forge_template`](template-engine-api.md) facade -- specifically
`discover_components()` for catalogue existence/kind checks. It is
deliberately **not** `src/forge_template` code:

- No roadmap issue in Stage 09, the final stage in roadmap v1, schedules a
  shipped resolver. Adding one here would convert a `type:test`,
  `priority:low` issue into an unplanned feature and a `0.4.0` release.
- CLAUDE.md already states the standing rule this respects: do not add policy
  parsing, resolution, public exports, or `ForgeEngineError` values to
  `src/forge_template`; a shipped implementation remains unscheduled.
- The precedent is
  [ADR 0028](adr/0028-composition-contract-fixtures.md):
  `tests/composition_contract.py` was kept out of `src/` for the same reason
  -- so a single future issue keeps undivided ownership of the eventual
  public surface.

Downstream, client-side policy resolution is already owned by create-forge's
[CF-09.01](https://github.com/Sandsy09/create-forge/issues/53). This fixture
is what such a client's own resolver can be built and tested against; it
raises its own `PolicyError` (category, sorted details), never
`forge_template.ForgeEngineError` -- the public error surface is unchanged by
this issue, exactly as organisation-policy.md and ADR 0038 already state.

## The placeholder policy documents

Six checked-in JSON documents at `tests/fixtures/organisation_policies/`,
every ID prefixed `example-` so neutrality is a checked property (see
`test_fixture_policies_carry_no_organisation_specific_values`), not an
assertion:

| File | Rules | Purpose |
| --- | --- | --- |
| `example-baseline.json` | defaults + required + forbidden together | the single-document floor |
| `example-delivery-baseline.json` | `required.platforms` | merges cleanly with `example-quality-baseline` |
| `example-quality-baseline.json` | `defaults.capabilities` + `forbidden.capabilities` | merges cleanly with `example-delivery-baseline` |
| `example-restricted-delivery.json` | `forbidden.platforms` | the documented irreconcilable pair with `example-delivery-baseline` (`required-forbidden-conflict`) |
| `example-production-library.json` | `required.archetype` + `forbidden.archetypes` | resolves against the **real installed catalogue**, not the fixture one |
| `example-no-copy-inheritance.json` | default/required capability and platform plus a forbidden capability | proves additive selected-component ownership for [FT-09.05](no-copy-inheritance.md) |

The middle three mirror
[organisation-policy.md's own worked merge example](organisation-policy.md#multiple-policies)
by structure and name, with its placeholder IDs (`capability-a`,
`platform-a`, ...) swapped for real fixture-catalogue identifiers so they
pass catalogue validation instead of staying decorative.

Negative/invalid documents (malformed fields, contradictory rule sets) stay
inline in the test module rather than on disk, for the same reason ADR
0028's invalid-catalogue fixtures split the same way: the checked-in
documents are the publishable artefact a downstream author copies, and a
deliberately broken one is not worth publishing.

## Two catalogues, split by purpose

The source production catalogue (`library`, `cli`, `jupyter`,
`scientific-python`) still has no platforms and deliberately provides only a
small capability set. Most scenarios therefore resolve against the fixture catalogue
at `tests/fixtures/component_manifests/` (`library`, `library-v2` as two
archetypes; `changelog`, `coverage`, `documentation` as capabilities;
`github` as a platform), reached through the same private
`_CATALOGUE_ROOT_OVERRIDE`/`_FOUNDATION_ROOT_OVERRIDE` seam
[`tests/test_engine.py`](../tests/test_engine.py)'s `fixture_catalogue`
fixture already uses -- not a new one.

One scenario, `example-production-library`, resolves against the **real**
installed catalogue via `discover_components()` and is carried all the way
through `parse_project_spec` and `render_project` in
`test_resolved_selection_renders_a_real_project`. This is the fixture's one
genuinely end-to-end proof: a policy-resolved selection is directly
`ProjectSpec`-shaped and produces a real rendered project through the
supported [template-engine API](template-engine-api.md). FT-09.05 builds on
that path in the [no-copy inheritance proof](no-copy-inheritance.md), comparing
the policy-derived result with an equivalent direct client and separating the
real-catalogue proof from additive private-fixture coverage.

## What the tests prove

| Test | Proves |
| --- | --- |
| `test_defaults_fill_only_absent_selections` | the authority order's lowest two tiers: a policy default only fills a gap; an explicit choice, including an explicitly empty one, is never overwritten |
| `test_required_and_forbidden_validate_without_mutating` | required/forbidden only validate -- a missing requirement or a forbidden selection fails rather than being silently added or dropped |
| `test_multiple_policies_merge_independently_of_order` | the delivery/quality worked example merges to one identical result under every input order; the restricted-delivery pair fails identically under every order too |
| `test_every_documented_detail_code_is_reachable` | all 17 named detail codes across the three structured-failure categories are reachable, not just prose |
| `test_policy_cannot_carry_content_metadata_or_options` | a policy naming a file, project-metadata field, or component option is rejected as `unknown-field` -- the [extension-points.md](extension-points.md) four-surface boundary, executable |
| `test_resolved_selection_renders_a_real_project` | the end-to-end half: a real `ComponentSelection`, a real `ProjectSpec` with recorded `provenance.policies`, and a real `render_project()` result |
| `test_fixture_policies_carry_no_organisation_specific_values` | every checked-in fixture is `example-`-prefixed and references only identifiers a real catalogue has |

## What this does not implement

- No shipped resolver, parser, or public API. `forge_template`'s facade,
  `EngineErrorCode`, and package version (`0.3.2`) are all unchanged.
- No profile implementation. The authority order's lowest tier is modelled
  as a plain keyword argument to the reference resolver
  (`profile_default_archetype` and friends), not a delivered profile
  feature.
- The `no-permitted-archetype` code is exercised for the case this reference
  resolver can produce it -- no archetype resolves at all (no explicit
  choice, no policy default, no profile default) -- not every theoretical
  path organisation-policy.md's prose could be read to imply (for example, a
  policy set that forbids every catalogue archetype without an explicit
  choice). A shipped resolver may need to cover more of that surface; this
  fixture proves the documented rules are internally consistent and
  reachable, not that every edge case is enumerated.

## Ownership and deferred work

`forge-template` owns this fixture and what it proves about
organisation-policy.md and extension-points.md. A downstream client owns its
own resolver implementation, policy-source trust, and ProjectSpec
construction -- this fixture is a reference to build and test against, not a
dependency to import.

The [no-copy inheritance proof](no-copy-inheritance.md) demonstrates that a
downstream client can retain those responsibilities without copying any
Foundation or component source. Its private fixture-catalogue scenario proves
composition mechanics only and creates no supported client injection seam.

A shipped, public resolver remains unscheduled in roadmap v1: Stage 09 is
its final stage, and no issue here or in create-forge currently commits to
one. Until a future ADR changes that, client-side resolution against this
reference is the operative architecture -- see
[ADR 0040](adr/0040-organisation-policy-reference-fixture.md)'s
Consequences.
