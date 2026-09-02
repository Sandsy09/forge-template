# 45. Define Data Science as an independent package-plus-notebooks shape

Date: 2026-09-02

## Status

Accepted

## Context

[ADR 0044](0044-plan-data-science-as-the-third-archetype.md) selected a
package-backed, notebook-oriented Data Science project as Forge's next
archetype direction, but deliberately left its exact shape and ownership to
Stage 10. Without that boundary, implementation could duplicate an existing
archetype, put domain concerns into Foundation, couple the project to one
scientific stack, or make `create-forge` recreate catalogue semantics.

Library and CLI Application already prove that independent archetypes can own
similar package markers and tests without inheriting from each other. The
Stage 08 review also established that Foundation owns neutral root files and
quality outcomes while archetypes contribute their shape through reviewed
extension points.

The initial Data Science shape must be useful before a scientific stack is
selected, preserve Forge's Python 3.11 floor, and leave notebook tooling,
scientific dependencies, and safeguards separable for their following Stage
10 decisions.

## Decision

Define `data-science` as an optionless, independent archetype with fixed
`uv-build-static` packaging (`uv_build>=0.12,<0.13`) and static initial version
`0.1.0`.

The archetype owns a version-only typed package under `src/<package_name>/`,
its import/version smoke test, and the tracked
`notebooks/getting-started.ipynb` starter. The notebook uses only the generated
package and standard library. The package exports only `__version__`, resolved
from distribution metadata with a deterministic `0.0.0` fallback.

Data Science owns the conventions for ignored `data/raw/`, `data/interim/`,
`data/processed/`, `models/`, and `artifacts/` working trees and documents them
in its contribution to the root README. No placeholders are tracked in those
trees, and Forge supplies no runtime path or data helper.

Foundation continues to own neutral root sources and universal guarantees.
The Data Science archetype contributes its packaging, classifiers, README
shape, and ignore entries through reviewed Foundation extension points. A
future Jupyter capability owns notebook authoring, execution, validation, and
development tooling; a future Scientific Python capability owns the optional
scientific runtime stack. Platforms own provider integrations, inputs own
selection policy, and `create-forge` owns orchestration and filesystem effects.

The complete path and concern assignment is the canonical
[Data Science archetype contract](../data-science-archetype.md). Dependency
lines and formal component requirements remain with FT-10.02, safeguards with
FT-10.03, and compatibility and acceptance versions with FT-10.04.

## Consequences

- Data Science has a minimal useful shape that does not depend on an optional
  scientific stack.
- Package, test, and typing-marker similarities remain deliberate
  archetype-owned duplication; no archetype inheritance or shared runtime
  layer is introduced.
- Notebook content belongs to the primary shape, while its reusable tooling
  remains independently composable.
- Ignored working trees are documented conventions, not tracked empty content
  or runtime APIs.
- Fixed packaging and absent options keep later implementation and client
  prompting bounded.
- Foundation, ProjectSpec, all component protocols, the public engine API,
  the production catalogue, the direct-Copier path, and generated output are
  unchanged by this decision.
