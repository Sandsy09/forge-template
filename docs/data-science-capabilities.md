# Initial Data Science Capability Contracts

This document defines the future `jupyter` and `scientific-python`
capabilities and their dependency ownership. It is the canonical living
contract accepted by
[ADR 0046](adr/0046-initial-data-science-capabilities.md) for FT-10.02.

The contract is intentionally ahead of implementation. The production engine
catalogue still contains only `library` and `cli`; Stages 11 and 12 will add
the capabilities and Data Science archetype after the remaining Stage 10
decisions are complete. Nothing here changes the direct-Copier Library path.

## Shared component contract

Both capabilities use the existing component model without adding an
applicability field or another protocol:

| Field | `jupyter` | `scientific-python` |
| --- | --- | --- |
| Display name | Jupyter | Scientific Python |
| Kind | `capability` | `capability` |
| Manifest protocol | `2` | `2` |
| Component version | `1.0.0` | `1.0.0` |
| ProjectSpec protocols | `[1]` | `[1]` |
| Generated Python compatibility | `>=3.11` | `>=3.11` |
| Options schema | none | none |
| Requirements | none | none |
| Conflicts | none | none |

The capabilities are independently selectable with Library, CLI Application,
or Data Science. Their manifests do not restrict an archetype by name. A
future compatibility restriction must use the existing component relationship
and version contracts rather than a client-side allowlist.

The proposed manifest metadata is conceptual until Stage 11 packages it. The
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md)
classifies the complete protocol and engine-package picture: both capabilities
enter at component version `1.0.0` on the `forge-template` `0.4.0` line, with
every protocol integer unchanged.

The complete identity and relationship portion of each future manifest is:

```toml
manifest_version = 2
id = "jupyter"
name = "Jupyter"
description = "Notebook authoring, execution, and validation tooling."
kind = "capability"
version = "1.0.0"
content_root = "content"
requires = []
conflicts = []

[compatibility]
projectspec_protocols = [1]
requires_python = ">=3.11"
```

```toml
manifest_version = 2
id = "scientific-python"
name = "Scientific Python"
description = "A core numerical, tabular, plotting, and machine-learning stack."
kind = "capability"
version = "1.0.0"
content_root = "content"
requires = []
conflicts = []

[compatibility]
projectspec_protocols = [1]
requires_python = ">=3.11"
```

