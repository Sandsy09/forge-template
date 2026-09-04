# Composition Architecture Review

This is the living record of Forge's production composition reviews. Stage 08
reviewed Library and CLI Application after both became usable through the
public engine; [ADR 0037](adr/0037-two-archetype-composition-review.md)
records the corrections that review accepted. Stage 14 repeats the review
after Data Science, Jupyter, and Scientific Python became real catalogue
entries and create-forge Stage 13 exercised them through the shared preview
pipeline. [ADR 0056](adr/0056-three-archetype-composition-boundary-review.md)
records the accepted result.

## Stage 14 review result

The three-archetype model remains correctly separated. Foundation is implicit,
mandatory, runtime-free, shape-neutral, and provider-neutral. Each archetype
owns a complete primary project shape; Jupyter and Scientific Python own their
optional reusable concerns; create-forge owns selection UX and filesystem
finalisation.

The review found no new production boundary defect. The Stage 08 corrections
remain effective: Foundation contains no package-layout assumption, typed
classifier, coverage or pre-commit capability, component runtime, domain tool,
or client orchestration. Consequently FT-14.01 changes no engine module,
Foundation/component resource, manifest, rendered byte, public signature,
protocol, component version, or package version. It updates the executable
review and the mutable contracts that still described the pre-Data Science
state.

## Selection and ownership

| Selection | Owned contract |
| --- | --- |
| `library` | Package-backed Library shape; three packaging modes and the only production component option schema. No requirements or conflicts. |
| `cli` | Fixed uv-build package, Typer runtime, console/module entry points, command tests, and usage guidance. No options, requirements, or conflicts. |
| `data-science` | Fixed uv-build package, smoke test, starter notebook, scientific classifiers, and local data/model/artefact conventions. Requires `jupyter>=1,<2`; no options or conflicts. |
| `jupyter` | Reusable development-only notebook dependencies, authoring and validation tasks, safe validator, checkpoint ignore rule, and guidance. No options, requirements, or conflicts. |
| `scientific-python` | Reusable optional scientific runtime dependencies, import test, and guidance. No options, requirements, or conflicts. |
| Foundation | Neutral identity, licence, root handoff documents, repository hygiene, development environment, quality commands, and extension targets. It is not selectable. |
| create-forge | Discovery-driven prompts and flags, ProjectSpec construction, compatibility diagnostics, staging, lock resolution, cleanup, and atomic destination placement. |

Library and CLI accept any of: no capabilities, Jupyter, Scientific Python,
or both. Data Science accepts Jupyter or Jupyter plus Scientific Python. These
ten valid compositions plan and render deterministically. Data Science without
Jupyter, an incorrectly typed or duplicate selection, an unknown component,
an invalid option, or an unsatisfied requirement fails through the existing
structured engine errors before rendering.

## Deliberate duplication

The package contains the following byte-identical resources. They remain
separate because ownership and independent evolution matter more than textual
deduplication.

| Resource | Owners | Rationale |
| --- | --- | --- |
| Package-root `__init__.py` | Library, CLI, Data Science | Each archetype owns its public package API and version shim and may evolve it independently. Foundation cannot own generated runtime/package code. |
| `py.typed` | Library, CLI, Data Science | The distribution that publishes inline typing owns its marker. |
| `tests/__init__.py` | Library, CLI, Data Science | Each archetype owns its complete test-package shape. |
| `tests/test_smoke.py` | Library, Data Science | Both currently test import/version behaviour, but their acceptance suites and future domain behaviour are independent. |
| Static project version fragment | CLI, Data Science | Both currently start generated projects at `0.1.0`; initial version remains an archetype packaging decision. |
| uv-build configuration fragment | CLI, Data Science | Both currently use the same fixed `src/` packaging layout; Library's configurable packaging contract proves this is not universal. |
| uv-build system fragment | CLI, Data Science | Both select the same backend today, but backend selection defines the archetype rather than Foundation. |

Extracting any row into Foundation would make it package-shaped. Making one
archetype read another's resource would create inheritance and hidden coupling.
A new capability would add selection complexity without independent user
value. The review tests therefore pin current byte equality and distinct
`ComponentOwner` attribution while allowing a later accepted decision to let
the copies diverge.

The seven groups add 892 raw bytes beyond keeping one copy of each distinct
resource. That cost is accepted and small relative to the clarity of complete
component ownership.

## Extension-point ownership

Foundation owns the three mixed root targets and publishes eleven stable
extension points. Components own only the fragments they contribute; no
production component publishes another point or may override a target.

| Extension point | Contributors | Why it remains separate |
| --- | --- | --- |
| `pyproject-build-system` | Library, CLI, Data Science | Build backend and requirements are archetype packaging choices. |
| `pyproject-archetype-metadata` | Library, CLI, Data Science | Version/dynamic-version metadata belongs to the selected archetype. |
| `pyproject-build-configuration` | Library, CLI, Data Science | Backend configuration follows the archetype's package layout. |
| `pyproject-runtime-dependencies` | CLI, Scientific Python | Runtime dependencies belong to the behaviour that imports them. |
| `pyproject-classifiers` | Library, CLI, Data Science | Typed, console, and scientific classifiers describe owned project shapes. |
| `pyproject-entry-points` | CLI | Executable entry points belong only to the executable archetype. |
| `pyproject-development-dependencies` | Jupyter | Notebook tooling is optional development behaviour. |
| `pyproject-task-definitions` | Jupyter | Notebook commands exist only with their owning capability. |
| `pyproject-aggregate-check` | Jupyter | The capability extends the universal gate with its own validation. |
| `readme-project-shape` | All five components | Each selected owner appends only its project-shape or usage guidance. |
| `gitignore-project-shape` | Library, Data Science, Jupyter | Generated-version, working-tree, and checkpoint rules stay with their owners. |

