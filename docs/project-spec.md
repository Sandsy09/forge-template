# ProjectSpec Protocol v1

ProjectSpec is the canonical, serialisable description of an effective Forge
generation request. Protocol v1 is owned by `forge-template` and implemented
by the strict Pydantic models in
[`forge_template.project_spec`](../src/forge_template/project_spec.py).

The [stable template-engine API](template-engine-api.md) now parses and
validates this protocol and uses it for deterministic planning and in-memory
rendering. The current Copier path does not consume ProjectSpec, and protocol
1 is not yet a supported `create-forge` integration line.

## Wire contract

ProjectSpec uses a JSON object with snake-case field names and the required
integer `protocol_version` value `1`. Unknown fields, omitted protocol
versions, unsupported protocol versions, and implicit type coercion fail
validation. JSON object key order has no meaning.

The Pydantic models are the single schema source. Consumers may inspect
`ProjectSpec.model_json_schema()` when a JSON Schema representation is useful;
Forge does not commit a second generated schema that could drift.

The top-level object has this shape:

| Field | Type | Meaning |
| --- | --- | --- |
| `protocol_version` | integer literal `1` | ProjectSpec compatibility protocol. |
| `project` | `ProjectMetadata` | Provider-neutral identity and handoff metadata. |
| `python` | `PythonSelection` | Compatibility floor and development interpreter. |
| `components` | `ComponentSelection` | One archetype and the effective optional selections. |
| `provenance` | `SelectionProvenance` | Optional identifiers for defaults and constraints already applied. |
| `component_options` | object | JSON-compatible values namespaced by selected component identifier. |

### Project metadata

`ProjectMetadata` contains:

- a non-empty human-readable `name`;
- `package_name`, using the existing lower-case Python package-name rule;
- `repository_name`, using the existing provider-neutral repository-name rule;
- an optional empty `description` string;
- a non-empty `licence` identifier; and
- zero or more `authors`, each with a non-empty `name` and optional email.

GitHub organisation, repository URL, CODEOWNERS identity, credentials, and the
destination path are deliberately absent. Provider values belong to the
owning platform's options; destination choice and filesystem finalisation
belong to the client constructing the request.

### Python selection

`PythonSelection.minimum` is the generated project's compatibility floor and
`PythonSelection.development` is its development interpreter and tested upper
edge. Both use `major.minor` CPython strings, must be offered by the current
engine release, and must satisfy `minimum <= development`.

The current offered values are CPython 3.11 through 3.14, matching the
[Python support policy](python-support.md) and existing Copier choices. The
contiguous `tested_versions` range is derived by the Python model and is not a
wire field. Support-window transitions change the engine's offered values
under that policy without duplicating a caller-supplied test matrix.

### Component selection

`ComponentSelection` requires exactly one `archetype` and accepts zero or more
`capabilities` and zero or more `platforms`. Component, profile, and policy
identifiers use lower-case kebab-case and carry no requested version: normal
discovery is constrained to the installed engine release, whose
[component manifests](component-manifests.md) own globally unique IDs,
component versions, compatibility, dependencies, and conflicts.

Capability and platform arrays are unique sets and serialise in lexical order.
That canonical wire ordering is not composition ordering. Deterministic
application order is defined by
[composition-order.md](composition-order.md), delivered through FT-06.03, and
output targets, dispositions, and collision behaviour are now defined by
[file-conflicts.md](file-conflicts.md), delivered through FT-06.04.

Multiple platforms are valid. A repository-host adapter and a runtime-target
adapter can coexist when their extension-point declarations do not collide,
per [file-conflicts.md](file-conflicts.md).

### Effective selections and provenance

