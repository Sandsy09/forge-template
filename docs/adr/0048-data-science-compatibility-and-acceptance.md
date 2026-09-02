# 48. Fix the Data Science compatibility, acceptance, and release contract

Date: 2026-09-02

## Status

Accepted

## Context

[ADR 0045](0045-data-science-project-shape.md),
[ADR 0046](0046-initial-data-science-capabilities.md), and
[ADR 0047](0047-notebook-data-and-model-safeguards.md) fixed the Data Science
archetype shape, the `jupyter` and `scientific-python` capabilities, and the
fail-closed notebook safeguards. Each one explicitly deferred compatibility
classification, the acceptance matrix, and release hand-offs to FT-10.04, the
last child of FT-EPIC-10.

Fifteen open issues across Stages 11 to 14 and both repositories depend on
those answers. Without them, FT-11.01 cannot begin without re-deciding which
axes may move, and every later issue would re-derive its own acceptance bar.

Released `create-forge` declares `forge-template>=0.3.1,<0.4`. Below `1.0` a
supported engine range is minor-scoped, so additive catalogue content shipped
inside `0.3.x` would be invisible to that client and could not be made
visible without a range change anyway.

Existing build evidence — `uv run poe archetype` — covers one interpreter
(`development` 3.13) with one `PythonSelection`, and this repository's CI runs
every job on Python 3.13. The roadmap claims a Python 3.11–3.14 acceptance
range that no current test exercises.

## Decision

Adopt the canonical
[Data Science compatibility and acceptance](../data-science-compatibility-and-acceptance.md)
contract.

The Data Science rollout moves exactly two versioned surfaces: the
`forge-template` package version and the set of discovered components.
ProjectSpec protocol `1`, component manifest protocols `1` and `2`,
option-schema protocols `1` and `2`, the Foundation source protocol `1`, the
organisation-policy protocol `1`, and every public engine signature, result
field, and `EngineErrorCode` value are unchanged. The published
extension-point inventory only grows, with no rename or removal. `library` and
`cli` stay at component version `1.0.1`.

The first Data Science engine line is `0.4.0`, reviewed as `0.4.1`. It is a
new minor line rather than a patch because a client opts in at the minor
boundary — `create-forge` moves its extra from `<0.4` to `<0.5` — because a
new discovered component is a client-observable catalogue change, and because
`0.3.x` stays a stable two-archetype line. `data-science`, `jupyter`, and
`scientific-python` each enter at component version `1.0.0`, independent of
the package version and distinct from a generated project's own `0.1.0`
starting version.

Acceptance is an executable matrix of five tables. Every row names one
non-interactive command with a binary outcome and one owner, in this
repository (`poe check`, `poe archetype`, `poe combos`, `poe update`,
`poe check:wheel`, `notebook:check` in the generated project) or in
`create-forge` (its contract, preview-pipeline, and end-to-end suites). A row
is executable when its command exists at the stage that needs it, not when it
passes today. Dependency resolution is swept at Python 3.11 and 3.14 per
capability dependency set; Data Science build, install, import, and
`notebook:check` evidence is required at both endpoints; `library` and `cli`
keep their current single-selection evidence as regression. Endpoint sweeping
is new machinery FT-12.03 builds. A resolution failure at an endpoint is
resolved by an upstream review and a superseding ADR, never a silent bound
change.

The valid selections are `library` or `cli` with any capability subset, and
`data-science` with `jupyter` and optionally `scientific-python`. `data-science`
without `jupyter`, two archetypes, a wrong-kind selection, a duplicate, and an
unknown ID each fail closed as a structured error before rendering.

Four release gates carry explicit entry and exit criteria: `forge-template`
`0.4.0` (FT-12.04), `create-forge` `>=0.4,<0.5` adoption (CF-13.01), reviewed
`forge-template` `0.4.1` (FT-14.03), and `create-forge` `0.3.0` (CF-14.04).
They bind to `create-forge`'s existing four-step release-coordination order
rather than restating it. A per-issue mapping records what each Stage 11 and
12 child may no longer decide.

## Consequences

- FT-EPIC-11 and FT-11.01 are unblocked; the Stage 10 contract set is
  complete and epic FT-EPIC-10 can close.
- `create-forge` cannot see Data Science until it widens its engine range to
  `>=0.4,<0.5`; this is deliberate client-controlled adoption, not a gap.
- FT-12.03 must build Python-endpoint sweep machinery that does not exist
  today; the single-interpreter `poe archetype` is a regression baseline, not
  the acceptance bar.
- A dependency that fails to resolve at Python 3.11 or 3.14 blocks the line
  until an upstream review and a superseding ADR under the capability
  maintenance rules; urgency does not authorise a silent widening.
- The living compatibility-state table stays at `0.3.2` until FT-12.04
  publishes `0.4.0`; this contract merging bumps no version and tags nothing.
- Component version `1.0.0` for the three new components and the generated
  project's `0.1.0` version are separate axes that never move together.
- ADR 0045, 0046, and 0047 are not superseded; this decision classifies what
  they deferred without changing any shape, capability, or safeguard they
  fixed.
- No manifest, dependency, Foundation extension, catalogue entry, generated
  file, public API, protocol, package version, tag, or release changes
  through this decision.
