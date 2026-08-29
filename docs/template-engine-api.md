# Stable template-engine API

This is the canonical living contract for the supported `forge-template`
engine facade. [ADR 0029](adr/0029-stable-template-engine-api.md) records the
decision to expose it. The first compatibility line is package version
`0.2.x`; ProjectSpec and component-manifest protocol versions remain separate
from the package version.

The facade is side-effect-free. It discovers only reviewed components bundled
in the installed wheel, validates an effective ProjectSpec, plans composition,
and renders an immutable in-memory result. It does not choose a destination,
create directories, write files, resolve target conflicts, run tasks, or
finalise a generated repository.

## Supported imports

Clients import supported names from `forge_template`, not from its low-level
modules. The public functions are:

```python
from forge_template import (
    discover_components,
    get_engine_info,
    parse_project_spec,
    plan_generation,
    render_project,
    validate_project_spec,
    validate_rendered_project,
)
```

The package also re-exports the ProjectSpec models needed by typed clients,
the immutable discovery, planning, and rendering result models, and the
structured error types. The wheel includes `py.typed`.

Undocumented names in `forge_template.engine`, `component_manifest`,
`composition`, `file_conflicts`, `project_spec`, and `template_variables` are
implementation details. They may change within the `0.2.x` line when the
supported top-level behaviour remains compatible.

## Engine and protocol information

`get_engine_info() -> EngineInfo` reports:

- the installed `forge-template` package version;
- supported ProjectSpec wire protocols; and
- supported component-manifest protocols.

It never scans the component catalogue. Package SemVer describes compatibility
of the Python facade. ProjectSpec and manifest protocol integers describe
their respective data formats; changing one does not implicitly change the
others.

## Discovery

`discover_components() -> tuple[ComponentDescriptor, ...]` reads the component
catalogue bundled beneath the installed `forge_template.components` package.
It returns immutable descriptors in lexical component-ID order. Descriptors
contain identity, display metadata, kind, component version, protocol and
Python compatibility, requirements, conflicts, and option declarations. They
never reveal package-resource or filesystem paths.

The public API cannot redirect discovery to a remote registry, plugin,
entrypoint, or arbitrary directory. This is a deliberate trust boundary:
discovered manifests, option schemas, templates, and literal content were all
reviewed as part of the installed engine distribution.

The production `0.2.0` catalogue is intentionally empty. Stage 08 will add the
first production manifest when it implements the accepted
[Library archetype contract](library-archetype.md). Consequently,
discovery currently returns an empty tuple and catalogue validation rejects a
ProjectSpec that selects a component. Test-only fixture injection is private
and is not a supported client extension mechanism.

## Parsing and validation

`parse_project_spec(payload) -> ProjectSpec` accepts:

- an existing `ProjectSpec`;
- a JSON-compatible mapping;
- a JSON string; or
- JSON bytes.

It performs strict ProjectSpec protocol and wire validation without reading
the catalogue. It preserves the protocol's no-coercion, no-unknown-field, and
canonical collection rules.

`validate_project_spec(spec) -> ProjectSpec` validates a parsed specification
against the installed catalogue. It checks component existence and kind,
protocol and complete tested-Python-range compatibility, required and
conflicting selections, and manifest-declared component options. It returns
the same immutable specification on success and never adds a dependency or
changes a selection.

Clients that start with wire data call parsing before catalogue validation.
`plan_generation` and `render_project` perform full validation themselves.

## Planning

`plan_generation(spec) -> GenerationPlan` returns the deterministic component
order and a target-sorted immutable file plan. Every planned file identifies
its project-relative target, its owning component, and ordered extension
contributions. It exposes no source or package-resource paths.

Planning applies the canonical [composition order](composition-order.md),
[file conflict rules](file-conflicts.md), and
[template variable contract](template-variables.md). Invalid catalogue
resources, selections, options, output collisions, or extension declarations
fail before any rendering or destination activity.

## Rendering

