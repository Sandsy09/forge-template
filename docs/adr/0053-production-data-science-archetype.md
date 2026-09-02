# 53. Ship Data Science as a production archetype

Date: 2026-09-02

## Status

Accepted

## Context

[ADR 0045](0045-data-science-project-shape.md) fixed the `data-science`
archetype's project shape, fixed choices, reserved file set, and ownership map
as a living contract, explicitly "ahead of the archetype implementation".
[ADR 0048](0048-data-science-compatibility-and-acceptance.md) classified it as
component version `1.0.0` on the `forge-template` `0.4.0` line, requiring five
components to discover in lexical order without any protocol or public-facade
change. [ADR 0049](0049-foundation-capability-tooling-extension-points.md),
[ADR 0050](0050-production-jupyter-capability.md), and
[ADR 0051](0051-production-scientific-python-capability.md) shipped the
reusable capability layer, and
[ADR 0052](0052-validate-production-capability-composition.md) proved that
layer end to end — its synthetic `requires-jupyter` fixture deliberately
rehearsing the exact `requires = [{ id = "jupyter", version = ">=1,<2" }]`
edge this archetype declares.

The production catalogue now holds `library`, `cli`, `jupyter`, and
`scientific-python` but not the third archetype. FT-12.01 is the first Stage 12
child: it must add an independent, package-backed archetype that requires
Jupyter and inherits from neither sibling, without touching the direct-Copier
path, the engine, or the package version.

FT-12.02 owns the starter notebook and the ignored working trees, and with
them the `readme-project-shape` and `gitignore-project-shape` contributions.
FT-12.03 owns the full composition and regression matrix. FT-12.04 publishes
`0.4.0`.

## Decision

Add package-bound component `data-science` version `1.0.0`, using component
manifest protocol `2`, ProjectSpec protocol `1`, and Python compatibility
`>=3.11`. It has no options schema and no conflicts. It declares
`requires = [{ id = "jupyter", version = ">=1,<2" }]`; the archetype, not the
capability, owns that edge, keeping `jupyter` reusable and acyclic.

The archetype owns four generated files under its content tree:
`src/<package>/__init__.py` (resolving `__version__` from installed
distribution metadata with the shared `0.0.0` fallback), `src/<package>/py.typed`,
`tests/__init__.py`, and `tests/test_smoke.py`. The three package-source
files are byte-identical to `library`'s copies and are copied, not shared —
the archetype reads no sibling resource, matching the deliberate duplication
recorded in
[the composition architecture review](../composition-architecture-review.md).

It contributes through four of Foundation's existing archetype-neutral
extension points: `pyproject-build-system` and `pyproject-build-configuration`
fix the `uv-build-static` mode (`uv_build>=0.12,<0.13`),
`pyproject-archetype-metadata` fixes the generated project's `0.1.0` starting
version, and `pyproject-classifiers` contributes `Typing :: Typed`,
`Intended Audience :: Science/Research`, and `Topic :: Scientific/Engineering`.
It contributes no runtime dependency and no entry point.

Selecting `data-science` without `jupyter` is rejected before rendering as
`INVALID_COMPONENT_SELECTION` with `operation` `validate` — the same failure
from `plan_generation` and `render_project`, never `render`. Selecting
`scientific-python` alongside composes the two independent capability
contributions on top of the archetype.

No engine module, public signature, `EngineErrorCode` value, ProjectSpec /
component-manifest / option-schema / Foundation-source protocol integer, or
existing component changes. `library` and `cli` stay `1.0.1`; `jupyter` and
`scientific-python` stay `1.0.0`. The package stays `0.3.2` and untagged;
FT-12.04 publishes the expanded catalogue on the accepted `0.4.0` line.

## Consequences

- Discovery from this source tree returns `cli`, `data-science`, `jupyter`,
  `library`, and `scientific-python` in lexical order. The published `v0.3.2`
  wheel remains the two-archetype line until FT-12.04 publishes `0.4.0`.
- A Data Science project builds a wheel and sdist, installs into an isolated
  environment, imports, reports `__version__` and `py.typed`, and passes its
  own locked `poe check` — including `notebook:check` over an empty notebook
  set — with `jupyter` selected.
- The archetype is unusable without an explicit `jupyter` selection, by
  design. A client may preselect that requirement, but the ProjectSpec stays
  complete and observable.
- `scripts/check_wheel.py` now also asserts the `data-science` manifest,
  content tree, and extension tree ship in the built wheel.
- The starter notebook, the `data/`, `models/`, and `artifacts/` working
  trees, the README and `.gitignore` contributions for that shape, the full
  capability-composition and archetype-regression matrix, and the `0.4.0`
  release remain owned by FT-12.02, FT-12.03, and FT-12.04.
- No `copier.yml` question, `template/` file, Copier answer, public API,
  generated-project runtime dependency, tag, or release changes through this
  decision.
