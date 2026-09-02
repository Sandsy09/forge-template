# Capability composition validation

This document records what the production capability layer is proven to do,
and what it is deliberately not proven to do, once both initial capabilities
exist. It is the canonical result of
[FT-11.04 / #108](https://github.com/Sandsy09/forge-template/issues/108), the
final child of
[FT-EPIC-11](https://github.com/Sandsy09/forge-template/issues/97), adopted by
[ADR 0052](adr/0052-validate-production-capability-composition.md), and proved
by
[`tests/test_capability_composition.py`](../tests/test_capability_composition.py).

FT-11.02 and FT-11.03 each proved one capability in isolation. This issue
proves the *layer*: that `jupyter` and `scientific-python` compose across
every archetype that claims them, that every invalid selection the
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md#valid-and-invalid-selections)
lists fails closed, and that discovery, Foundation neutrality, and packaged
resources all hold under composition. It changes no manifest, no content, no
engine code, and no version.

## What the proof establishes

### Every claimed composition renders

For each archetype in `library` and `cli`, and each capability selection in
none, `jupyter`, `scientific-python`, and both:

- planning and rendering succeed;
- `GenerationPlan.component_order` is the archetype followed by the selected
  capabilities in lexical order — the single order
  [composition-order.md](composition-order.md) fixes;
- every planned file is owned by Foundation or by a selected component, never
  by an unselected one;
- the generated `pyproject.toml` is valid TOML; and
- a capability's owned file (`scripts/check_notebooks.py` for `jupyter`,
  `tests/test_scientific_python.py` for `scientific-python`) appears exactly
  when that capability is selected.

With both capabilities selected, their Foundation contributions compose in
composition order and never last-write-wins: the README gains the Jupyter
guidance before the Scientific Python guidance, runtime dependencies are the
archetype's followed by the four scientific pins, the aggregate `check` array
ends with `notebook:check`, and no `[[forge:extension …]]` marker survives in
any rendered file.

Rendering is deterministic: repeating a render, and supplying the capability
list in the opposite order, both produce byte-identical output.

### Invalid selections fail closed before rendering

Every rejection in the accepted selection table surfaces as a structured
`ForgeEngineError` with a stable `EngineErrorCode`, a populated `details`
list, and a JSON-serialisable `as_dict()`. `render_project` raises the *same*
failure as `plan_generation` — the error's `operation` is `parse` or
`validate`, never `render`, so no content is produced for an invalid
selection.

| Rejected selection | `EngineErrorCode` | `operation` |
| --- | --- | --- |
| The same component listed twice | `INVALID_PROJECT_SPEC` | `parse` |
| One component selected under two kinds | `INVALID_COMPONENT_SELECTION` | `validate` |
| A capability id given as the archetype | `INVALID_COMPONENT_SELECTION` | `validate` |
| An archetype id given as a capability | `INVALID_COMPONENT_SELECTION` | `validate` |
| An unknown component id | `INVALID_COMPONENT_SELECTION` | `validate` |
| An unsatisfied hard `requires` edge | `INVALID_COMPONENT_SELECTION` | `validate` |
| A declared `conflicts` edge | `INVALID_COMPONENT_SELECTION` | `validate` |
| Options for an optionless component | `INVALID_COMPONENT_OPTIONS` | `validate` |
| A missing required option, or a value failing its type or `choices` | `INVALID_COMPONENT_OPTIONS` | `validate` |

The satisfied cases compose: a capability whose `requires` edge is met plans
in composition order, and a valid option value reaches the rendered output.

### Discovery descriptors stay path-free

All four production descriptors expose exactly the published
`ComponentDescriptor` field set, carry no `content_root`, `options_schema`,
`extensions/`, `content/`, `component.toml`, package path, or path separator
in their serialised form, reject attribute assignment, and compare equal and
sorted across repeated `discover_components()` calls.

### Foundation stays neutral, generated projects stay Forge-free

No file under `src/forge_template/foundation/` names a capability, an
archetype, or a domain tool (`jupyter`, `numpy`, `pandas`, `matplotlib`,
`scikit-learn`, and related tokens), and neither does the rendered output of
any capability-free composition. Across every composition, no generated
runtime or development dependency is `forge-template` or `create-forge`, and
no generated module imports `forge_template`.

### Every manifest-declared resource is packaged

Through `importlib.resources` — the accessor the engine itself uses — every
`component.toml`, every file under each `content_root`, each declared
`options_schema`, each `extension_points[].content`, each
`contributions[].content`, and `foundation/foundation.toml` with its
extension-point targets are reachable as package resources.
[`scripts/check_wheel.py`](../scripts/check_wheel.py) additionally asserts the
built wheel ships each component's manifest and `extensions/` tree, closing
the gap where a `[tool.hatch.build.targets.wheel]` `exclude` could publish an
undiscoverable or unusable catalogue.

## The fixture catalogue

The production catalogue cannot express an unsatisfied `requires` edge, a
`conflicts` edge, or a capability option: all four shipped components declare
`requires = []` and `conflicts = []`, and only `library` carries an
`options_schema`. Three synthetic capabilities under
[`tests/fixtures/capability_composition/`](../tests/fixtures/capability_composition/)
fill that gap:

| Fixture | Declares | Exercises |
| --- | --- | --- |
| `requires-jupyter` | `requires = [{ id = "jupyter", version = ">=1,<2" }]` | The hard-dependency edge — the exact shape the future `data-science` archetype declares |
| `conflicts-jupyter` | `conflicts = [{ id = "jupyter" }]` | The conflict branch of selection validation |
| `optioned-tooling` | an `options_schema` with a required and a `choices` option, contributing a task fragment that reads them | Capability option validation and rendering |

They overlay a copy of the real production catalogue through the private
`_CATALOGUE_ROOT_OVERRIDE` test seam, with the real installed Foundation
source left live so the shipped extension points are what gets exercised. This
is the same seam FT-11.01 used. These fixtures are test-only. They are not a
plugin surface, a client catalogue mechanism, or an example of one, and the
override that loads them stays unsupported — as
[ADR 0039](adr/0039-deny-policy-file-overrides.md) and
[no-copy-inheritance.md](no-copy-inheritance.md) already require.

## What this does not prove

This is an in-memory composition proof. It deliberately does not cover:

- **lock resolution or build** of a generated project — owned by FT-12.03's
  `uv run poe archetype` endpoint sweep;
- **notebook execution** — `notebook:check` is a generated-project task, out
  of engine scope, proved by
  [`tests/test_notebook_validator.py`](../tests/test_notebook_validator.py);
- **the `data-science` archetype** — FT-12.01 /
  [ADR 0053](adr/0053-production-data-science-archetype.md) introduced it and
  [`tests/test_data_science_archetype.py`](../tests/test_data_science_archetype.py)
  covers it; the `requires-jupyter` fixture here only rehearses its
  cross-tier dependency edge; and
- **`create-forge` selection UX** — owned by create-forge Stages 13–14.

Those rows in the
[acceptance matrix](data-science-compatibility-and-acceptance.md#the-acceptance-matrix)
carry their own owners and evidence commands.

## Ownership and change process

`forge-template` owns the capability manifests, their content, the
composition rules, and this proof. The proof pins behaviour that later
Data Science work builds on: a change that alters composition order, a
rejection's `EngineErrorCode`, or the packaged-resource set must update this
document and `tests/test_capability_composition.py` together. The public
engine API, package version `0.3.2`, and every protocol version remain
unchanged by this validation.
