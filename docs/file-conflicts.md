# File conflict and override rules

This contract defines what project-relative output target a component's
owned content produces, what a component may do to a target another
component owns, and what happens when two components' output collides.
Protocol v1 is implemented by
[`forge_template.file_conflicts`](../src/forge_template/file_conflicts.py),
operating over a validated
[composition plan](composition-order.md); this document is its canonical
contract, adopted by [ADR
0026](adr/0026-file-conflict-and-override-rules.md).

## Scope

This contract defines output targets, dispositions, and collision safety.
The [stable template-engine API](template-engine-api.md) uses it to plan and
render in memory, defines extension-marker syntax, and translates expected
collisions into structured public failures. Destination file operations remain
outside the engine. The
option-schema and template-variable vocabulary is now defined by
[template-variables.md](template-variables.md), delivered through
[FT-06.05](https://github.com/Sandsy09/forge-template/issues/36). It does not
define organisation-policy overrides — that is Stage 09.

## Output targets

Each file under an owner's `content_root` — a component's own, or the
implicit Foundation content source's — maps to one project-relative output
target: the path, first rendered through the same `StrictUndefined`
template-variable context file content renders with, then with one trailing
`.jinja` suffix stripped when present. A path ending `.jinja` renders before
it lands at the stripped path; every other path copies literally at its own
(still-rendered) path.

```text
content/pyproject.toml.jinja                    ->   pyproject.toml
content/py.typed                                ->   py.typed
content/src/{{ project.package_name }}/py.typed ->   src/credit_risk_utils/py.typed
```

`forge_template.file_conflicts.render_output_path` performs the rendering
step and validates the result as a normalised relative POSIX path — it must
not become absolute, escape via `..`, or produce an empty segment, so a path
variable can never redirect output outside the project tree. A path
referencing an undefined variable fails before any file operation, exactly
as undefined content does. This is what makes the accepted [Library
archetype contract](library-archetype.md)'s `src/<package_name>/` outcome
representable at all — see [ADR
0032](adr/0032-render-component-content-paths.md).

Two of one owner's own owned files mapping to the same *rendered* target —
for example `foo.txt` and `foo.txt.jinja` both present under one
`content_root`, or two templated paths that happen to render identically —
is an authoring error inside that owner, independent of any other owner's
selection.

## Dispositions

| Disposition | Meaning | Protocol v1 |
| --- | --- | --- |
| `create` | Sole contributor owns the target outright. | **Granted** — the default for every owned file. |
| `extend` | Additive contribution into an extension point the target's owner published. The owner keeps ownership of the target. | **Granted**, only through a declared extension point. |
| `merge` | Format-aware structured combination of two components' contributions to one target (for example, TOML or YAML key union). | Classified, not granted. |
| `override` | Full replacement of another component's target. | Classified, reserved to a documented extension point and future organisation policy. |

Only `create` and `extend` are expressible in protocol v1. `merge` and
`override` are named and defined so this contract can state precisely what
they would mean, but no manifest field grants either: a collision that would
need one fails with an unsupported-collision error rather than silently
choosing a resolution. This reads the issue's "reserve policy overrides for
documented extension points" literally — reservation, not availability.

## Extension points

A component publishes an extension point by declaring `[[extension_points]]`
in `component.toml`, naming an `id` and the `content` path — component-root
relative, matching `options_schema`'s convention — of the owned file the
point lives in. That path must fall inside the component's own
`content_root`: an extension point extends content the component itself
owns and emits, never an arbitrary resource.

```toml
[[extension_points]]
id = "ci-steps"
content = "content/ci.yml.jinja"
```

Another component contributes to it by declaring `[[contributions]]`,
naming its target, its `extension_point` id, and its own `content` path. A
contribution's `content` must fall **outside** its own `content_root`: a
contribution is not itself an owned output file, so it must not also be
emitted at its own target under the rule above.

Manifest protocol `1` names the target component directly:

```toml
[[contributions]]
component = "github"
extension_point = "ci-steps"
content = "extensions/ci-step.yml.jinja"
```

Manifest protocol `2` (FT-08.02) replaces that flat key with a discriminated
`target`, naming either a component or the implicit Foundation content
source — see
[component-manifests.md](component-manifests.md#accepted-manifest-protocol-v2-target-owner):

```toml
[[contributions]]
extension_point = "pyproject-build-system"
content = "extensions/pyproject-build-system.toml.jinja"
target.kind = "foundation"
```

A component may not contribute to its own extension point, extension point
IDs are unique within one owner, and one component may not declare two
contributions to the same `(target, extension_point)` pair. All of this is
enforced by `ComponentManifest`'s model validators, without touching the
filesystem. A manifest may use only its own protocol's shape: protocol `1`
rejects a `target` table, protocol `2` rejects the flat `component` key.

`manifest_version` stays `1` or becomes `2`. Every existing protocol-`1`
manifest, with neither field present, remains valid — protocol `1` parsing
is retained unchanged, not replaced. [ADR
0024](adr/0024-component-manifest-protocol-v1.md) is not superseded.

## Resolving contributions

A component's owned content and its contributions are validated
independently of any particular selection or tier. **The output plan is
resolved whole, before any file operation**: every selected component's
owned content becomes a target's `create`-disposition base, and every
selected component's contributions then attach as ordered `extend` entries
onto the target their point lives in.

This matters because the canonical extension case runs *against* tier
order. A `coverage` capability contributing a CI step to the `github`
platform's workflow is a capability extending a platform, but [composition
order](composition-order.md#tier-order) applies every capability before any
platform. Resolving the whole plan first — rather than applying components
one at a time to a filesystem — means a target's base is always supplied by
its owner regardless of which tier the contributing component sits in;
nothing here ever needs the base to already exist on disk before a later
tier is reached.

Composition order still matters for *what it does* decide: when more than
one component contributes to the same extension point, the contributions
attach in composition order — the same deterministic order
[composition-order.md](composition-order.md) already defines. Tier order
never decides whether a target's base exists, only the order among multiple
contributors once it does.

A contribution whose named target component is not part of the current
selection is dropped, not an error: an optional integration (a coverage
capability extending a CI workflow) stays valid whether or not the platform
it would extend is also selected. This is safe only because catalogue-wide
validation — `component_manifest.validate_manifest_set`, alongside its
existing cycle rejection — already proves every contribution names a real
component and a real, published extension point on it, independent of any
selection. A missing owner at plan-resolution time therefore only ever
means "not selected", never a typo that silently disappeared. A
Foundation-targeted contribution has no such "not selected" case — Foundation
is mandatory whenever it is supplied to `resolve_output_plan` at all — so a
missing Foundation source is a hard error instead.

## Unsupported collisions

Two selected owners both creating the same target is an unsupported
collision — whether both are components, or one is the implicit Foundation
content source. `resolve_output_plan` raises, naming both owners and the
shared target — the executable form of [terminology.md's normative
rules](terminology.md#composition-and-authority): implicit last-write-wins
replacement is forbidden, and unsupported collisions fail rather than
silently overwriting content. Being later in composition order is never
implicit permission to replace an earlier owner's target.

## Foundation and policy overrides

Foundation is the implicit baseline, not a component. FT-08.02 makes it a
real content source: `resolve_output_plan` takes it as its own argument
(`forge_template.foundation_source.FoundationPlacement`), never as a member
of the composition placements it also takes, so it structurally cannot
appear in `component_order`. Foundation's owned content becomes every
target's `create`-disposition base before any selected component's does;
Foundation's targets are never overridable by a component, and a component
creating a target Foundation already owns is an unsupported collision like
any other. Foundation publishes extension points exactly like a component
does — a contribution names it through a discriminated `target.kind =
"foundation"` (manifest protocol `2`; see
[component-manifests.md](component-manifests.md#accepted-manifest-protocol-v2-target-owner))
rather than gaining an implicit right to be replaced. This satisfies
[foundation-scope.md's neutral handoff
material](foundation-scope.md#neutral-handoff-material): "Later layers may
add owned sections through explicit extension points. They may not silently
replace the neutral handoff material."

`PlannedFile.owner` and `OutputContribution.owner` are discriminated on
`kind`: `FoundationOwner(kind="foundation")` or `ComponentOwner(kind=
"component", id=...)`. This replaced `owner_component_id` in the package's
`0.3.0` line — a plain component-id string could not truthfully represent a
Foundation-owned file.

[FT-09.02](https://github.com/Sandsy09/forge-template/issues/45) resolved the
reserved `override` grant as a denial: organisation policy never gains
`override` authority over any extension point, in protocol `1`. See
[extension-points.md](extension-points.md) and [ADR
0039](adr/0039-deny-policy-file-overrides.md) for the published extension-point
inventory and the full rationale. This contract still only reserves the
vocabulary; no authority to override exists.

## Deferred work

Option validation is defined by
[template-variables.md](template-variables.md), composed evidence by
[composition-fixtures.md](composition-fixtures.md), and public planning,
rendering, marker syntax, and structured failures by the
[stable template-engine API](template-engine-api.md). This conflict contract
does not define:

- destination writes or client filesystem conflict handling; or
- organisation-policy selection resolution (defined by
  [organisation-policy.md](organisation-policy.md), FT-09.01) or executable
  policy parsing/resolution (still deferred).

The current CLI continues to pass its plain answer mapping directly to Copier.
No generated project depends on `forge_template.file_conflicts` during normal
development or runtime.