The inventory needs no new point. Contributions compose in tier and lexical
order; an unfilled point emits zero bytes. The Foundation-owned target remains
one `PlannedFile`, and every fragment remains a `PlannedExtension` attributed
to its selected component.

## Determinism and validation

- `discover_components()` returns the path-free, lexically ordered tuple
  `("cli", "data-science", "jupyter", "library", "scientific-python")`.
- ProjectSpec protocol `1` expresses exactly one archetype, ordered component
  kinds, and namespaced options. Catalogue validation remains the authority
  for kinds, compatibility, requirements, conflicts, and option schemas.
- Planning orders the archetype before capabilities and orders capabilities
  lexically. Repetition, input reordering, catalogue filesystem order, and
  `PYTHONHASHSEED` do not move the plan or rendered bytes.
- Rendering remains side-effect-free and in memory. Every returned project has
  passed plan/output, universal `pyproject.toml`, and extension-completion
  validation.
- Generated-project tests retain real lock, build, install, import, typing,
  task, and notebook execution evidence at Python 3.11 and 3.14. Library and
  CLI output remains byte-pinned across all capability selections.

## Operational consequences

| Concern | Review conclusion and evidence |
| --- | --- |
| Security | Foundation keeps only neutral secret ignores and reporting guidance. Jupyter validates and executes discarded temporary copies with safe diagnostics; Scientific Python adds runtime packages only when selected. No component gains override, plugin, policy, provider, or client authority. |
| Reproducibility | Engine plans and renders are deterministic; create-forge resolves `uv.lock` in staging before atomic finalisation; generated checks run from committed lock state. This remains declared-input repeatability, not a byte-identical-build promise. |
| Package size | A 2026-09-04 local `uv build --wheel` produced a 72,566-byte wheel. Foundation and the five component trees contain 39,182 raw bytes across 60 files, including 892 bytes of deliberate duplicate overhead. `poe check:wheel` verifies every required resource remains packaged and repository-only tooling remains excluded. |
| Maintenance | Eight bounded direct dependencies are split by owner: four Jupyter development dependencies and four Scientific Python runtime dependencies. Bound changes require owner-specific compatibility review and Python-endpoint evidence. Duplicate files may diverge only through an explicit reviewed component change. |

## Client boundary

create-forge Stage 13 now consumes the public facade behind
`new --engine-preview`. Its current `main` branch declares
`forge-template>=0.4,<0.5`, derives selections and required-capability hints
from descriptors, constructs ProjectSpec protocol `1`, and sends invalid
selections to the engine unchanged. Its shipped modules contain no hard-coded
production component identifier or copied catalogue rule.

The latest released create-forge remains `0.2.1` with the older
`forge-template>=0.3.1,<0.4` range. The future `0.3.0` release adopts the
reviewed `0.4` line only after forge-template `0.4.1` is published. This does
not change the direct-Copier Library path.

Lock resolution remains a client-finalisation artefact. `render_project()`
does not perform network or filesystem work; create-forge writes into an
adjacent staging directory, resolves `uv.lock`, and exposes the destination
only after success. Failure removes staging and leaves the destination
untouched.

## Compatibility and FT-14.02 handoff

FT-14.01 hands the following decision-complete candidate to FT-14.02:

| Axis | Reviewed value |
| --- | --- |
| Source package version | `0.4.0`; FT-14.03 alone bumps and publishes `0.4.1` |
| ProjectSpec protocols | `(1,)` |
| Component manifest protocols | `(1, 2)` |
| Option-schema protocols | `(1, 2)` |
| Foundation source protocol | `1` |
| Components | `library`/`cli` `1.0.1`; `data-science`/`jupyter`/`scientific-python` `1.0.0` |
| Extension points | The unchanged eleven-entry inventory above |
| Public facade and errors | Unchanged signatures, result fields, and `EngineErrorCode` values |
| Generated output | Unchanged; existing regression digests remain authoritative |

FT-14.02 may start when #113 is merged, ADR 0056 is accepted, create-forge
Stage 13 remains complete, and both repositories' `main` branches are clean
and synchronised. Its inputs are the `forge-template 0.4.0` source catalogue,
the create-forge `forge-template>=0.4,<0.5` preview range, ProjectSpec protocol
`1`, component-manifest protocols `(1, 2)`, option-schema protocols `(1, 2)`,
Foundation source protocol `1`, the five component versions above, and the
unchanged eleven-point inventory.

FT-14.02 must validate current forge-template and create-forge `main` together
through the local sibling source, exercise all accepted Data Science
compositions plus Library and CLI, confirm deterministic failure cleanup,
re-check wheel resources and measured size, and record evidence without an
unpublished registry dependency. It must not tag, release, change the client
dependency range, or alter the default Copier path.

## FT-14.02 executed the handoff

[ADR 0057](adr/0057-validate-the-cross-repository-data-science-line.md)
records FT-14.02's result: a paired local install of both `main` branches —
never PyPI — generates and passes its own checks for all ten valid
compositions, fails the documented rejections closed with no partial
destination, and reproduces this review's package-size figures exactly
(60 files, 39,182 bytes, 892 bytes of duplicate overhead), now pinned by
`tests/test_composition_architecture_review.py`. `create-forge`'s own
canonical `tests/test_engine_cross_repository.py` passes against the same
pair. See
[cross-repository-validation.md](cross-repository-validation.md) for the
exact commands, revisions, and outcomes. The candidate above is unchanged;
FT-14.03 alone bumps and publishes `0.4.1`.
