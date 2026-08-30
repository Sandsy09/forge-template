# 36. Publish the engine to PyPI, excluding repo-local tooling

## Status

Accepted

## Context

[`create-forge#9`](https://github.com/Sandsy09/create-forge/issues/9) owns
the installable-distribution decision ADR 0010 (in `create-forge`) deferred:
`forge-template` is classified `Private :: Do Not Upload` and has never been
published, so `create-forge` cannot declare a bounded runtime dependency on
it -- PyPI rejects `@ git+...` direct references, and `[tool.uv.sources]` is
a workspace-local `uv` mechanism, stripped from published metadata. Every
document that promises a "first assigned engine range"
([`docs/engine-resolution.md`](https://github.com/Sandsy09/create-forge/blob/main/docs/engine-resolution.md),
[`docs/integration-contract.md`](https://github.com/Sandsy09/create-forge/blob/main/docs/integration-contract.md))
depends on this repository publishing first.

`src/forge_template/`'s package mixes two things that have never had to be
told apart before, because nothing has installed this package outside a full
`uv sync --all-groups` checkout:

- the **public engine facade** -- `engine.py`, `project_spec.py`,
  `composition.py`, `component_manifest.py`, `file_conflicts.py`,
  `foundation_source.py`, `template_variables.py`, and the `foundation/` and
  `components/*/content` trees they compose -- which needs only `jinja2`,
  `packaging`, and `pydantic`, exactly what `[project.dependencies]` already
  declares;
- **this repository's own CI tooling** -- `adr.py`, `render.py`, `schema.py`,
  `github_actions.py` -- which inspects `docs/adr/`, `copier.yml`, and
  `template/`, none of which exist once this package is installed elsewhere,
  and which needs `pyyaml`, present only in the `dev`/`test` dependency
  groups.

[`forge-template#8`](https://github.com/Sandsy09/forge-template/issues/8)
already flagged the `pyyaml` gap as "harmless today... but factually wrong,"
predicting exactly this moment. Its proposed fix -- move `pyyaml` (and
`jinja2`, already declared, and `copier`, which `render.py` does not
actually import) into `[project.dependencies]` -- was written before
publishing was a live decision, when the only known consumer was this
repository's own `uv sync --all-groups`.

## Decision

**Publish `forge-template` to PyPI via Trusted Publishing (OIDC)**, the same
mechanism `create-forge` adopts for itself in
[`create-forge` ADR 0018](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0018-pypi-distribution-and-the-first-engine-range.md).
No stored token; a `pypi` GitHub Environment gates the publish step, added as
a job in `release.yml`, running only when `dry_run` is unset and only after
the tag/release job succeeds.

**Exclude the four CI-tooling modules from the wheel**, rather than
declaring `pyyaml` a runtime dependency as `forge-template#8` proposed.
`[tool.hatch.build.targets.wheel]` gains an `exclude` list naming them by
path. This is a *narrower* fix than #8's: it makes the wheel's dependency
declaration true by removing what it couldn't honestly support, rather than
by adding a dependency (and, transitively, `pyyaml`'s own dependency
footprint) to every engine consumer for four modules that cannot function
outside this checkout regardless. `#8` is closed by this decision, noting its
`copier` claim was stale -- `render.py` never imports `copier`.

Nothing in `forge_template/__init__.py` imports the four excluded modules
today, so the facade needs no change; this decision only changes what ships.
`template/` and `copier.yml` remain git-only content, resolved by Copier
directly from a tag as they always have -- the wheel is a distribution
channel for the *engine*, not a second copy of the template.

**`scripts/check_wheel.py`** (new, `poe check:wheel`, mirroring
`create-forge`'s own) builds into a fresh temporary directory each run and
asserts three things: the facade and content trees are present; the four
tooling modules are absent; and the wheel imports and calls
`discover_components()` successfully in a `uv run --isolated --no-project
--with <wheel>` environment resolving only declared dependencies -- the exact
check that would have caught `#8` before publishing made it a real user-facing
break. Wired into CI as a new `wheel` job, required by `all-green`, and run
again defensively inside the `publish` job itself.

**Version `0.3.1`**, a patch: this changes packaging metadata and repository
tooling, not template output, schema, rendered content, or the public
facade's behavior.

## Consequences

- `pip install forge-template` and `uvx --from forge-template ...` become
  real, for the first time. `create-forge#9`'s native blocker on "no
  installable index release" is cleared.
- The wheel is now a strictly smaller surface than the sdist and the git
  checkout: `adr.py`, `render.py`, `schema.py`, `github_actions.py`, `tests/`,
  `docs/`, and `template/` never leave this repository via PyPI. Editable
  installs (`uv sync --all-groups`) are unaffected -- they resolve `src/` on
  `sys.path` directly, bypassing Hatchling's wheel-build exclusion entirely;
  confirmed by running the full suite unchanged after adding the exclude.
- A future fifth module needing `pyyaml`, or any module that must be both
  wheel-shipped *and* import one of the four excluded modules, requires a
  deliberate decision here, not a silent wheel regression -- `check:wheel`'s
  isolated-import assertion is what would catch it.
- `pyproject.toml`'s classifiers drop `Private :: Do Not Upload` and gain the
  standard alpha/audience/topic set `create-forge` already uses, for
  consistency across the two published packages.
- This decision does not itself assign `create-forge`'s runtime engine range
  or change anything under `src/create_forge/` -- that is
  [`create-forge` ADR 0018](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0018-pypi-distribution-and-the-first-engine-range.md),
  sequenced to land only after this package is live on PyPI.
