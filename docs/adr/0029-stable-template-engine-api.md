# 29. Expose a stable, side-effect-free template-engine API

Date: 2026-08-27

## Status

Accepted

## Context

ProjectSpec protocol v1, component-manifest protocol v1, deterministic
composition, file-conflict rules, the template-variable contract, and their
composition fixtures now form an executable low-level engine contract. They
did not provide a supported client boundary: callers would have needed to
import internal helpers, handle unrelated exception types, discover source
paths, and reproduce the transition from validation through rendering.

`create-forge` needs one typed integration surface that can be versioned
independently from the ProjectSpec and manifest data protocols. The engine must
also keep reviewed package content inside its trust boundary and return output
without taking ownership of CLI prompting, destination safety, filesystem
writes, task execution, or repository finalisation.

The production Library scaffold is still monolithic. Publishing a Library
component manifest as part of this API issue would combine the engine boundary
with the separate Stage 08 migration and would make it harder to prove that
discovery is package-bound and empty before that migration.

## Decision

Expose the supported facade from the top-level `forge_template` package:
`get_engine_info`, `discover_components`, `parse_project_spec`,
`validate_project_spec`, `plan_generation`, and `render_project`. Re-export the
ProjectSpec models and immutable discovery, plan, result, and error models
needed by typed clients, and mark the wheel with `py.typed`. Low-level module
helpers remain implementation details.

Make `0.2.x`, beginning with project version `0.2.0`, the first compatibility
line for this Python API. Package SemVer governs that facade; ProjectSpec and
component-manifest protocol integers continue to version their own wire
formats. The release workflow derives `v<project-version>` solely from
`pyproject.toml`, rejects an existing or non-increasing version, and retains a
dry-run mode. A reviewed project-version change is therefore required before
release. This decision creates no tag or release.

Discover only the installed `forge_template.components` package and return
lexically sorted, path-free descriptors. Do not expose public catalogue-root
injection, remote registries, arbitrary directories, or plugins. Ship that
namespace empty until Stage 08 migrates Library.

Parse ProjectSpec wire inputs strictly and validate effective selections
against the installed catalogue without mutation. Planning returns immutable
component order plus target, owner, and extension metadata. Rendering returns
the plan plus target-sorted in-memory bytes and performs no destination or
finalisation work.

Copy literal resources byte-for-byte. Render UTF-8 `.jinja` resources with
`StrictUndefined`, trailing-newline preservation, no autoescaping, and no
filesystem include loader. A manifest-declared extension point uses one
indented whole-line `[[forge:extension <component-point-id>]]` token in its
owner template. Validate the owner and snippets as UTF-8 `.jinja` resources,
reject malformed or nested tokens, require non-empty snippets to end in a
newline, splice snippets in composition order using the marker indentation,
remove unused marker lines, and render the assembled owner once.

Translate expected ProjectSpec, TOML, Pydantic, package-resource, selection,
option, collision, Unicode, and Jinja failures into `ForgeEngineError`. Give
it a stable category, operation, safe message, and immutable structured
details containing code, path, and message. Do not catch unexpected
programming defects as if they were user-correctable engine failures.

The complete living contract is
[template-engine-api.md](../template-engine-api.md).

## Consequences

- Typed clients can inspect compatibility, discover reviewed components,
  validate ProjectSpec, preview composition, and render content through one
  supported boundary.
- The production catalogue is intentionally empty, so a real component
  selection fails until Stage 08 supplies packaged manifests.
- Generated projects remain independent: the engine returns bytes but does
  not become a generated runtime dependency.
- Destination conflict handling, file writes, task execution, and repository
  finalisation stay with the integrating client.
- `create-forge` cannot claim protocol or engine compatibility merely because
  the facade exists; its dependency range remains unassigned until its own
  implementation and cross-repository tests pass.
- The current Copier schema, template tree, generated output, and released CLI
  behaviour remain unchanged.
