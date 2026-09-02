# Data Science Archetype Contract

This document defines the `data-science` archetype's project shape and
ownership boundaries. It is the canonical living contract accepted by
[ADR 0045](adr/0045-data-science-project-shape.md) for FT-10.01, implemented by
FT-12.01 / [ADR 0053](adr/0053-production-data-science-archetype.md) and
FT-12.02 / [ADR 0054](adr/0054-data-science-notebook-and-artefact-layout.md).

Those two changes ship the archetype in the source catalogue:
`discover_components()` returns `cli`, `data-science`, `jupyter`, `library`,
and `scientific-python` in lexical order. FT-12.01 shipped the manifest, the
owned package and smoke tests, and the four packaging/metadata/classifier
contributions; FT-12.02 shipped the starter notebook, the five ignored working
trees, and the archetype's `readme-project-shape` and `gitignore-project-shape`
contributions. The full composition and regression matrix remains FT-12.03's.
The published `0.3.2` wheel stays the two-archetype line until FT-12.04
publishes `0.4.0`. Nothing here changes the direct-Copier Library path.

## Archetype identity and fixed choices

Data Science is an independent, package-backed, notebook-oriented archetype
composed over the same implicit Foundation as Library and CLI Application.
Its canonical identity and fixed project choices are:

| Concern | Contract |
| --- | --- |
| Component ID | `data-science` |
| Display name | Data Science |
| Component options | none |
| Packaging | `uv-build-static` |
| Build requirement | `uv_build>=0.12,<0.13` |
| Initial version | `0.1.0` |
| Runtime entry point | none |
| Intrinsic runtime dependencies | none |

The fixed choices keep the initial archetype focused on composition rather
than creating another packaging matrix. The canonical [initial capability
contracts](data-science-capabilities.md) supply its intended variability. The
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md)
classifies the complete component, protocol, engine-package,
Python-compatibility, and release picture: `data-science` enters at component
version `1.0.0` on the `forge-template` `0.4.0` line, and the generated
project's own `0.1.0` starting version above is a separate axis.

The archetype uses PEP 517 and PEP 621 metadata and must build a wheel and
source distribution. It contributes these classifiers:

- `Typing :: Typed`;
- `Intended Audience :: Science/Research`; and
- `Topic :: Scientific/Engineering`.

It introduces no command entry point, runtime configuration, logging setup,
network behaviour, deployment integration, publication workflow, or shared
runtime framework.

## Reserved generated shape

The production component owns this minimal tracked shape:

```text
src/<package_name>/__init__.py
src/<package_name>/py.typed
tests/__init__.py
tests/test_smoke.py
notebooks/getting-started.ipynb
```

FT-12.01 shipped the first four; FT-12.02 shipped
`notebooks/getting-started.ipynb`.

The package is independent rather than inherited from either existing
archetype. Its root public API initially exports only `__version__`, resolved
from installed distribution metadata with the same deterministic `0.0.0`
fallback used by the existing archetypes. `py.typed` declares inline typing,
and the smoke test owns import and version behaviour. The `__init__.py`,
`py.typed`, and `tests/__init__.py` files are byte-identical to `library`'s
copies — copied into the archetype's own content tree, never read across
archetypes.

The starter notebook is tracked, output-free, and uses only the generated
package and Python's standard library. It demonstrates the package-plus-
notebooks boundary without making a scientific stack mandatory. Its exact
executable validation and failure behaviour are fixed by the
[notebook, data, and model safeguards](notebook-data-and-model-safeguards.md)
contract.

## Local working trees

The generated README documents these project-root working trees:

```text
data/raw/
data/interim/
data/processed/
models/
artifacts/
```

They contain local or generated working material, not Forge-owned source.
They are ignored through the archetype's contribution to Foundation's root
`.gitignore` and have no tracked `.gitkeep`, README, or other placeholder.
Consequently, a clean checkout does not contain the directories until a user
or selected component creates them.

