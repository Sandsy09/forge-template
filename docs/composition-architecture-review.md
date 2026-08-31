# Composition Architecture Review

This is the living record of the Stage 08 review performed after both
production reference archetypes became usable through the public engine and
the `create-forge` reference client. It applies the canonical
[Foundation scope](foundation-scope.md), [component ownership](component-manifests.md),
and [engine API](template-engine-api.md) contracts to concrete Library and CLI
Application output. [ADR 0037](adr/0037-two-archetype-composition-review.md)
records why the resulting boundary changes were accepted.

## Review result

The composition model remains archetype-neutral. `library` and `cli` are
independent selections with no requirement, conflict, inheritance, or
cross-component resource access. Foundation remains implicit and runtime-free;
ProjectSpec protocol `1`, manifest protocol `2`, option-schema protocol `2`,
Foundation protocol `1`, and the public engine facade are unchanged.

The comparison did expose four implementation leaks, all corrected in the
`0.3.2` compatibility line:

| Finding | Previous placement | Accepted correction |
| --- | --- | --- |
| Typed-package classifier | Foundation always emitted `Typing :: Typed`. | Each archetype contributes the classifier through the existing `pyproject-classifiers` point because each owns its `py.typed` marker. |
| Quality target layout | Foundation named `src`, `tests`, and `tests.*`. | Ruff, mypy, and pytest use repository-wide discovery; the aggregate gate remains mandatory without assuming an archetype layout. |
| Coverage | Foundation installed and configured `pytest-cov`. | Removed until a selected capability owns reporting or thresholds. Plain pytest remains the mandatory test gate. |
| Pre-commit feedback | Foundation installed `pre-commit` and described a hook the engine path did not generate. | Removed until a selected capability owns hook configuration. Neutral ignore safeguards remain in Foundation. |

No new extension point is required. The existing classifier point already
expresses typed-distribution ownership, while the layout-neutral tool defaults
remove source/test path data rather than creating another archetype-to-
Foundation configuration channel.

## Deliberate duplication

The two archetypes currently carry byte-identical source templates for their
package-root `__init__.py`, empty `py.typed` markers, and empty test-package
markers. This is deliberate duplication, not a missing shared component:

- each archetype owns its complete primary project shape;
- the package-root API and version shim may diverge independently later;
- `py.typed` belongs to the distribution that ships it; and
- Foundation cannot own package or test-package runtime structure without
  becoming package-shaped itself.

Tests therefore verify both the coincidental equality and the distinct
`ComponentOwner` recorded in each generation plan. Deduplicating those files
would require an explicit future capability with real independent value, not
archetype inheritance or an implicit shared runtime base.

## Lock state and finalisation

Foundation guarantees committed, machine-readable dependency lock state and
automatic drift detection. The generated project exposes `lock:check` and the
canonical aggregate command is `uv run --locked poe check`; the outer
`--locked` prevents uv from silently updating stale state before the check.
Intentional dependency changes use `uv lock`, followed by review and commit.

`render_project()` remains side-effect-free and returns only reviewed,
deterministic component content. A dependency lock is resolved against an
index and therefore cannot truthfully be part of that in-memory render. The
client materialising a successful project must resolve `uv.lock` after writing
the rendered files and before making the destination visible.

The `create-forge` reference client implements that boundary by running
`uv lock` inside its adjacent staging directory before the atomic rename. The
lock is a finalisation artefact, not a `GenerationPlan` or `RenderedProject`
entry. Resolution failure removes staging and leaves the destination
untouched. It creates no `.git`, `.venv`, hook, or Forge runtime dependency.

## Current output contract

Both archetypes retain Ruff formatting/linting, strict mypy coverage of
project-owned Python found from the repository root, pytest discovery, Poe's
aggregate task, deterministic builds, and their archetype-owned tests. Library
continues to build all three packaging modes; CLI continues to build, install,
and execute both its console and module entry points.

The legacy direct-Copier Library path is intentionally unchanged. Its existing
coverage, pre-commit, GitHub, task, answer, and update behavior remains the
monolithic compatibility surface until a coordinated cutover or migration is
accepted separately.

## Compatibility

- `forge-template` package: `0.3.2`;
- `library` component: `1.0.1`;
- `cli` component: `1.0.1`;
- ProjectSpec: protocol `1`;
- component manifests: protocol `2`;
- option schemas: protocol `2`;
- Foundation source: protocol `1`.

The package and component patch increments identify corrected generated
content and ownership. They do not alter selection, schema, planning models,
error codes, or public Python signatures.
