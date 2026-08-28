# 30. Validate rendered projects before exposing engine success

Date: 2026-08-28

## Status

Accepted

## Context

The stable engine API can validate a ProjectSpec, plan composition, and render
an immutable in-memory file set. Its current repository checks validate a
Copier scaffold during tests, but no supported engine operation proves the
rendered result before a client receives it. A CLI could therefore report
success or begin filesystem finalisation without an engine-owned check that
the public plan matches the returned files or that universal project metadata
matches the generation request.

Destination validation is not an appropriate substitute. The accepted
two-repository boundary makes `create-forge` responsible for staging and
finalisation while `forge-template` owns generated content and its validity.
Moving this check to a filesystem path would weaken the engine's
side-effect-free contract and force other clients to recreate the rules.

## Decision

Expose `validate_rendered_project(spec, project) -> RenderedProject` from the
top-level package and have `render_project` invoke it before returning. The
operation remains entirely in memory and returns the same immutable result on
success.

Require the generation plan and rendered result to use unique, lexically
ordered targets with exactly matching sets. Require a root UTF-8, valid-TOML
`pyproject.toml` containing a `[project]` table. Its distribution name must
normalise to `ProjectSpec.project.repository_name`, and its
`requires-python` value must be exactly the lower bound selected by
`ProjectSpec.python.minimum`, with no additional clause or upper cap.

Continue to let `StrictUndefined` reject unresolved Forge Jinja variables
during rendering, and reject any Forge extension marker that survives in
UTF-8 output. Do not reject arbitrary Jinja-like delimiters because a
component may intentionally emit syntax for a downstream tool.

Report all independently detectable failures through the existing
`ForgeEngineError` surface using category `generated-project-invalid`,
operation `validate-output`, and deterministic structured details. Do not
promote zero-byte, YAML, provider workflow, secret-file, git, artifact, command
execution, or destination checks into this universal engine boundary.

The complete living contract is
[generated-project-validation.md](../generated-project-validation.md).

## Consequences

- A successful render is also a validated render before any client-owned
  filesystem activity begins.
- Clients share one plan/output and metadata contract without receiving path
  access or a generated-project runtime dependency.
- `pyproject.toml` and its ProjectSpec-aligned name and Python floor become
  universal generated-project invariants.
- Scaffold-specific repository, provider, artifact, and command checks remain
  available without constraining unrelated future archetypes.
- The additive API remains in the first, still-unreleased `0.2.x`
  compatibility line. This decision creates no tag or release.
- Library migration, production manifests, destination staging, CLI
  consumption, and end-to-end generated command execution remain later work.
