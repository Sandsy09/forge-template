# Component Manifest Protocol v1

Component manifests are the machine-readable metadata for the archetypes,
capabilities, and platforms bundled with a future `forge-template` engine
release. Protocol v1 is implemented by the strict models and provisional
validators in
[`forge_template.component_manifest`](../src/forge_template/component_manifest.py).

This contract defines metadata and validation before production components or
discovery exist. The current Library scaffold remains the monolithic `template/`
tree and has no production manifest. Its migration is owned by
[FT-08.02](https://github.com/Sandsy09/forge-template/issues/41).

## Authoring and schema source

Each component uses a UTF-8 TOML file named `component.toml`. TOML is the
canonical human-authored representation; the Pydantic models are the single
structural schema source. Consumers may inspect
`ComponentManifest.model_json_schema()` when JSON Schema is useful, but Forge
does not commit a second generated schema that could drift.

Unknown fields, omitted or unsupported manifest versions, implicit primitive
type coercion, invalid identifiers, and invalid PEP 440 values fail validation.
The low-level loader currently exposes standard TOML, Pydantic, filesystem, or
value failures. The stable structured engine-error surface remains
[FT-06.07](https://github.com/Sandsy09/forge-template/issues/38) work.

```toml
manifest_version = 1
id = "documentation"
name = "Documentation"
description = "A project documentation site."
kind = "capability"
version = "1.1.0"
content_root = "content"
options_schema = "options.schema.json"
requires = [{ id = "library", version = ">=1,<2" }]
conflicts = []

[compatibility]
projectspec_protocols = [1]
requires_python = ">=3.11"
```

The example is conceptual metadata, not a production manifest or a claim that
the Library scaffold is already composed.

## Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `manifest_version` | integer literal `1` | Component manifest protocol. |
| `id` | lower-case kebab-case string | Canonical globally unique component identifier. |
| `name` | non-empty string | Human-facing display name. |
| `description` | non-empty string | Human-facing discovery summary. |
| `kind` | `archetype`, `capability`, or `platform` | Component kind defined by the canonical terminology. |
| `version` | canonical PEP 440 string | Independent component content/contract version. |
| `content_root` | relative path | Required owned contribution directory. |
| `options_schema` | relative path or omitted | Reserved owner-local option-schema resource. |
| `compatibility` | table | ProjectSpec protocol and generated-Python compatibility. |
| `requires` | array of component references | Hard selected-component dependencies. |
| `conflicts` | array of component references | Incompatible selected components. |
| `extension_points` | array of extension points, optional | Named points this component publishes for another to extend. |
| `contributions` | array of contributions, optional | Additive contributions into another component's published extension point. |

### Identity and kinds

Component IDs share the same lower-case kebab-case rule as ProjectSpec and
must be globally unique across all kinds. Global uniqueness is required because
ProjectSpec component options are keyed by component ID without a separate kind
segment.

`name` and `description` are presentation metadata. Clients may display them,
but they use `id` for ProjectSpec, dependency, conflict, and persistence
semantics.

Only archetypes, capabilities, and platforms are components. Foundation is the
implicit mandatory baseline. Profiles and organisation policies select,
default, require, or forbid components; they do not gain component manifests or
rendering authority.

### Manifest and component versions

`manifest_version` versions this TOML contract. Component `version` separately
uses canonical PEP 440 and versions that component's content and compatibility
surface. Neither value is the `forge-template` package version or the
ProjectSpec protocol version.

All normal components ship inside one reviewed, version-constrained engine
release, so a manifest does not repeat an engine package range. The installed
release determines the one catalogue and concrete component versions available
for discovery. Runtime remote registries and arbitrary installed plugins remain
outside the accepted trust model.

### Compatibility

`compatibility.projectspec_protocols` is a non-empty, unique set of ProjectSpec
protocol integers. This engine line understands only protocol `1`.

`compatibility.requires_python` is a non-empty PEP 440 specifier for the
generated project's interpreters. Every minor in
`PythonSelection.tested_versions`, from the compatibility floor through the
development version, must satisfy it. Checking only one endpoint would permit a
component to weaken the generated project's claimed tested range.

Compatibility is evaluated before composition or rendering. A client may
present compatible choices, but `forge-template` remains the validation owner.

### Owned content and option schema

`content_root` names a real, non-empty directory relative to `component.toml`.
Every file below it is reviewed content owned by that component. Resource paths
use forward slashes, cannot be absolute or traverse upwards, and must remain
inside the component directory after symlink resolution.

This contract inventories the source tree only. Whether an entry renders or
copies literally, its output target, and whether a collision creates,
extends, merges, or overrides are now defined by
[file-conflicts.md](file-conflicts.md), delivered through
[FT-06.04](https://github.com/Sandsy09/forge-template/issues/35), while
deterministic ordering — including this content's own applied order — is
defined by [composition-order.md](composition-order.md), delivered through
[FT-06.03](https://github.com/Sandsy09/forge-template/issues/34). A component
may publish a named extension point in this content, or contribute into
another component's published point, through the optional
`extension_points`/`contributions` fields below.

`options_schema` may name one existing file under the same component directory.
The canonical project/package/Python variables, the component option-schema
format, and required/unknown-option rejection are now defined by
[template-variables.md](template-variables.md), delivered through
[FT-06.05](https://github.com/Sandsy09/forge-template/issues/36).

### Extension points and contributions

`extension_points` publishes named points a component's own owned content
exposes for another to extend. Each entry names an `id` and a `content`
path — component-relative like `options_schema`, and required to fall
inside this component's own `content_root`.

`contributions` targets another component's published point. Each entry
names the target `component`, its `extension_point` id, and this
component's own `content` path — required to fall **outside** this
component's `content_root`, since a contribution is not itself an owned
output file. A component may not contribute to its own extension point.

Both are optional and additive: omitting them leaves a manifest identical to
protocol 1 as accepted by [ADR 0024](adr/0024-component-manifest-protocol-v1.md),
so `manifest_version` stays `1`. What a contribution does to its target's
output — creation, extension, and the full disposition and collision rules —
is defined by [file-conflicts.md](file-conflicts.md), delivered through
[FT-06.04](https://github.com/Sandsy09/forge-template/issues/35).

## Dependencies and conflicts

Each entry in `requires` or `conflicts` contains a component `id` and an
optional PEP 440 `version` specifier. Omitting the specifier means any packaged
version. Reference arrays are unordered sets and are canonicalised lexically
for inspection; their source order is never composition order.

A valid bundled manifest set requires:

- globally unique component IDs;
- every referenced ID to exist in the same packaged set;
- every referenced component version to satisfy its specifier;
- no duplicate or self-reference; and
- no component to name the same target in both sets.

`requires` is a hard effective-selection constraint. Every dependency must
appear explicitly in ProjectSpec under its declared kind. The engine rejects a
missing dependency rather than silently modifying ProjectSpec; clients may
guide users or profiles may supply defaults, but the final request remains
observable and complete.

`conflicts` is symmetric at selection time: if both the declaring component and
the referenced component are selected, the request is invalid. A declaration
does not need a duplicated reverse entry.

Dependency cycles are rejected catalogue-wide by `validate_manifest_set`,
independent of component kind, before any content operation occurs. See
[composition-order.md](composition-order.md#cycles), delivered through
[FT-06.03](https://github.com/Sandsy09/forge-template/issues/34).
`validate_manifest_set` also rejects, catalogue-wide, any contribution that
names a component or extension point that does not exist — independent of
any ProjectSpec selection. See
[file-conflicts.md](file-conflicts.md#resolving-contributions), delivered
through [FT-06.04](https://github.com/Sandsy09/forge-template/issues/35).

## ProjectSpec selection validation

The provisional low-level validation checks that an effective ProjectSpec:

1. resolves every selected ID from the installed manifest set;
2. selects an archetype as an archetype, capabilities as capabilities, and
   platforms as platforms;
3. never selects one global ID under multiple kinds;
4. satisfies each selected component's ProjectSpec and complete Python-range
   compatibility;
5. includes every hard dependency explicitly; and
6. contains no declared conflict.

The validator returns selected manifests in lexical order only to make tests
and catalogue inspection deterministic. That order grants no rendering or
overwrite authority.

## Deferred work

Protocol v1 does not define:

- production manifests, component discovery, or package-data layout;
- the second roadmap archetype;
- optional or recommended dependencies;
- file operations, rendering, or the in-file extension-point marker syntax
  (FT-06.07); output targets, dispositions, and collision safety are now
  defined by [file-conflicts.md](file-conflicts.md) (FT-06.04);
- the option-schema and template-variable vocabulary are now defined by
  [template-variables.md](template-variables.md) (FT-06.05);
- full composed-output fixtures (FT-06.06);
- stable engine discovery, rendering functions, or structured errors
  (FT-06.07); or
- CLI prompts, automatic choice guidance, or filesystem orchestration
  (`create-forge`).

Until those coordinated contracts and the atomic cutover are complete, the
released CLI continues to use its bundled registry and direct Copier path.
Generated projects acquire no dependency on these manifest models.