`render_project(spec) -> RenderedProject` returns the generation plan together
with a target-sorted tuple of `RenderedFile(target, content)`. Content is
always bytes:

- a source without a `.jinja` suffix is copied byte-for-byte;
- a `.jinja` source is decoded and rendered as UTF-8;
- Jinja uses `StrictUndefined`, preserves trailing newlines, performs no
  autoescaping, and has no filesystem include loader; and
- the assembled owner template renders exactly once, so owner and extension
  snippets share the canonical variable context.

Rendering is an in-memory operation. Before returning, it applies the canonical
[generated-project validation](generated-project-validation.md) to the result.
A successful result does not imply that a target directory exists or that any
file has been written.

`validate_rendered_project(spec, project) -> RenderedProject` exposes that
same side-effect-free check directly. It proves exact plan/output target
agreement, the universal ProjectSpec-aligned `pyproject.toml` contract, and
the absence of unresolved Forge extension markers. It returns the same
immutable result on success. Destination staging and finalisation remain
client responsibilities.

## Extension markers

An owner publishes an extension point in its manifest and places exactly one
indented whole-line marker in the corresponding UTF-8 `.jinja` resource:

```text
[[forge:extension <component-point-id>]]
```

Only spaces or tabs may precede the token and nothing except the line ending
may follow it. Each declared point must occur exactly once, and every marker
must name a declared point. Contribution resources must also be UTF-8
`.jinja` templates. Non-empty contributions must end with a newline and may
not contain another extension token.

The engine splices selected contributions in composition order. The marker's
indentation is prepended to each non-empty contribution line. With no selected
contribution the complete marker line is removed. Missing, duplicate,
undeclared, nested, malformed, non-whole-line, non-UTF-8, or non-template
extension resources fail during planning rather than being guessed at.

## Structured failures

Expected engine failures use one public exception, `ForgeEngineError`. It
contains:

- a stable `EngineErrorCode` category;
- the operation that failed;
- a safe human-readable message; and
- an immutable tuple of `EngineErrorDetail` values, each carrying a
  machine-readable code, field or resource path, and message.

The stable categories are invalid ProjectSpec, component discovery or
catalogue failure, invalid selection, invalid component options,
generation-plan failure, template-render failure, and invalid generated
project. TOML, Pydantic,
package-resource, Unicode, Jinja, selection, option, and expected collision
failures are translated into this surface. Unexpected programming defects are
allowed to escape rather than being mislabeled as user input failures.

Messages are diagnostic, not a parsing protocol. Clients branch on the error
code and structured detail paths and may present the safe messages to users.

## Compatibility and current cutover boundary

Within the `0.2.x` package line, documented top-level names, signatures,
result fields, error-code values, and their stated semantics are compatibility
commitments. An incompatible public change requires a package-major version
change after 1.0, or a new minor compatibility line while the package remains
pre-1.0, and always requires migration guidance. Additive result fields are
also treated carefully because strict consumers may serialise these models.

The generated-project validator is an additive part of the first, still
unreleased `0.2.0` API. The current Copier Library path and the released
`create-forge` CLI do not yet
consume this facade. `create-forge` must keep its supported engine range and
protocol support unassigned until its implementation and cross-repository
contract tests pass. This change creates no component manifest, ProjectSpec
field, Copier answer, generated file, destination API, CLI behaviour, tag, or
release.

FT-08.02 will make an explicitly incompatible pre-1.0 planning-model change:
`PlannedFile.owner_component_id` becomes a discriminated `owner` containing
either `FoundationOwner(kind="foundation")` or
`ComponentOwner(kind="component", id=...)`. Foundation still does not appear
in `component_order`. The [Library archetype contract](library-archetype.md)
therefore requires package version `0.3.0` for that implementation while
keeping ProjectSpec protocol `1`. Version `0.2.0` and the current field remain
the supported behaviour until FT-08.02 lands; this decision does not alter the
facade.
