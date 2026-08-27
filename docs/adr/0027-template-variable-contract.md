# 27. Design the template variable contract

## Status

Accepted

## Context

Six accepted contracts already name this issue as the owner of a vocabulary
none of them defines. `docs/component-manifests.md` states that
`options_schema` "may name one existing file… Protocol v1 reserves that
owner-local resource without defining or parsing its vocabulary. Canonical
project/package/Python variables, component option schemas, required and
unknown options, and structured validation failures remain FT-06.05 work."
`docs/project-spec.md` restates it: "FT-06.05 defines the canonical
project/package/Python variables and the recognised, required, and
unknown-option behaviour supplied by component manifests."
`docs/composition-order.md` and `docs/file-conflicts.md` each disclaim the
option-schema and template-variable vocabulary as FT-06.05's, and
`docs/editor-integration.md` names it as one of two remaining open contracts
before a concrete editor adapter can be proposed. [ADR
0024](0024-component-manifest-protocol-v1.md) deferred "option-schema meaning
to FT-06.05" by name.

The concrete shape of the gap was already checked in: the `library` fixture's
`options.schema.json` was a literal `{}` — a file the loader checked for
existence and never parsed, because nothing owned its vocabulary.

## Decision

Define, in `docs/template-variables.md` and `forge_template.template_variables`,
what a template author types and what a component may declare as its own
options:

- **Four reserved namespace roots: `project`, `python`, `components`,
  `options`.** `project` and `components` reuse `ProjectSpec`'s own
  `ProjectMetadata` and `ComponentSelection` models directly rather than
  redeclaring parallel ones, so the mapping holds by construction. `python`
  adds two engine-derived, read-only values — `tested_versions` and
  `requires_python` — on top of the two wire ones, so every component reads
  one already-computed matrix and specifier instead of re-deriving its own.
  `options` is reserved for component-specific values, so a component option
  can never collide with a core variable.
- **`options_schema` gains a Forge-owned, strict format**, validated by
  Pydantic rather than JSON Schema: no new runtime dependency, and a bounded
  surface rather than JSON Schema's unconstrained one (refs, conditionals,
  remote schemas). A schema declares a `schema_version` (currently only `1`)
  and zero or more `options`, each with a name, a type from a closed set
  (`string`, `integer`, `boolean`, `string_list`), and optional `required`,
  `default`, `choices`, and `description`.
- **No `options_schema` means no options.** A component that declares
  nothing accepts nothing; any option namespaced to it is unknown and
  rejected. There is no unvalidated passthrough class of option.
- **A component's options key is its identifier with hyphens replaced by
  underscores.** Component identifiers are kebab-case
  (`^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`) and can never contain an underscore, so
  this mapping is injective: two distinct identifiers can never collide on
  one options key. This is what keeps `{{ options.secret_scanning.tool }}` a
  plain Jinja lookup — the raw hyphenated identifier would parse as
  subtraction instead.
- **Declaration rules are checked without touching a ProjectSpec.**
  `required` and `default` are mutually exclusive; `choices`, when declared,
  must be non-empty, restricted to `string`/`integer` types, and every
  element (and `default`, if present) must match the declared type.
- **Resolution fails before any file operation** when a supplied option is
  not declared by its component, when a required option is missing, when a
  value's type or `choices` membership fails its declaration, or when any
  option is supplied to a component with no schema at all. Every failure
  names the component, the option, and the rule violated, raised as a plain
  `ValueError` — matching `composition.py` and `file_conflicts.py`, and
  deferring a structured engine-error type to FT-06.07's error surface.
- **The contract states, for FT-06.07 to implement, that an undefined
  template-variable reference must fail rather than silently render as an
  empty string.** Rendering itself remains out of scope here.

`forge_template.template_variables` adds `resolve_template_variables`,
consuming an already-validated `ProjectSpec` and a mapping of component ID to
`OptionSchema`, and returns the complete, strict, frozen namespace a renderer
would receive — mirroring how `composition_plan` and `resolve_output_plan`
each return a resolved plan rather than performing an action.

## Consequences

- `options_schema` acquires the meaning ADR 0024 deliberately left open,
  without superseding it or changing `manifest_version`; the field itself is
  unchanged.
- A component that wants configurable options must now declare them
  explicitly through `options_schema` — the `library` and `github` fixtures
  do so; a schema-less component such as `coverage` still validates cleanly
  and simply accepts none.
- `create-forge#46`'s cross-repository dependency on "FT-06.05: define
  structured validation errors" is satisfied in the sense that this contract
  states required failure content; the issue remains blocked on FT-06.07 for
  its actual structured exception type, which was true before this ADR too.
- FT-06.06 becomes unblocked: its three prerequisites (FT-06.03, FT-06.04,
  FT-06.05) are now all complete.
- The current v0.1.x Copier path, template tree, generated output, and CLI
  behaviour do not change. No generated project gains a dependency on
  `forge_template.template_variables`.
