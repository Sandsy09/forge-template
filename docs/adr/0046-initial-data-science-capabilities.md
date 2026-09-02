# 46. Define Jupyter and Scientific Python as independent capabilities

Date: 2026-09-02

## Status

Accepted

## Context

[ADR 0045](0045-data-science-project-shape.md) defines Data Science as an
independent package-plus-notebooks archetype. It deliberately leaves notebook
tooling and scientific dependencies outside the archetype so those concerns
can be selected and maintained independently.

That boundary still needs concrete capability contracts. Combining every
tool in the archetype would make a large scientific stack mandatory, prevent
Library and CLI Application from reusing notebook tooling, and duplicate
dependency ownership. Choosing unbounded or umbrella dependencies would also
make Python compatibility and maintenance consequences difficult to review.

The contracts must preserve Forge's Python 3.11 floor, existing component
protocols, explicit hard-dependency semantics, and provider-neutral
Foundation while leaving notebook safeguards and the full release acceptance
matrix to their following Stage 10 decisions.

## Decision

Define two optionless manifest-protocol-2 capabilities at component version
`1.0.0`, supporting ProjectSpec protocol `1` and generated Python `>=3.11`.
Both are reusable with every current and planned archetype and declare no
conflicts.

`jupyter` owns notebook authoring and validation tooling. It has no component
requirements and owns JupyterLab `>=4.6,<5`, ipykernel `>=7.3,<8`, nbclient
`>=0.11,<1`, and nbformat `>=5.11,<6` as development dependencies. It reuses
Foundation's Ruff installation and native notebook support. The Data Science
archetype declares `jupyter>=1,<2` as a hard requirement, so an effective
ProjectSpec must include the capability explicitly without engine mutation.

`scientific-python` owns NumPy `>=2.4,<2.5`, pandas `>=3.0,<4`, Matplotlib
`>=3.11,<4`, and scikit-learn `>=1.9,<2` as runtime dependencies. It has no
requirements and remains independently optional. Each package is a direct
dependency because each is part of the capability's promised import surface.

Dependency lines are selected by owned outcome, Python compatibility,
co-resolution, stable upstream maintenance, executable validation, and a
reviewed breaking-line ceiling. Routine lock updates may move inside the
bounds. Any bound change requires compatibility evidence and a component-
version assessment; crossing a ceiling additionally requires a superseding
ADR. The complete contract and dependency evidence live in the canonical
[initial capability reference](../data-science-capabilities.md).

## Consequences

- Data Science requires a reusable notebook workflow without making a
  scientific runtime stack mandatory.
- Library and CLI Application may reuse either capability without client-side
  applicability tables.
- Jupyter tools do not leak into consumer runtime metadata; scientific
  dependencies do not leak into the archetype or Foundation.
- The explicit NumPy 2.4 ceiling retains Python 3.11 support even though the
  subsequent NumPy minor line raises its floor.
- Jupyter owns no notebook, and Scientific Python introduces no shared runtime
  abstraction or model API.
- FT-10.03 still owns notebook and artefact safeguards; FT-10.04 still owns
  the complete compatibility and release acceptance matrix.
- No manifest, dependency, Foundation extension, catalogue entry, generated
  file, public API, protocol, package version, tag, or release changes through
  this decision.
