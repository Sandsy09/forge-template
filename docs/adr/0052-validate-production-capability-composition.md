# 52. Validate production capability composition

Date: 2026-09-02

## Status

Accepted

## Context

[ADR 0049](0049-foundation-capability-tooling-extension-points.md) published
the capability-tooling extension points, [ADR
0050](0050-production-jupyter-capability.md) shipped `jupyter` `1.0.0`, and
[ADR 0051](0051-production-scientific-python-capability.md) shipped
`scientific-python` `1.0.0`. Each proved its own component in isolation. ADR
0051 states explicitly that "exhaustive cross-capability composition and
failure validation remain FT-11.04 work".

[ADR 0048](0048-data-science-compatibility-and-acceptance.md) fixed a
valid/invalid selection set and an acceptance matrix whose "invalid
selections fail closed" and "descriptor results contain no filesystem or
package-resource path" rows are owned by FT-11.04. Two gaps make this more
than coverage. First, three of the nine documented rejection cases —
unsatisfied `requires`, a `conflicts` edge, and capability option validation —
are unreachable through the production catalogue, because all four shipped
components declare `requires = []`, `conflicts = []`, and only `library`
carries an `options_schema`. Second,
[`scripts/check_wheel.py`](../../scripts/check_wheel.py) asserted only each
component's `content/` prefix, so a build-exclude change could drop a
`component.toml`, an `extensions/` tree, or `library/options.schema.json` and
still pass while publishing an unusable catalogue.

Stage 12 builds the `data-science` archetype on this layer. It needs the
layer proven on evidence, not assertion.

## Decision

Add [capability-composition-validation.md](../capability-composition-validation.md)
as the living contract and prove it with
[`tests/test_capability_composition.py`](../../tests/test_capability_composition.py).
The document cites the accepted selection table rather than restating it.

The proof covers, in memory, every archetype-and-capability composition the
contracts claim: planning and rendering succeed, `component_order` is the
single fixed composition order, ownership stays within the selection, both
capabilities' Foundation contributions compose in composition order without
last-write-wins, and rendering is deterministic under repetition and
reordering. It asserts every documented rejection surfaces as a structured
`ForgeEngineError` with a stable `EngineErrorCode` before any content renders
— `render_project` raises the same failure as `plan_generation`. It asserts
the four production descriptors are immutable and carry no path, that
Foundation and every capability-free render name no capability or domain tool,
and that no composition makes a generated project depend on a Forge package.

Add three test-only synthetic capabilities under
`tests/fixtures/capability_composition/` — `requires-jupyter`,
`conflicts-jupyter`, and `optioned-tooling` — overlaying a copy of the real
production catalogue through the existing `_CATALOGUE_ROOT_OVERRIDE` seam with
the real installed Foundation left live. `requires-jupyter` declares the exact
`requires = [{ id = "jupyter", version = ">=1,<2" }]` edge the future
`data-science` archetype will carry.

Extend `scripts/check_wheel.py`'s `_MUST_CONTAIN` to require
`foundation/foundation.toml` and, for every component, its `component.toml`,
`content/`, and `extensions/` tree, plus `library/options.schema.json`. Add a
fast `importlib.resources` traversal asserting every manifest-declared
resource is reachable as a package resource.

Do not add a production component, manifest, content file, engine module,
public signature, `EngineErrorCode`, option schema, or any version bump. Do
not present the synthetic fixtures or the override that loads them as a
plugin, registry, or client catalogue mechanism.

## Consequences

- The capability layer is executable evidence: `jupyter` and
  `scientific-python` are proven to compose across `library` and `cli`, and
  every documented invalid selection is proven to fail closed before
  rendering.
- The three synthetic fixtures rehearse the `requires`, `conflicts`, and
  option paths the production catalogue cannot reach; `requires-jupyter`
  de-risks the `data-science` dependency edge FT-12.01 implements.
- `scripts/check_wheel.py` now fails if a build-exclude change drops a
  manifest, an `extensions/` tree, or an `options.schema.json`, and CI's
  `wheel` job enforces it on every push.
- The proof pins composition order, each rejection's `EngineErrorCode`, and
  the packaged-resource set; a later change to any of them must update the
  contract and the test together.
- FT-EPIC-11's six acceptance criteria are all met; Stage 11 and its
  milestone close, and FT-12.01 becomes actionable.
- No package version, protocol integer, component version, manifest,
  dependency, catalogue entry, public API, generated file, tag, or release
  changes through this decision.
