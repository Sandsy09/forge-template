# Library Archetype Contract

This document defines the additions the Forge `library` archetype makes to
the mandatory [Foundation](foundation-scope.md). It is the canonical living
contract accepted by [ADR 0031](adr/0031-library-archetype-contract.md).

The contract is an implementation requirement for
[FT-08.02](https://github.com/Sandsy09/forge-template/issues/41), not a claim
about the current engine catalogue. Today the released Copier path still
renders one monolithic Library tree, the installed engine catalogue is empty,
and `forge-template` remains at package version `0.2.0`. This decision changes
no template, Copier answer, ProjectSpec payload, generated file, or public
Python API.

## Archetype boundary

Library is the distributable Python-package shape composed over Foundation.
It owns only concerns that are specific to building, importing, typing, and
validating a reusable Python distribution:

- a `src/<package_name>/` package layout;
- PEP 517 build-system and PEP 621 project metadata contributions;
- wheel and source-distribution builds;
- an inline-typing marker at `src/<package_name>/py.typed`;
- package version exposure and package-focused smoke tests; and
- packaging-mode-specific build configuration.

Foundation remains mandatory and owns neutral project identity, root guidance,
repository hygiene, the declared development and quality environment, and the
aggregate validation outcomes. Mixed files do not transfer concern ownership:
Foundation owns the root `pyproject.toml` and README sources, while Library
contributes reviewed sections through their declared extension points.

The initial Library component adds no runtime dependency. A future capability
that contributes runtime behaviour owns its own dependency and conventions;
Library does not become a shared runtime layer.

## Production component contract

FT-08.02 must add a package-bound production manifest with this identity:

| Field | Required value |
| --- | --- |
| Manifest protocol | `2` |
| Component ID | `library` |
| Kind | `archetype` |
| Component version | `1.0.0` |
| ProjectSpec protocols | `[1]` |
| Generated Python compatibility | `>=3.11` |
| Requirements | none initially |
| Conflicts | none initially |

Component version `1.0.0`, manifest protocol `2`, ProjectSpec protocol `1`,
and the `forge-template` package version are independent compatibility axes.
The production manifest is discoverable as an archetype only after FT-08.02
implements it. Foundation is never returned as a component descriptor.

## Library options

Library uses option-schema protocol `2` and declares exactly these initial
options:

| Option | Type | Default | Validation |
| --- | --- | --- | --- |
| `packaging_mode` | string | `uv-build-static` | one of `uv-build-static`, `hatchling-static`, or `hatchling-vcs` |
| `initial_version` | string | `0.1.0` | `format: "pep440"` |

Option-schema protocol `2` adds an optional `format` field for string options.
Its initial closed vocabulary contains only `pep440`. Resolution must validate
and canonicalise a PEP 440 value before rendering, and discovery descriptors
must expose the declared format so clients can present accurate guidance.
The field does not accept non-string option types, arbitrary regular
expressions, or application-defined validators.

### Legacy Copier answer mapping

The current `build_backend` and resolved versioning answers map to the new
single option as follows:

| Legacy effective answers | `packaging_mode` |
| --- | --- |
| `build_backend = uv_build` | `uv-build-static` |
| `build_backend = hatchling` and versioning absent or `static` | `hatchling-static` |
| `build_backend = hatchling` and versioning `vcs` | `hatchling-vcs` |

FT-08.02 owns replay-compatible migration of stored Copier answers. The
mapping does not rename or rewrite answers in this decision.

## Package and API outcomes

Every Library generation must satisfy all of these outcomes in each supported
packaging mode:

1. The package lives below `src/<package_name>/` and builds through standard
   PEP 517 metadata expressed with PEP 621 project metadata.
2. The build produces both a wheel and a source distribution.
3. The wheel contains the importable package and its `py.typed` marker.
4. The installed distribution metadata has the requested distribution name,
   canonical initial version, Python floor, and expected dependency metadata.
5. Importing the package succeeds, and its package-root `__version__` resolves
   from installed distribution metadata. When metadata is unavailable, it
   retains the deterministic `0.0.0` fallback.
6. The initial root public API exports only `__version__`. Future public
   modules deliberately define and document `__all__`; re-exporting their
   names from the package root is optional rather than automatic.

Library-specific validation therefore covers imports and version behaviour,
artifact metadata, wheel contents, wheel and sdist construction, and all three
packaging modes. These checks extend rather than replace the universal
[generated-project validation](generated-project-validation.md) and Foundation
quality contract.

## Publication boundary

Library always builds and validates its artifacts, but publication is
optional and outside this archetype contract. The archetype provides no:

- upload command or publish workflow;
- package-index selection or credentials;
- artifact signing; or
- provenance attestation.

A future capability may own provider-neutral packaging or release concerns,
and a platform may own provider-specific delivery, credentials, signing, or
attestation integration. Those contributions must use declared extension
points. The [supply-chain provenance contract](supply-chain-provenance.md)
continues to govern the exit criteria for that future work.

Optional documentation sites, changelogs, coverage reporting,
dependency-update automation, pre-commit feedback, configuration examples,
and GitHub-specific files remain with their existing capability or platform
owners. Selecting Library alone does not silently select them.

## Implicit Foundation source

Future composition uses exactly one package-bound Foundation content source.
It is:

- mandatory and applied before every selected component;
- implicit rather than selectable;
- absent from ProjectSpec component selections and component discovery;
- the owner of neutral root files such as `pyproject.toml` and `README.md`;
  and
- extensible only through reviewed, stable extension points.

`GenerationPlan.component_order` continues to list selected components only;
Foundation's earlier application is invariant and is not encoded as a
pseudo-component.

Library contributes to these stable extension-point targets:

| Target owner | Extension point | Requirement |
| --- | --- | --- |
| Foundation | `pyproject-build-system` | required |
| Foundation | `pyproject-library-metadata` | required |
| Foundation | `pyproject-build-configuration` | required |
| Foundation | `readme-project-shape` | required |
| `github` component | `ci-jobs` | only when that optional component is selected |
| `documentation` component | `api-reference` | only when that optional component is selected |

The optional target names describe stable integration contracts, not
production manifests introduced by this decision. An unsupported or absent
target must fail under the composition contract rather than disappear or use
last-write-wins replacement.

## Protocol and public API migration for FT-08.02

Manifest protocol `2` replaces a contribution's component-only target with a
discriminated owner:

```toml
[contributions.target]
kind = "foundation"
```

or:

```toml
[contributions.target]
kind = "component"
id = "github"
```

Protocol `1` parsing remains supported for existing component-to-component
fixtures. Production Library uses protocol `2`; no v1 manifest may target the
implicit Foundation source.

The public planning model must likewise replace
`PlannedFile.owner_component_id` with a discriminated `owner` value:

- `FoundationOwner(kind="foundation")`; or
- `ComponentOwner(kind="component", id="<component-id>")`.

`component_order` remains limited to selected components. The owner-field
replacement is an incompatible pre-1.0 facade change, so FT-08.02 must move
the package to `0.3.0`. ProjectSpec remains protocol `1` because its wire
shape and effective-selection semantics do not change.

These manifest, option-schema, descriptor, catalogue, planning-model, and
package-version changes are accepted requirements for FT-08.02. None is
implemented by FT-08.01.

## Current evidence and deferred work

The monolithic Library scaffold already demonstrates the requested package
shape, three effective packaging modes, artifact builds, inline typing,
version exposure, and package-focused checks. It does not demonstrate
Foundation/archetype separation or public-engine production discovery.

FT-08.02 owns that migration and its Copier compatibility. FT-08.03 retains
ownership of selecting and defining the deliberately unnamed second
archetype. CLI exposure, ProjectSpec construction, filesystem finalisation,
and the first supported released engine range remain `create-forge`
responsibilities.
