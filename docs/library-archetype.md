# Library Archetype Contract

This document defines the additions the Forge `library` archetype makes to
the mandatory [Foundation](foundation-scope.md). It is the canonical living
contract accepted by [ADR 0031](adr/0031-library-archetype-contract.md) and
implemented by FT-08.02
([ADR 0033](adr/0033-migrate-library-production-catalogue.md)).

FT-08.02 implements this contract in the installed engine catalogue at
package version `0.3.0`. It changes no Copier template, question, or
generated output: the released Copier path still renders one monolithic
Library tree, unchanged, and remains the only path `create-forge` consumes
today. `src/forge_template/foundation/` and `src/forge_template/components/library/`
are additive package content that co-exists with `template/` until a later,
deliberate cutover -- see "Current evidence and deferred work" below.

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

The production manifest at `src/forge_template/components/library/component.toml`
has this identity:

| Field | Value |
| --- | --- |
| Manifest protocol | `2` |
| Component ID | `library` |
| Kind | `archetype` |
| Component version | `1.0.0` |
| ProjectSpec protocols | `[1]` |
| Generated Python compatibility | `>=3.11` |
| Requirements | none |
| Conflicts | none |

Component version `1.0.0`, manifest protocol `2`, ProjectSpec protocol `1`,
and the `forge-template` package version (`0.3.0`) are independent
compatibility axes. `discover_components()` returns exactly this one
descriptor today. Foundation is never returned as a component descriptor.

## Library options

Library uses option-schema protocol `2` and declares exactly these options,
at `src/forge_template/components/library/options.schema.json`:

| Option | Type | Default | Validation |
| --- | --- | --- | --- |
| `packaging_mode` | string | `uv-build-static` | one of `uv-build-static`, `hatchling-static`, or `hatchling-vcs` |
| `initial_version` | string | `0.1.0` | `format: "pep440"` |

