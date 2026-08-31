# Generated-project validation

This is the canonical living contract for the in-memory validation that every
successful Forge engine render passes. [ADR
0030](adr/0030-generated-project-validation.md) records the decision. The
contract is implemented by the public
`forge_template.validate_rendered_project` function and is invoked
automatically by `render_project` before it returns.

## Boundary

Validation operates on a `ProjectSpec` and immutable `RenderedProject`. It
reads no destination, writes no files, runs no generated command or task, and
uses no network or workstation state. A successful result is therefore safe
for a client to stage, but it does not prove that client-owned filesystem
finalisation succeeded.

`create-forge` owns destination conflicts, adjacent staging directories,
cleanup, finalisation, and user-facing diagnostics. The generated project owns
its normal development and runtime checks after handoff. Validation here is a
generation-time engine responsibility and adds no Forge dependency to the
generated output.

## Public operation

```python
from forge_template import validate_rendered_project

validated = validate_rendered_project(spec, rendered)
```

The function returns the same immutable `RenderedProject` object on success.
`render_project(spec)` calls it before exposing a result, so a client using the
normal rendering operation cannot receive an unvalidated project.

Failures use `ForgeEngineError` with:

- code `generated-project-invalid`;
- operation `validate-output`;
- the safe message `The generated project is invalid.`; and
- all independently detectable failures as deterministic, immutable details.

Details are ordered by path, code, and message. File-related paths begin with
the project-relative target. Clients may present messages, but branch on codes
and paths rather than parsing prose.

## Plan and output integrity

Both `GenerationPlan.files` and `RenderedProject.files` must contain unique
targets in lexical order. Their target sets must be identical: every planned
file exists in the rendered result and the result contains no unplanned file.
These rules make the public plan an exact preview rather than an estimate.

The stable detail codes are:

- `duplicate-plan-target` and `unordered-plan-targets`;
- `duplicate-rendered-target` and `unordered-rendered-targets`;
- `missing-rendered-file` and `unexpected-rendered-file`; and
- `missing-pyproject` when `pyproject.toml` is absent from either side.

## Universal `pyproject.toml` contract

Every generated Forge project plans and renders a root `pyproject.toml`. The
file must be UTF-8, parse as TOML, and contain a `[project]` table.

Two ProjectSpec-owned values are enforced:

- `[project].name` is a non-empty valid Python distribution name and, after
  standard distribution-name normalisation, equals
  `ProjectSpec.project.repository_name`;
- `[project].requires-python` is exactly the single lower bound `>=X.Y`, where
  `X.Y` is `ProjectSpec.python.minimum`.

The exact Python form deliberately rejects extra clauses, exclusions, and
upper caps. It implements the canonical Python support policy without turning
the development upper edge into an artificial consumer cap.

The engine does not require version, description, licence, author, or build
system parity here. Those fields may be archetype-owned, dynamically supplied,
or mapped by later component contracts.

The stable detail codes are `invalid-pyproject-encoding`,
`invalid-pyproject-toml`, `invalid-project-table`, `invalid-project-name`,
`project-name-mismatch`, `invalid-requires-python`, and
`python-requires-mismatch`.

## Template completion

Forge-owned `.jinja` content renders with Jinja `StrictUndefined`, so an
unresolved Forge variable fails as `template-render-failed` before a
`RenderedProject` exists. Output validation additionally rejects any surviving
`[[forge:extension ...]]` sequence with detail code
`unresolved-extension-marker`.

The validator does not scan arbitrary `{{ ... }}` or `{% ... %}` sequences.
Generated projects may intentionally contain syntax for another template,
documentation tool, or runtime system; treating all delimiters as unresolved
Forge input would reject valid content.

## Checks that remain outside this boundary

The engine does not make these universal:

- zero-byte-file policy;
- YAML parsing or GitHub Actions policy;
- secret-example and ignore-file policy;
- git tracking or clean-tree state;
- wheel and sdist contents;
- generated command execution; or
- destination filesystem state.

The released Copier Library scaffold continues to exercise its applicable
checks through `forge_template.render`, combination tests, update tests, and
generated CI, unaffected by the engine catalogue below. FT-08.02 made the
first production component catalogue available under the accepted
[Library archetype contract](library-archetype.md); `tests/test_library_build.py`
(the `archetype` marker) additionally proves wheel/sdist/import/version
outcomes this validator does not check itself (wheel and sdist contents are
explicitly out of this boundary, above). FT-08.04 added the independent CLI
Application archetype, and the
[Stage 08 composition review](composition-architecture-review.md) proves both
shapes against the same validation and ownership boundary.
