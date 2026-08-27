# 25. Define deterministic composition order

## Status

Accepted

## Context

[ADR 0023](0023-projectspec-protocol-v1.md) and
[ADR 0024](0024-component-manifest-protocol-v1.md) both defined a strict
request and metadata contract while explicitly deferring how a selection
applies. `docs/project-spec.md` states plainly that ProjectSpec's lexical
capability and platform arrays are "canonical wire ordering," not composition
ordering. `docs/component-manifests.md` goes further: reference arrays are
"canonicalised lexically for inspection; their source order is never
composition order," `validate_manifest_selection`'s lexical return order
"grants no rendering or overwrite authority," and — most concretely —
"Dependency cycles remain syntactically valid in protocol v1 so this issue
does not pre-empt the graph and deterministic-order decision. FT-06.03 must
define and reject unsupported cycles before any content operation occurs."
Both ADRs name this issue as the owner of exactly that gap.

A second, independently discovered gap made "deterministic" more than a
labelling exercise: `load_component_manifest` enumerates a component's owned
content with `content_root.rglob("*")`, whose iteration order is
filesystem-dependent. Ordering components alone would not make composed
output deterministic for a given ProjectSpec; content enumeration needed the
same treatment.

`docs/terminology.md`'s composition-and-authority rules are already
normative — "implicit last-write-wins replacement is forbidden" and
"unsupported component collisions fail rather than silently overwriting
content" — but rely on this issue and FT-06.04 for their mechanics.

## Decision

Define, in `docs/composition-order.md` and `forge_template.composition`, the
single deterministic order in which a validated ProjectSpec selection applies:

- **Kind is the outer key.** Foundation is the implicit mandatory baseline
  and precedes every tier without being a component itself. Selected
  components then apply archetype, then capabilities, then platforms, always
  in that order.
- **Within one tier**, apply the lexicographically smallest component whose
  same-tier `requires` targets have already been applied — a topological sort
  over that tier's own dependency edges, made a single deterministic total
  order by always picking the smallest ready node one at a time rather than
  an arbitrary valid ordering.
- **A `requires` edge that targets a different tier never reorders tiers.**
  It remains exactly what ADR 0024 already defined it as: a hard selection
  constraint, resolved entirely by `validate_manifest_selection`. This keeps
  a real, already-named case legal: `docs/supply-chain-provenance.md`'s
  future release-provenance capability may hard-require the `github`
  platform without capabilities and platforms interleaving.
- **Dependency cycles are rejected catalogue-wide**, in
  `component_manifest.validate_manifest_set`, using `graphlib` — stdlib, so
  no new dependency — over the complete supplied catalogue's `requires`
  edges. Because `composition_order` always calls
  `validate_manifest_selection` (which calls `validate_manifest_set`) before
  ordering any tier, every same-tier subgraph it orders is already proven
  acyclic; the ordering step itself does not re-implement cycle detection.
  This closes ADR 0024's deferred cycle-rejection obligation in exactly the
  place it named: before any content operation occurs.
- **A component's owned content applies in ascending POSIX-relative-path
  order**, replacing `rglob`'s filesystem-dependent enumeration and closing
  the second gap above.
- **Order confers no overwrite authority.** Being later in the order is
  never implicit permission to replace an earlier component's content — that
  boundary stays with FT-06.04, which owns file operations and collisions.

`forge_template.composition` adds `composition_order`, `component_content_order`,
and `composition_plan`, layered on the existing `component_manifest` and
`project_spec` models rather than replacing them. It does not discover
components, decide output paths, perform file operations, or expose a stable
engine error surface; those remain FT-06.04 and FT-06.07 work.

## Consequences

- `component_manifest.validate_manifest_set` becomes stricter: a cyclic
  catalogue that previously validated now fails with a clear `ValueError`
  naming the cycle. One existing test asserting the old permissive behaviour
  is replaced with one asserting rejection, exactly as ADR 0024 anticipated
  when it left cycles "syntactically valid" only "until ordering work."
- `graphlib` is part of the Python standard library, so no dependency is
  added to `forge-template` or to any generated project.
- FT-06.04 is unblocked: file conflict and override rules can now assume a
  single deterministic component order to define collisions over.
- A future engine must not reinterpret composition order as overwrite
  authority; that remains FT-06.04's decision to make, not an implicit
  consequence of this one.
- The current v0.1.x Copier path, template tree, generated output, and CLI
  behaviour do not change. No generated project gains a dependency on
  `forge_template.composition`.
