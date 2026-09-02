# Data Science Archetype Contract

This document defines the future `data-science` archetype's project shape and
ownership boundaries. It is the canonical living contract accepted by
[ADR 0045](adr/0045-data-science-project-shape.md) for FT-10.01.

The contract is intentionally ahead of implementation. The production engine
catalogue still contains only `library` and `cli`; Stage 12 will implement this
shape after the remaining Stage 10 decisions and the Stage 11 capabilities are
complete. Nothing here changes the direct-Copier Library path.

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
contracts](data-science-capabilities.md) supply its intended variability.
FT-10.04 retains ownership of the complete component, protocol,
engine-package, Python-compatibility, and release classification.

The archetype uses PEP 517 and PEP 621 metadata and must build a wheel and
source distribution. It contributes these classifiers:

- `Typing :: Typed`;
- `Intended Audience :: Science/Research`; and
- `Topic :: Scientific/Engineering`.

It introduces no command entry point, runtime configuration, logging setup,
network behaviour, deployment integration, publication workflow, or shared
runtime framework.

## Reserved generated shape

The future production component owns this minimal tracked shape:

```text
src/<package_name>/__init__.py
src/<package_name>/py.typed
tests/__init__.py
tests/test_smoke.py
notebooks/getting-started.ipynb
```

The package is independent rather than inherited from either existing
archetype. Its root public API initially exports only `__version__`, resolved
from installed distribution metadata with the same deterministic `0.0.0`
fallback used by the existing archetypes. `py.typed` declares inline typing,
and the smoke test owns import and version behaviour.

The starter notebook is tracked, output-free, and uses only the generated
package and Python's standard library. It demonstrates the package-plus-
notebooks boundary without making a scientific stack mandatory. Its exact
executable validation and failure behaviour remain with FT-10.03.

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
[path and resource conventions](paths-and-resources.md). FT-10.03 defines the
retention, secret, generated-artefact, and validation safeguards; this
contract fixes only shape and ownership. Prose uses British spelling, while
the conventional filesystem path remains `artifacts/`.

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
archetype's package or notebook. The future Data Science manifest explicitly
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

This contract deliberately does not decide or implement:

- notebook execution, data/model/secret, and generated-artefact safeguards,
  owned by FT-10.03;
- ProjectSpec, manifest, option-schema, Foundation, component, engine-package,
  Python, acceptance-matrix, or release compatibility, owned by FT-10.04; or
- any production manifest, resource, generated output, CLI behaviour, tag, or
  release, owned by Stages 11–14.

FT-10.02 subsequently accepted the capability identities, dependency bounds,
and formal Jupyter requirement in the canonical [initial capability
contracts](data-science-capabilities.md); those decisions do not alter this
archetype's package or path ownership.
