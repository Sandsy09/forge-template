# 35. Implement the CLI Application reference archetype

## Status

Accepted

## Context

[ADR 0034](0034-select-cli-application-reference-archetype.md) selected CLI
Application as the second reference archetype and fully specified it in
[cli-application-archetype.md](../cli-application-archetype.md), without
implementing it: "This decision changes no code, template, schema, answer,
generated output, public API, package version, tag, or release." FT-08.04
([#4](https://github.com/Sandsy09/forge-template/issues/4)) is the
implementation, split into two sequenced pull requests on the same issue,
mirroring how FT-08.02 delivered Library
([ADR 0033](0033-migrate-library-production-catalogue.md)).

The first PR added four extension points to the Foundation-owned
`pyproject.toml` source with no `cli` component yet in existence -- the
isolated proof that they leave Library's output unchanged. This record
covers the second: the actual `cli` production manifest, its content, and
proving the result builds a real, installable, executable Python
distribution with a working console script and `python -m` entry point.

## Decision

**Retire `pyproject-library-metadata`.** Foundation's static-version-metadata
point is renamed the archetype-neutral `pyproject-archetype-metadata`, since
FT-08.03 accepted the same job for a second, distinct archetype rather than a
Library-specific one. Library's contribution and its extension filename move
to the neutral name; Library's *rendered* output is unaffected.

Add three further neutral points to the same Foundation source:
`pyproject-runtime-dependencies` (inside the `project.dependencies` array),
`pyproject-classifiers` (inside the `project.classifiers` array), and
`pyproject-entry-points` (after core project metadata, ahead of
`[build-system]`). Extension markers are whole-line constructs
([engine.py](../../src/forge_template/engine.py)'s `_EXTENSION_TOKEN_RE`), so
an *empty* point erases its own line including the trailing newline. Library
therefore renders `dependencies = [\n]` in place of the previous literal
`dependencies = []` -- structurally identical (`tomllib` parses both to `[]`),
reviewed rather than byte-for-byte, and gains no `classifiers` entries or
`project.scripts` table. `docs/adr/0033` (immutable) still names the old
point; it is not edited.

Add `src/forge_template/components/cli/` (`component.toml` at manifest
protocol `2`, component version `1.0.0`, ProjectSpec protocol `1`,
`requires_python = ">=3.11"`, no `requires`/`conflicts`/`options_schema`;
`content/` owning `src/<package_name>/{__init__,__main__,cli}.py` and
`py.typed`, plus `tests/{__init__.py,test_cli.py}`; seven `extensions/`
contributions covering the three points reused from Library, the four new
neutral points, and `readme-project-shape`).

`cli.py` uses Typer's `@app.callback(invoke_without_command=True)` for the
top-level `--version`/no-argument-help behavior rather than
`no_args_is_help`, whose exit code has moved between upstream Click majors;
the callback explicitly raises `typer.Exit` so exit `0` is guaranteed. Typer
`0.27` ships with no external Click dependency (`uv pip list` after
installing shows no `click` package); `typer>=0.27,<1` is CLI's one direct
runtime dependency, confirmed empirically against a throwaway venv before
authoring the component. The package root exposes only `__version__`,
matching Library's contract; `<package_name>.cli` exposes `app`, never
re-exported from the package root.

`template/` and `copier.yml` are untouched; the new package content is
purely additive. `forge-template` stays package version `0.3.0`.

## Consequences

- The production catalogue now contains `cli` and `library`;
  `discover_components()`, `plan_generation`, and `render_project` compose
  either archetype with Foundation end-to-end, and neither inherits from or
  reads resources from the other.
- `uv run poe archetype` (the `archetype` pytest marker) proves the CLI
  distribution builds a real wheel and sdist, installs, and its console
  script and `python -m <package_name>` both satisfy the documented help,
  `--version`, and `hello` command contract -- not merely rendered text. It
  additionally runs `uv sync --all-groups` and `uv run poe check` inside the
  generated project, proving the generated `cli.py` clears Foundation's own
  `mypy --strict`/Ruff gate rather than only importing successfully; Library's
  existing suite is left as it was.
- Library's `dependencies` array changes shape (not content) as described
  above; a new fast-suite test pins the reviewed invariance directly against
  the parsed TOML.
- `create-forge#10`'s native blocker on a non-empty `cli` catalogue entry is
  cleared; it must consume this component's discovery output rather than
  duplicating its metadata, questions, or rendering rules.
- Known gaps already accepted for Library (no `.env.example`, secret
  scanning, coverage threshold, documentation site, or GitHub-specific files)
  apply identically to CLI, since both compose over the same Foundation.