ProjectSpec carries the effective request after profile defaults,
organisation-policy defaults, explicit choices, and required or forbidden
constraints have been resolved under the
[canonical authority order](terminology.md#composition-and-authority) and the
strict [organisation policy protocol](organisation-policy.md).

`SelectionProvenance.profile` and `SelectionProvenance.policies` record only
the optional identifiers that influenced that effective request. They do not
reapply defaults, carry policy documents, or grant rendering authority.
Organisation-policy protocol `1` now defines the external document, conflict,
and failure semantics; executable parsing and resolution remain unscheduled
client-owned work in roadmap v1 and do not alter this ProjectSpec wire shape.

### Component options

`component_options` is an object keyed by a selected archetype, capability, or
platform identifier. Each owner receives an object of lower-snake-case keys
and JSON-compatible values. An option namespace for an unselected component is
invalid.

Protocol v1 establishes only this structural boundary. The canonical
project/package/Python variables and the recognised, required, and
unknown-option behaviour supplied by component manifests are now defined by
[template-variables.md](template-variables.md), delivered through
[FT-06.05](https://github.com/Sandsy09/forge-template/issues/36). Foundation
is implicit and is not an option owner in ProjectSpec.

Component options must not contain secrets, credentials, arbitrary file
content, executable code, destination paths, or organisation-policy
documents. ProjectSpec is a generation request, not a general extension or
code-execution channel.

## Library-shaped example

The direct-Copier Library scaffold remains monolithic, while the engine
catalogue now composes the same archetype from Foundation and Library content.
Both use a request that keeps GitHub metadata outside the core project model:

```json
{
  "protocol_version": 1,
  "project": {
    "name": "Credit Risk Utils",
    "package_name": "credit_risk_utils",
    "repository_name": "credit-risk-utils",
    "description": "Shared credit-risk calculations.",
    "licence": "mit",
    "authors": [
      {
        "name": "Test User",
        "email": "test@example.invalid"
      }
    ]
  },
  "python": {
    "minimum": "3.11",
    "development": "3.13"
  },
  "components": {
    "archetype": "library",
    "capabilities": ["changelog", "documentation"],
    "platforms": ["github"]
  },
  "provenance": {
    "profile": "maintainer",
    "policies": ["security-baseline"]
  },
  "component_options": {
    "library": {
      "packaging_mode": "uv-build-static",
      "initial_version": "0.1.0"
    },
    "documentation": {
      "site_name": "Credit Risk Utils"
    },
    "github": {
      "organisation": "example-org"
    }
  }
}
```

The `library` identifier and its two options are accepted by the canonical
[Library archetype contract](library-archetype.md) and implemented in the
production catalogue by FT-08.02.

## CLI Application multi-platform example

The selected second reference archetype has no component options. Its command
name derives from `project.repository_name` under the canonical
[CLI Application contract](cli-application-archetype.md):

```json
{
  "protocol_version": 1,
  "project": {
    "name": "Example CLI",
    "package_name": "example_cli",
    "repository_name": "example-cli",
    "description": "An example command-line application.",
    "licence": "proprietary",
    "authors": []
  },
  "python": {
    "minimum": "3.12",
    "development": "3.14"
  },
  "components": {
    "archetype": "cli",
    "capabilities": ["capability-a"],
    "platforms": ["repository-host", "runtime-target"]
  },
  "provenance": {
    "profile": null,
    "policies": []
  },
  "component_options": {}
}
```

## Compatibility and deferred work

Protocol 1 is separate from the `forge-template` package and component
manifest versions. A breaking
wire-format, core validation, or semantic change requires a new protocol;
compatible additions may remain on protocol 1. Component-catalogue versions
and option validity belong to the installed engine release and manifests.

The surrounding implementation is defined by the
[manifest field contract](component-manifests.md),
[composition order](composition-order.md),
[file conflict and override rules](file-conflicts.md),
[template variable contract](template-variables.md),
[composition fixtures](composition-fixtures.md), and
[stable template-engine API](template-engine-api.md). This protocol still does
not define:

- executable organisation-policy parsing and resolution (unscheduled in
  roadmap v1); or
- CLI prompting, ProjectSpec construction, diagnostics, or target filesystem
  orchestration (`create-forge`).

The current CLI continues to pass its plain answer mapping directly to Copier.
No generated project depends on the ProjectSpec model during normal
development or runtime.