Neither manifest has `options_schema`. Contribution blocks are optional
manifest fields and remain absent from these decision-level examples because
FT-11.02 and FT-11.03 own the concrete packaged resources. FT-11.01 has
delivered the three Foundation extension points those contributions target —
`pyproject-development-dependencies`, `pyproject-task-definitions`, and
`pyproject-aggregate-check`
([extension-points.md](extension-points.md#capability-tooling-extends-the-same-foundation-content),
[ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md)).

## Jupyter capability

`jupyter` owns the reusable development-time notebook workflow:

- interactive authoring through JupyterLab;
- the generated project's Python kernel;
- structural notebook parsing and validation;
- programmatic execution of a temporary notebook copy;
- the future `notebook` and `notebook:check` Poe tasks;
- integration of `notebook:check` into the aggregate quality contract; and
- usage guidance contributed to the Foundation-owned root README.

It does not own a notebook. The Data Science archetype owns
`notebooks/getting-started.ipynb`; other archetypes or future components may
own their own notebooks. A selected `jupyter` capability must therefore pass
its future check without side effects when no notebooks exist.

The capability owns these generated development dependencies:

```toml
jupyterlab = ">=4.6,<5"
ipykernel = ">=7.3,<8"
nbclient = ">=0.11,<1"
nbformat = ">=5.11,<6"
```

Each direct dependency has a distinct owned purpose: JupyterLab supplies the
authoring interface, ipykernel supplies the project kernel, nbclient supplies
programmatic execution, and nbformat supplies parsing and structural
validation. They belong to a development dependency group and never enter the
generated distribution's runtime metadata.

Foundation already supplies Ruff as the mandatory lint and format
implementation. Ruff discovers and checks notebooks natively, so `jupyter`
adds no duplicate Ruff dependency, `nbqa`, or competing notebook formatter.
The [Ruff notebook discovery documentation](https://docs.astral.sh/ruff/configuration/#jupyter-notebook-discovery)
is the upstream reference for that choice.

The [notebook, data, and model safeguards](notebook-data-and-model-safeguards.md)
contract fixes the validator's ordering, temporary-copy execution, timeout,
source preservation, deterministic failure identifiers, and safe diagnostics.
FT-11.01 has delivered the additive Foundation extension points for
development dependencies, Poe task definitions, and aggregate-check entries
([extension-points.md](extension-points.md#capability-tooling-extends-the-same-foundation-content)).
FT-11.02 owns the packaged manifest, resources, and implementation that
contribute through them.

## Data Science requires Jupyter

The `data-science` archetype, not `jupyter`, declares the hard relationship:

```toml
requires = [{ id = "jupyter", version = ">=1,<2" }]
```

This direction keeps Jupyter reusable and avoids a dependency cycle. A valid
effective Data Science ProjectSpec explicitly includes both selections; its
component-selection fragment is:

```json
{
  "archetype": "data-science",
  "capabilities": ["jupyter"]
}
```

The engine rejects an omitted hard dependency rather than silently adding it.
A client may explain or preselect a requirement, but the ProjectSpec remains
complete and observable. The cross-tier edge is a selection constraint only:
Foundation and the archetype still compose before capabilities under the
canonical ordering contract.

## Scientific Python capability

`scientific-python` owns one optional, reusable scientific runtime stack:

```toml
dependencies = [
    "numpy>=2.4,<2.5",
    "pandas>=3.0,<4",
    "matplotlib>=3.11,<4",
    "scikit-learn>=1.9,<2",
]
```

These are generated-project runtime dependencies and therefore appear in PEP
621 distribution metadata and resolved lock state. All four are declared
directly because all four are part of the capability's promised user-facing
import surface, even where another package would also install NumPy
transitively. This is not ownership duplication: no archetype or other
capability declares the same dependency.

The capability owns its usage guidance and a future component-owned import
test. It supplies no shared runtime wrapper, dataframe abstraction, model API,
notebook front end, deployment behaviour, or archetype content.

It has no relationship to `jupyter`: projects may select either, both, or
neither when their archetype permits it. Data Science requires Jupyter but
keeps Scientific Python optional, and its standard-library starter notebook
must continue to work without the scientific stack.

## Dependency evidence

The lower bounds were reviewed against official PyPI metadata on 2 September
2026. Each selected lower release accepts Python 3.11:

| Dependency line | Reviewed lower release | `Requires-Python` |
| --- | --- | --- |
| `jupyterlab>=4.6,<5` | [4.6.0](https://pypi.org/pypi/jupyterlab/4.6.0/json) | `>=3.10` |
| `ipykernel>=7.3,<8` | [7.3.0](https://pypi.org/pypi/ipykernel/7.3.0/json) | `>=3.10` |
| `nbclient>=0.11,<1` | [0.11.0](https://pypi.org/pypi/nbclient/0.11.0/json) | `>=3.10.0` |
| `nbformat>=5.11,<6` | [5.11.0](https://pypi.org/pypi/nbformat/5.11.0/json) | `>=3.10` |
| `numpy>=2.4,<2.5` | [2.4.0](https://pypi.org/pypi/numpy/2.4.0/json) | `>=3.11` |
| `pandas>=3.0,<4` | [3.0.0](https://pypi.org/pypi/pandas/3.0.0/json) | `>=3.11` |
| `matplotlib>=3.11,<4` | [3.11.0](https://pypi.org/pypi/matplotlib/3.11.0/json) | `>=3.11` |
| `scikit-learn>=1.9,<2` | [1.9.0](https://pypi.org/pypi/scikit-learn/1.9.0/json) | `>=3.11` |

NumPy needs the narrower minor-line ceiling: [2.4.6 supports Python
3.11](https://pypi.org/pypi/numpy/2.4.6/json), while [2.5.0 requires Python
3.12 or newer](https://pypi.org/pypi/numpy/2.5.0/json). Allowing `>=2.4,<3`
would therefore make a valid Forge Python 3.11 selection fail during lock
resolution. A temporary uv resolution of the combined dependency set against
Python 3.11 also passed during this decision review. The
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md#python-endpoint-checks)
makes the executable Python 3.11 and 3.14 endpoint sweep a required FT-11.02,
FT-11.03, and FT-12.03 acceptance check.

## Selection criteria

A dependency belongs in either initial capability only when it:

1. directly supplies an outcome that capability owns;
2. supports Forge's Python floor across the declared line;
3. resolves with the capability's other direct dependencies through uv;
4. has a maintained stable release line and documented upstream behaviour;
5. can be validated through a non-interactive generated-project check; and
6. has a reviewed upper bound that prevents an unassessed breaking line.

This rejects selection by popularity alone. It also rejects an umbrella
scientific metapackage: the four promised imports remain visible and
independently reviewable. Jupyter's four direct development dependencies are
similarly explicit instead of relying on a broad metapackage whose transitive
surface could move without an ownership decision.

## Maintenance and compatibility

The declared bounds are normative compatibility lines.

- Lock movement within unchanged bounds is routine reviewed maintenance. The
  refreshed lock and canonical locked quality checks provide the evidence.
- Changing any lower or upper bound requires an upstream compatibility review,
  resolution across the accepted Python range, generated lock and capability
  regression evidence, and an explicit component-version assessment under the
  Forge compatibility policy.
- Crossing an accepted upper-bound line requires a superseding ADR. Automated
  dependency updates may not cross it or raise the Python floor silently.
- A security-driven update follows the same fail-closed review. Urgency does
  not authorise an untested bound change or weakening the supported Python
  claim.

Changing generated dependency metadata is observable component content. The
implementing change must therefore version the owning capability consistently
with the canonical component SemVer rules; it must not transfer the dependency
to an archetype or Foundation to avoid that obligation.

## Deferred decisions

This contract does not implement or decide:

- either production manifest or its resources, owned by FT-11.02 and
  FT-11.03; or
- the Data Science production manifest and generated shape, owned by Stage
  12.

FT-10.03 subsequently accepted the notebook validator's ordering, temporary
copy, timeout, source preservation, failure identifiers, and safe
diagnostics in the
[notebook, data, and model safeguards](notebook-data-and-model-safeguards.md)
contract, and FT-10.04 the full compatibility matrix, `0.4.0` engine line,
release hand-offs, and version-axis classification in the
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md).
FT-11.01 subsequently delivered the three Foundation capability-tooling
extension points these contributions target
([extension-points.md](extension-points.md#capability-tooling-extends-the-same-foundation-content),
[ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md)). None
of these decisions changes any dependency or manifest metadata above.

No package dependency, manifest, catalogue entry, public API, ProjectSpec,
template, Copier answer, generated output, tag, or release changes through
this documentation decision.
