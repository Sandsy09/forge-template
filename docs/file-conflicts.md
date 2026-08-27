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

This contract defines output targets, dispositions, and collision safety
only. It does not perform file operations, render or splice content, define
the in-file syntax an extension point uses, or expose a stable engine error
surface — that is
[FT-06.07](https://github.com/Sandsy09/forge-template/issues/38). The
option-schema and template-variable vocabulary is now defined by
[template-variables.md](template-variables.md), delivered through
[FT-06.05](https://github.com/Sandsy09/forge-template/issues/36). It does not
define organisation-policy overrides — that is Stage 09.

## Output targets

Each file under a component's `content_root` maps to one project-relative
output target: the same path, with one trailing `.jinja` suffix stripped
when present. A path ending `.jinja` renders before it lands at the stripped
path; every other path copies literally at its own path.

```text
content/pyproject.toml.jinja   ->   pyproject.toml
content/py.typed               ->   py.typed
```

Two of one component's own owned files mapping to the same target — for
example `foo.txt` and `foo.txt.jinja` both present under one `content_root`
— is an authoring error inside that component, independent of any other
component's selection.

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
naming the target `component`, its `extension_point` id, and its own
`content` path. A contribution's `content` must fall **outside** its own
`content_root`: a contribution is not itself an owned output file, so it
must not also be emitted at its own target under the rule above.

```toml
[[contributions]]
component = "github"
extension_point = "ci-steps"
content = "extensions/ci-step.yml.jinja"
```

A component may not contribute to its own extension point, extension point
IDs are unique within one component, and one component may not declare two
contributions to the same `(component, extension_point)` pair. All of this
is enforced by `ComponentManifest`'s model validators, without touching the
filesystem.

`manifest_version` stays `1`. Both fields are optional and additive: every
existing manifest, with neither field present, remains valid. [ADR
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

A contribution whose named `component` is not part of the current selection
is dropped, not an error: an optional integration (a coverage capability
extending a CI workflow) stays valid whether or not the platform it would
extend is also selected. This is safe only because catalogue-wide
validation — `component_manifest.validate_manifest_set`, alongside its
existing cycle rejection — already proves every contribution names a real
component and a real, published extension point on it, independent of any
selection. A missing owner at plan-resolution time therefore only ever
means "not selected", never a typo that silently disappeared.

## Unsupported collisions

Two selected components both creating the same target is an unsupported
collision. `resolve_output_plan` raises, naming both components and the
shared target — the executable form of [terminology.md's normative
rules](terminology.md#composition-and-authority): implicit last-write-wins
replacement is forbidden, and unsupported component collisions fail rather
than silently overwriting content. Being later in composition order is
never implicit permission to replace an earlier component's target.

## Foundation and policy overrides

Foundation is the implicit baseline, not a component, so it cannot yet
collide with a component's target under this contract. Two things are
stated now regardless: Foundation's targets are never overridable by a
component, and once Foundation becomes a real content source it publishes
extension points like any other owner rather than gaining an implicit right
to be replaced. This is required by [foundation-scope.md's neutral handoff
material](foundation-scope.md#neutral-handoff-material): "Later layers may
add owned sections through explicit extension points. They may not silently
replace the neutral handoff material."

A future organisation policy may be granted `override` authority over a
specific, documented extension point. That grant is Stage 09's decision to
make; this contract only reserves the vocabulary and states that no such
authority exists implicitly today.

## Deferred work

This contract does not define:

- structured option validation errors (FT-06.07); the recognised
  template-variable catalogue is now defined by
  [template-variables.md](template-variables.md)
  ([FT-06.05](https://github.com/Sandsy09/forge-template/issues/36));
- full composed-output fixtures — now defined by
  [composition-fixtures.md](composition-fixtures.md)
  ([FT-06.06](https://github.com/Sandsy09/forge-template/issues/37));
- component discovery, a stable rendering API, the in-file marker syntax an
  extension point splices into, or structured engine errors
  ([FT-06.07](https://github.com/Sandsy09/forge-template/issues/38)); or
- organisation-policy resolution, including any real `override` grant
  (Stage 09).

Until those coordinated contracts are complete, v0.1.x continues to pass its
plain answer mapping directly to Copier. No generated project depends on
`forge_template.file_conflicts` during normal development or runtime.
