# 32. Render component and Foundation content paths

## Status

Accepted

## Context

[ADR 0026](0026-file-conflict-and-override-rules.md) fixed output-target
derivation to "path identity with a trailing `.jinja` stripped" — a purely
literal transform. `docs/file-conflicts.md`'s "Output targets" section states
the same rule and gives no way for a path to vary with the request.

The accepted [Library archetype contract](../library-archetype.md) requires
FT-08.02 to place the distributable package at `src/<package_name>/`, where
`<package_name>` is `ProjectSpec.project.package_name` — a value only known
once a request is resolved. No accepted contract permits a template variable
inside a content path, so this requirement is unexpressible under ADR 0026
alone: a component could name a literal directory, but never one that varies
per project.

## Decision

Render every owned content path — a component's own, and the implicit
Foundation content source's — through the same `StrictUndefined` Jinja
context used for file *content*, before the `.jinja` suffix is stripped:

```text
content/src/{{ project.package_name }}/py.typed
                                  |
                                  v  render_output_path(path, context)
src/credit_risk_utils/py.typed
                                  |
                                  v  output_target(...)
src/credit_risk_utils/py.typed
```

`forge_template.file_conflicts.render_output_path` performs this and
validates the rendered result as a normalised relative POSIX path through
`component_manifest.relative_resource_path` — the same containment rule
already applied to every owned resource. A path referencing an undefined
variable fails the same way undefined content does: before any file
operation, naming the reference. A rendered path that would resolve absolute,
escape via `..`, or produce an empty segment is rejected outright, so a path
variable can never redirect output outside the project tree.

Collision detection (`component_targets`, `resolve_output_plan`'s base
claims) runs on *rendered* targets, not the literal source path. This is
strictly stronger than ADR 0026's original rule, not a relaxation of it: two
components whose literal paths differ can now be caught colliding once
rendered, exactly as two components whose literal paths already matched
always were.

Extension-point `content` paths render the same way when resolving which
target a point's marker lives in — a point's own path is itself one owned
content path, so treating it differently would be an arbitrary exception.

## Consequences

- A content path can fail at plan time (undefined variable, unsafe rendered
  result) in addition to file content already being able to.
- `docs/file-conflicts.md`'s "Output targets" section is updated to state
  rendering explicitly; ADR 0026 is not superseded, only extended.
- This is what makes the Library archetype's `src/<package_name>/` outcome
  representable at all; FT-08.02's production `library` manifest depends on
  it.
- No existing literal (non-templated) content path changes behaviour:
  rendering a path with no `{{ }}` expressions returns it unchanged.
