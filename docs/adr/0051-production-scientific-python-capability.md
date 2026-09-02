# 51. Ship Scientific Python as a production capability

Date: 2026-09-02

## Status

Accepted

## Context

[ADR 0046](0046-initial-data-science-capabilities.md) defines
`scientific-python` as an optionless, reusable capability that owns a bounded
runtime stack for numerical, tabular, plotting, and machine-learning work.
[ADR 0048](0048-data-science-compatibility-and-acceptance.md) requires that
stack to resolve at the Python 3.11 and 3.14 support endpoints without changing
the engine's protocols or public facade. [ADR
0049](0049-foundation-capability-tooling-extension-points.md) confirms that a
selected capability may contribute through Foundation's existing extension
points without transferring ownership to Foundation.

The production catalogue needs a concrete component that exposes the four
promised imports to generated projects while remaining independent of Jupyter
and every archetype. Its dependencies must be visible in PEP 621 runtime
metadata and committed lock state, and its validation must be owned by the
capability rather than a shared generated runtime module.

## Decision

Add package-bound component `scientific-python` version `1.0.0`, using
component manifest protocol `2`, ProjectSpec protocol `1`, and Python
compatibility `>=3.11`. It has no options schema, requirements, or conflicts
and is independently selectable with Library, CLI Application, and the future
Data Science archetype.

The component contributes `numpy>=2.4,<2.5`, `pandas>=3.0,<4`,
`matplotlib>=3.11,<4`, and `scikit-learn>=1.9,<2` through Foundation's existing
`pyproject-runtime-dependencies` point. These are generated-project runtime
dependencies and part of the capability's public import surface. They do not
become `forge-template` runtime or development dependencies.

The component owns one literal generated file,
`tests/test_scientific_python.py`. It imports `numpy`, `pandas`, `matplotlib`,
and `sklearn` and verifies that each exposes non-empty version metadata. The
existing Foundation pytest task discovers the test, so the capability adds no
task or development dependency. README guidance names the distribution and
import names and explains the locked-environment smoke check.

No runtime wrapper, dataframe abstraction, model API, notebook front end,
deployment behaviour, Foundation extension point, or shared generated module
is added. Selection alongside Jupyter composes the two independent capability
contributions; neither component requires or reads from the other.

The package remains version `0.3.2`; FT-12.04 publishes the expanded catalogue
on the accepted `0.4.0` line. ProjectSpec, component-manifest, option-schema,
Foundation-source, and public engine protocols and APIs remain unchanged.

## Consequences

- Discovery from this source tree returns `cli`, `jupyter`, `library`, and
  `scientific-python` in lexical order. The published `v0.3.2` wheel remains
  the two-archetype line until FT-12.04 publishes `0.4.0`.
- Selecting the capability adds the exact four runtime dependency lines,
  generated import coverage, and guidance; omitting it leaves existing
  Library and CLI Application output unchanged.
- The accepted dependency set resolves at Python 3.11 and 3.14, and generated
  Library and CLI projects run the component-owned import test from committed
  lock state.
- Scientific Python and Jupyter remain independently selectable. Exhaustive
  cross-capability composition and failure validation remain FT-11.04 work.
- Data Science content, create-forge selection, the `0.4.0` release, and the
  reviewed `0.4.1` line remain owned by later roadmap issues.