Forge supplies no path helper, project-root discovery, data loader, model
registry, or artefact API for these locations. Any future runtime owner that
uses them must follow the canonical
[path and resource conventions](paths-and-resources.md). The
[notebook, data, and model safeguards](notebook-data-and-model-safeguards.md)
contract defines the retention, secret, generated-artefact, and validation
safeguards, including the root-anchored ignore entries and the prose-only
guidance reading; this contract fixes only shape and ownership. Prose uses
British spelling, while the conventional filesystem path remains `artifacts/`.

## Ownership map

Each generated concern has one owner, including when multiple owners
contribute to a mixed root file.

| Concern | Owner |
| --- | --- |
| Neutral project identity, licence, prerequisites, lock and quality guarantees, root guidance, and repository hygiene | Foundation |
| Root `pyproject.toml`, `README.md`, and `.gitignore` source files | Foundation, accepting only reviewed component contributions |
| Package and test paths, packaging/version metadata, classifiers, notebook path and content, and working-tree conventions | Data Science archetype |
| Data Science project-shape and working-tree guidance within the root README | Data Science archetype through `readme-project-shape` |
| Data/model/artefact ignore entries within the root `.gitignore` | Data Science archetype through `gitignore-project-shape` |
| Notebook authoring, execution, validation, development dependencies, and tooling guidance | [`jupyter`](data-science-capabilities.md#jupyter-capability) capability |
| Optional scientific runtime dependencies and their import validation | [`scientific-python`](data-science-capabilities.md#scientific-python-capability) capability |
| CI, repository-provider, delivery, and deployment integrations | Selected platform components |
| Default or constrained selections | Profiles and organisation policies, which own no rendered files |
| Discovery-driven input, ProjectSpec construction, staging, lock finalisation, and atomic destination placement | `create-forge` |

Data Science may reuse Foundation extension points and public template
variables. It may not read or contribute through Library or CLI Application
resources, select either archetype, or introduce inheritance between
archetypes. The Jupyter and Scientific Python contracts may contribute their
own files or use declared extension points, but do not gain ownership of the
archetype's package or notebook. The Data Science manifest explicitly
requires `jupyter>=1,<2`; Scientific Python remains optional.

Foundation remains provider-, framework-, organisation-, and domain-neutral.
Neither notebooks, scientific libraries, data/model conventions, nor their
tooling become universal Foundation dependencies.

## Client boundary

`create-forge` discovers component descriptors and constructs an effective
ProjectSpec through the supported public engine facade. It must not copy this
shape, hard-code the `data-science` identifier, recreate component
requirements, or render archetype content itself. The engine remains the
authority for selection, options, compatibility, planning, rendering, and
generated-project validation; the client remains responsible for filesystem
effects and lock finalisation.

The archetype will remain available only through `new --engine-preview` under
the current roadmap. Retiring the direct-Copier Library path requires a
separate decision.

## Deferred decisions

FT-12.01 implemented the manifest, the owned package and smoke tests, and the
four packaging/metadata/classifier contributions. FT-12.02 implemented the
starter notebook, the five ignored working trees, and the
`readme-project-shape` and `gitignore-project-shape` contributions that carry
their guidance and ignore entries. Still owned by later Stage 12 children:

- the full capability-composition and Library/CLI-Application regression
  matrix, and the generated-project restoration and lock evidence — FT-12.03;
- the `0.4.0` engine release, its tag, and PyPI publication — FT-12.04.

FT-10.02 subsequently accepted the capability identities, dependency bounds,
and formal Jupyter requirement in the canonical [initial capability
contracts](data-science-capabilities.md), FT-10.03 the notebook
validation order, working-tree, secret, and generated-artefact safeguards in
the [notebook, data, and model safeguards](notebook-data-and-model-safeguards.md)
contract, and FT-10.04 the versioned-axis classification, executable
acceptance matrix, and release gates in the
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md);
none of the three alters this archetype's package, path, or no-placeholder
ownership.