Option-schema protocol `2` adds an optional `format` field for string options.
Its closed vocabulary contains only `pep440`. Resolution validates and
canonicalises a supplied `initial_version` before rendering (`"1.0"` stays
`"1.0"`, `"v1.0.0"` normalises to `"1.0.0"`), and discovery descriptors expose
the declared format so clients can present accurate guidance. The field does
not accept non-string option types, arbitrary regular expressions, or
application-defined validators. See
[template-variables.md](template-variables.md#declaring-options).

### Legacy Copier answer mapping

The released Copier `build_backend` and resolved `versioning` answers map to
the single `packaging_mode` option as follows:

| Legacy effective answers | `packaging_mode` |
| --- | --- |
| `build_backend = uv_build` | `uv-build-static` |
| `build_backend = hatchling` and versioning absent or `static` | `hatchling-static` |
| `build_backend = hatchling` and versioning `vcs` | `hatchling-vcs` |

`forge_template.map_legacy_library_answers(answers)` implements this table as
a pure, side-effect-free function taking `{"build_backend": ..., "versioning_resolved":
...}` and returning `{"packaging_mode": ...}` -- see
[template-engine-api.md](template-engine-api.md). It performs the mapping
only; replaying it against a specific stored project's answers, and deciding
when to do so, remains `create-forge`'s responsibility. The mapping does not
rename or rewrite Copier's own answers.

## Package and API outcomes

Every Library generation satisfies all of these outcomes in each supported
packaging mode, proven by `tests/test_library_build.py` (the `archetype`
pytest marker, `uv run poe archetype`) building real wheels and sdists for
all three modes:

1. The package lives below `src/<package_name>/` and builds through standard
   PEP 517 metadata expressed with PEP 621 project metadata.
2. The build produces both a wheel and a source distribution.
3. The wheel contains the importable package and its `py.typed` marker.
4. The installed distribution metadata has the requested distribution name,
   canonical initial version, and Python floor.
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
quality contract. `tests/test_library_archetype.py` covers the equivalent
render-level assertions (plan owners, rendered `pyproject.toml` per mode, the
composed file set) in the fast suite, without invoking `uv build`.

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
owners -- none exist in the production catalogue yet. Selecting Library alone
does not silently select them, and today it is the *only* thing a ProjectSpec
can select.

## Implicit Foundation source

Composition uses exactly one package-bound Foundation content source,
declared at `src/forge_template/foundation/foundation.toml` and implemented
by [`forge_template.foundation_source`](../src/forge_template/foundation_source.py).
It is:

- mandatory and applied before every selected component;
- implicit rather than selectable;
- absent from ProjectSpec component selections and component discovery;
- the owner of neutral root files: `pyproject.toml`, `README.md`, `LICENSE`,
  `CONTRIBUTING.md`, `SECURITY.md`, `.gitignore`, `.gitattributes`,
  `.editorconfig`, and `.python-version`; and
- extensible only through reviewed, stable extension points.

`GenerationPlan.component_order` lists selected components only;
Foundation's earlier application is invariant and is not encoded as a
pseudo-component -- see [composition-order.md](composition-order.md).

Library contributes to these stable extension-point targets:

| Target owner | Extension point | Requirement |
| --- | --- | --- |
| Foundation | `pyproject-build-system` | required |
| Foundation | `pyproject-archetype-metadata` | required |
| Foundation | `pyproject-build-configuration` | required |
| Foundation | `readme-project-shape` | required |
| Foundation | `gitignore-project-shape` | required |
| `github` component | `ci-jobs` | only when that (not yet existing) optional component is selected |
| `documentation` component | `api-reference` | only when that (not yet existing) optional component is selected |

`gitignore-project-shape` is additive against the original four-point table:
Library's `hatchling-vcs` packaging mode generates `src/<package_name>/_version.py`
at build time, and this point is where Library ignores it -- empty in the two
static modes. The `github`/`documentation` rows describe stable integration
contracts for components that do not exist in the production catalogue yet;
selecting `library` alone never requires them. An unsupported or absent
target fails under the composition contract rather than disappearing or using
last-write-wins replacement.

`pyproject-library-metadata` was renamed `pyproject-archetype-metadata` when
FT-08.04 needed the same static-version-metadata point for a second, distinct
archetype. FT-08.04 also added three further neutral points on the same
Foundation source -- `pyproject-runtime-dependencies`, `pyproject-classifiers`,
and `pyproject-entry-points` -- that Library never contributes to; see
[cli-application-archetype.md](cli-application-archetype.md).

## Manifest protocol 2 and the discriminated planning owner

Manifest protocol `2` replaces a contribution's component-only target with a
discriminated owner:

```toml
[[contributions]]
extension_point = "pyproject-build-system"
content = "extensions/build-system.toml.jinja"
target.kind = "foundation"
```

or:

```toml
[[contributions]]
extension_point = "ci-jobs"
content = "extensions/ci-jobs.yml.jinja"
target.kind = "component"
target.id = "github"
```

Protocol `1` parsing remains supported for existing component-to-component
fixtures. Production Library uses protocol `2`; no protocol-`1` manifest may
target the implicit Foundation source.

The public planning model replaces `PlannedFile.owner_component_id` with a
discriminated `owner`:

- `FoundationOwner(kind="foundation")`; or
- `ComponentOwner(kind="component", id="<component-id>")`.

`component_order` remains limited to selected components. This owner-field
replacement is an incompatible pre-1.0 facade change, moving the package to
`0.3.0`. ProjectSpec remains protocol `1` because its wire shape and
effective-selection semantics did not change. See
[template-engine-api.md](template-engine-api.md#compatibility-and-current-cutover-boundary).

A content path may also reference template variables --
`content/src/{{ project.package_name }}/py.typed` -- rendered through the
same context as file content before its output target is derived; see
[ADR 0032](adr/0032-render-component-content-paths.md). This is what makes
`src/<package_name>/` representable as owned content at all.

## Current evidence and deferred work

The production catalogue now contains exactly `library`, proven end-to-end:
`discover_components()` returns its descriptor, `plan_generation`/`render_project`
compose Foundation and Library into a real project across all three packaging
modes, and `uv run poe archetype` builds real wheels and sdists from that
output. `template/`'s monolithic Copier tree is untouched and remains the
only path the released `create-forge` CLI consumes; the two co-exist as a
deliberate, documented duplication until a later, separate cutover decision
retires one in favour of the other.

Known, deliberate gaps against the monolithic Copier scaffold's output,
tracked as later work rather than silently claimed complete:

- No `.env.example`, secret-scanning, coverage threshold, or documentation
  site: each belongs to a capability that does not exist in the production
  catalogue yet (`foundation-scope.md`'s neutral-safeguard boundary already
  assigns `.env.example` itself to the consuming component, not Foundation).
- Foundation's quality gate is fixed to `mypy` with no configured coverage
  threshold, since ProjectSpec carries no field yet to vary type-checker
  choice or threshold the way the Copier questions do; this is an accepted
  simplification, not a contract gap, pending a profile or options mechanism
  to reintroduce that choice.
- No GitHub-specific files (workflows, `CODEOWNERS`, issue templates): the
  `github` platform component named in the extension-point table above does
  not exist in the production catalogue yet.

FT-08.03 selected and defined the independent, optionless `cli` reference
shape in the canonical [CLI Application archetype
contract](cli-application-archetype.md). FT-08.04 owns its package-bound
implementation; it neither inherits this component nor changes Library's
contract. CLI exposure, ProjectSpec construction, filesystem finalisation,
and the first supported released engine range remain `create-forge`
responsibilities.
