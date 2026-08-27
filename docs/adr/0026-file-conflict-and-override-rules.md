# 26. Define file conflict and override rules

## Status

Accepted

## Context

[ADR 0024](0024-component-manifest-protocol-v1.md) defined component
metadata while explicitly deferring what happens to the content it
describes. `docs/component-manifests.md` states plainly that the manifest
contract "does not decide whether an entry renders or copies literally, its
output target, or whether a collision creates, extends, merges, or
overrides. Those operations and their safety rules belong to FT-06.04."
[ADR 0025](0025-deterministic-composition-order.md) went further:
"Order confers no overwrite authority… that boundary stays with FT-06.04,
which owns file operations and collisions", and `docs/composition-order.md`
states "What happens when two components name the same output target is
entirely FT-06.04's decision to make." `docs/project-spec.md` names this
issue the owner of "collision and override behaviour" a third time.

`docs/terminology.md`'s composition-and-authority rules were already
normative — rule 2, "implicit last-write-wins replacement is forbidden",
and rule 5, "unsupported component collisions fail rather than silently
overwriting content" — but had no executable mechanics behind them.

Separately, five accepted contracts (`terminology.md`, `foundation-scope.md`,
`configuration-ownership.md`, `editor-integration.md`, and
`environment-variables.md`) already use "documented extension point" as an
accepted concept a future component or capability may rely on. None of them
defines what an extension point is, how a component declares one, or how a
contribution to it is expressed. This issue is where that gap closes.

## Decision

Define, in `docs/file-conflicts.md` and `forge_template.file_conflicts`, the
output target, disposition, and collision rules for a validated composition
plan:

- **Output target is path identity with a trailing `.jinja` stripped.** A
  content path ending `.jinja` renders to the stripped path; every other
  path copies literally at its own path. Two of one component's own files
  mapping to the same target is an authoring error.
- **Four dispositions are classified; two are granted.** `create` and
  `extend` are expressible in protocol v1. `merge` and `override` are
  defined precisely enough to state what they would mean, but no manifest
  field grants either — a collision that would need one fails clearly
  instead of silently choosing a resolution. This reads the issue's
  "reserve policy overrides for documented extension points" literally.
- **Extension points are optional, additive `component.toml` fields.**
  `[[extension_points]]` publishes a named point at an owned, in-`content_root`
  file; `[[contributions]]` targets another component's published point from
  a payload outside the contributor's own `content_root`, so it is never
  also emitted as its own output file. `manifest_version` stays `1`: both
  fields are optional, so every existing manifest remains valid, and ADR
  0024 is not superseded.
- **Contributions are validated catalogue-wide.** `validate_manifest_set`
  gains a check, alongside its existing cycle rejection, that every
  contribution names a real component and a real, published extension point
  on it — independent of any ProjectSpec selection. This is what makes it
  safe for plan resolution to silently drop a contribution whose owner
  happens not to be selected: a missing owner can only mean "not selected",
  never a typo.
- **The output plan resolves whole, before any file operation.** Every
  selected component's owned content becomes a target's `create` base, and
  every selected component's contributions attach as ordered `extend`
  entries onto the target their point lives in. This is required because the
  canonical extension case — a capability extending a platform's file — runs
  against composition order's own tier direction (capabilities apply before
  platforms). Resolving the whole plan first means a target's base is always
  supplied by its owner regardless of tier, and composition order only
  decides the order among multiple contributors once a target exists, never
  whether it exists yet.
- **Two components creating the same target is an unsupported collision**
  and raises, naming both components and the shared target — the executable
  form of `terminology.md` rules 2 and 5.
- **Foundation's targets are not overridable**, and Foundation publishes
  extension points like any other owner once it becomes a real content
  source, as required by `foundation-scope.md`'s neutral-handoff-material
  rule. A future `override` grant over a documented extension point remains
  Stage 09's decision.

`forge_template.file_conflicts` adds `output_target`, `component_targets`,
and `resolve_output_plan`, consuming `composition_plan`'s
`ComponentPlacement` sequence directly. It performs no file operations,
renders and splices no content, and defines no in-file marker syntax; those
remain FT-06.07 work.

## Consequences

- `ComponentManifest` gains two optional fields while remaining protocol 1;
  no existing manifest, including all four fixture components, needs any
  change to stay valid.
- `component_manifest.validate_manifest_set` becomes stricter again: a
  contribution naming a missing component or an undeclared extension point
  now fails with a clear `ValueError`, exactly as its existing cycle
  rejection already fails a cyclic catalogue.
- `merge` and `override` remain deliberately unavailable until a real
  production component justifies the concrete rules either would need;
  nothing here invents that vocabulary speculatively.
- FT-06.05 and FT-06.06 gain a concrete surface to build the option-schema
  vocabulary and composition fixtures against.
- The current v0.1.x Copier path, template tree, generated output, and CLI
  behaviour do not change. No generated project gains a dependency on
  `forge_template.file_conflicts`.
