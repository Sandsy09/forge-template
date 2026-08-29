# Template variable contract

This contract defines what a template author types, what a component may
declare as its own options, and what fails before any file operation.
Protocol v1 is implemented by
[`forge_template.template_variables`](../src/forge_template/template_variables.py),
operating over a validated [ProjectSpec](project-spec.md) and a mapping of
component ID to declared option schema; this document is its canonical
contract, adopted by [ADR
0027](adr/0027-template-variable-contract.md).

## Scope

This contract defines the rendered variable namespace and the component
option vocabulary. The
[stable template-engine API](template-engine-api.md) consumes the namespace,
defines the in-file extension-marker syntax, renders with strict undefined
handling, and exposes structured failures. This contract
does not define output targets, dispositions, or collision safety — that is
[file-conflicts.md](file-conflicts.md). It does not define
organisation-policy defaults or constraints — that is Stage 09.

## The variable namespace

Every template author reads from exactly four reserved roots:

```jinja
{{ project.name }}              {{ python.minimum }}
{{ project.package_name }}      {{ python.development }}
{{ project.repository_name }}   {{ python.tested_versions }}
{{ project.licence }}           {{ python.requires_python }}

{{ components.archetype }}      {{ options.library.packaging_mode }}
{{ components.capabilities }}   {{ options.secret_scanning.tool }}
```

No other top-level name is part of this contract. A component that needs a
value it owns declares it as an option under its own `options` namespace
rather than inventing a fifth root.

## Project variables

`project` is [`ProjectSpec.project`](project-spec.md#project-metadata)
re-exposed unchanged — `ProjectMetadata` is not redeclared for rendering, so
the two can never drift apart. Values ProjectSpec deliberately excludes from
core project metadata — a GitHub organisation, a repository URL, a
CODEOWNERS identity — remain the owning platform's own options; no
production `github` manifest exists yet to name concretely.

## Python variables

`python.minimum` and `python.development` are
[`PythonSelection`](project-spec.md#python-selection)'s two wire values,
unchanged. `python.tested_versions` and `python.requires_python` are derived
once by this contract rather than left for every component to re-derive:

```text
python.tested_versions   PythonSelection.tested_versions
                          (the contiguous minimum..development range)

python.requires_python   ">=" + python.minimum
```

Every selected component's `compatibility.requires_python` must already be
satisfied across the full tested range
([component-manifests.md](component-manifests.md#compatibility)), so
`python.requires_python` is safe for any component to emit as its own
generated project's floor without re-checking anything.

## Component selection

`components` is [`ComponentSelection`](project-spec.md#component-selection)
re-exposed unchanged and read-only, so a template can reflect the effective
selection — for example, gating a section on whether a particular capability
is present. This is not a substitute for an extension point: conditioning a
component's own content on another component's selection is fine, but
*affecting* another component's content is governed entirely by
[file-conflicts.md](file-conflicts.md).

## Component option namespaces

Each selected component's declared options live under
`options.<namespace>`, where `<namespace>` is that component's identifier
with every hyphen replaced by an underscore:

```text
github             -> options.github
secret-scanning    -> options.secret_scanning
```

Component identifiers are kebab-case
(`^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`, [component-manifests.md](component-manifests.md#identity-and-kinds))
and can therefore never themselves contain an underscore. That makes the
hyphen-to-underscore mapping injective: two distinct identifiers can never
collide on one options key. This is also what keeps dotted Jinja access
correct for every legal identifier — `{{ options.secret-scanning.tool }}`
would parse as subtraction, not lookup, so the raw hyphenated identifier
could never have worked as a namespace on its own.

Every selected component receives an `options` entry, empty when it declares
no options, so a template never has to test whether its own namespace exists
before reading from it.

## Declaring options

A component declares its accepted options by naming a strict JSON document
in `options_schema` ([component-manifests.md](component-manifests.md#owned-content-and-option-schema)):

```json
{
  "schema_version": 1,
  "options": [
    {
      "name": "build_backend",
      "type": "string",
      "required": true,
      "choices": ["uv_build", "hatchling"]
    },
    {
      "name": "initial_version",
      "type": "string",
      "default": "0.1.0"
    }
  ]
}
```

`schema_version` is currently only `1`. Each option names a lower-snake-case
`name` (the same rule ProjectSpec's own component options already use), a
`type` from a closed set, and:

| Field | Meaning |
| --- | --- |
| `type` | One of `string`, `integer`, `boolean`, `string_list`. |
| `required` | Whether ProjectSpec must supply this option explicitly. |
| `default` | The value used when not supplied. Mutually exclusive with `required`. |
| `choices` | A non-empty enumerated set of admissible values. Only meaningful for `string` and `integer`. |
| `description` | Human-facing documentation only. |

The accepted [Library archetype contract](library-archetype.md) requires
option-schema protocol `2` to add `format` for string options, with `pep440`
as its initial supported value. FT-08.02 must validate and canonicalise the
Library `initial_version` before rendering and expose the format in discovery
descriptors. Protocol v1 and the table above remain the current implemented
behaviour; FT-08.01 adds no schema or resolver support.

A component with no `options_schema` at all accepts no options: there is no
unvalidated passthrough class of option. A schema with no
`options_schema`-supplied value and no `default` for a non-required option
simply resolves to that namespace omitting the key.

## Resolution and rejection

`resolve_template_variables` takes an already-validated `ProjectSpec`
selection (per
[`validate_manifest_selection`](component-manifests.md#projectspec-selection-validation))
and a mapping of component ID to `OptionSchema`, and fails before any file
operation when:

- `component_options` supplies an option a component does not declare (this
  covers the "no schema" case too — every option is unknown against an empty
  schema);
- a `required` option is missing;
- a supplied value's type does not match its declaration; or
- a supplied value is outside its declared `choices`.

The low-level helper raises a plain `ValueError` naming the component, option,
and violated rule — matching
[`composition.py`](../src/forge_template/composition.py) and
[`file_conflicts.py`](../src/forge_template/file_conflicts.py)'s internal error
convention. The [stable API](template-engine-api.md#structured-failures)
translates expected option failures into a machine-readable public error.

An *undefined* variable reference — one naming a namespace or option
this contract does not resolve at all, as opposed to a value that resolved
but failed validation — fails and names the reference rather than silently
rendering as an empty string. The public renderer enforces this with Jinja
`StrictUndefined`.

## Deferred work

Composed-output evidence is defined by
[composition-fixtures.md](composition-fixtures.md), and discovery, rendering,
extension-marker syntax, and structured errors by the
[stable template-engine API](template-engine-api.md). This variable contract
does not define:

- organisation-policy resolution (Stage 09).

The current CLI continues to pass its plain answer mapping directly to Copier,
using its own flat `copier.yml` variable names unchanged. No generated project depends on
`forge_template.template_variables` during normal development or runtime.
