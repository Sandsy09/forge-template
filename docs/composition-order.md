# Composition order

Composition order is the single deterministic order in which a validated
[ProjectSpec](project-spec.md) selection of [component
manifests](component-manifests.md) applies. Protocol v1 is implemented by
[`forge_template.composition`](../src/forge_template/composition.py); this
document is its canonical contract, adopted by [ADR
0025](adr/0025-deterministic-composition-order.md).

## Scope

This contract defines order only. Output targets, dispositions, and collision
behaviour are now defined by
[file-conflicts.md](file-conflicts.md), delivered through
[FT-06.04](https://github.com/Sandsy09/forge-template/issues/35). This
contract does not define component discovery, a stable rendering API, or
structured engine errors — that is
[FT-06.07](https://github.com/Sandsy09/forge-template/issues/38). The
option-schema and template-variable vocabulary is now defined by
[template-variables.md](template-variables.md), delivered through
[FT-06.05](https://github.com/Sandsy09/forge-template/issues/36).

## Tier order

```text
Foundation
  then archetype        exactly one
  then capabilities     zero or more
  then platforms        zero or more
```

Foundation is the mandatory baseline received by every generated project. It
is not a component and never appears in a ProjectSpec selection, so it
precedes every tier implicitly rather than by comparison. Every selected
component then applies in kind order: the archetype first, then every
selected capability, then every selected platform. This mirrors the
structural model already stated in
[terminology.md's composition and authority section](terminology.md#composition-and-authority).

## Order within one tier

Within one tier, apply the lexicographically smallest component whose
same-tier `requires` targets have already been applied. Concretely: build a
graph of that tier's own components using only edges to other components in
the same tier, then repeatedly pick the lexicographically smallest node with
no remaining unapplied same-tier dependency, apply it, and repeat.

Picking one node at a time — rather than processing a whole "ready" batch in
lexical order before checking what became ready next — matters. Consider
three same-tier capabilities `a`, `b`, `c` where `b` requires `a` and `a`/`c`
have no dependencies. Both `a` and `c` are ready immediately. Taking the
smallest ready node one at a time yields `a`, which then makes `b` ready;
comparing `{b, c}` next yields `b` before `c`, for a final order of
`a, b, c`. Processing the first ready batch together in lexical order would
instead yield `a, c, b` — a different, incorrect order that ignores `b`'s
dependency on `a` relative to `c`.

This is exactly Kahn's algorithm for topological sorting, with the ready set
resolved by taking its lexicographic minimum at each step rather than in
arbitrary or insertion order.

## Cross-tier dependencies

A `requires` reference that targets a component in a different tier never
reorders tiers. It remains exactly what [the component manifest
protocol](component-manifests.md#dependencies-and-conflicts) already defines
it as: a hard *selection* constraint, evaluated entirely by
`validate_manifest_selection`. Tier order always wins over a cross-tier
dependency edge.

This is a real, already-named case, not a hypothetical one: a future
release-provenance capability may hard-require the `github` platform (see
[supply-chain-provenance.md](supply-chain-provenance.md)). That dependency
makes `github` a mandatory co-selection — composition still applies every
capability before every platform, so the provenance capability is never
pushed after the platform it depends on.

## Cycles

Dependency cycles are rejected **catalogue-wide**, in
[`component_manifest.validate_manifest_set`](../src/forge_template/component_manifest.py),
over the complete supplied catalogue's `requires` edges — independent of
component kind. This is deliberately broader than checking only the
components a given ProjectSpec selects: a cyclic bundled catalogue fails at
packaging and review time, before any user selection could ever reach it.

`composition_order` always calls `validate_manifest_selection` — which calls
`validate_manifest_set` — before ordering any tier. Every same-tier subgraph
it orders is therefore already proven acyclic; the ordering step itself does
not re-implement cycle detection. Cycles are rejected before any content
operation occurs, closing the obligation
[component-manifests.md](component-manifests.md#dependencies-and-conflicts)
left open: "Dependency cycles remain syntactically valid in protocol v1 so
this issue does not pre-empt the graph and deterministic-order decision.
FT-06.03 must define and reject unsupported cycles before any content
operation occurs."

## Content order within a component

A component's owned content applies in **ascending POSIX-relative-path
order** — plain string ordering of each file's path relative to the
component's `content_root`, forward-slash separated. This replaces
`load_component_manifest`'s internal use of `Path.rglob("*")`, whose
enumeration order depends on the underlying filesystem and is not guaranteed
stable across platforms or runs. Without this, component order alone would
not make composed output deterministic for a given ProjectSpec — a real gap,
not a theoretical one, since two component reference implementations already
ship nested content directories.

## Order is not authority

Composition order decides *when* a component applies, never *whether* it may
replace another component's content. This restates, without weakening,
[terminology.md's normative composition rules](terminology.md#composition-and-authority):
implicit last-write-wins replacement is forbidden, and unsupported component
collisions must fail rather than silently overwrite content. A component
placed later in this order gains no implicit permission over one placed
earlier. What happens when two components name the same output target —
targets, dispositions, extension points, and collision safety — is now
defined by [file-conflicts.md](file-conflicts.md), delivered through
[FT-06.04](https://github.com/Sandsy09/forge-template/issues/35).

## Determinism guarantee

For the same ProjectSpec and the same installed component catalogue, this
contract's order is identical regardless of the order manifests are supplied
in, `dict`/`set` iteration order, `PYTHONHASHSEED`, or the enumerating
filesystem. `forge_template.composition.composition_order`,
`component_content_order`, and `composition_plan` are the executable
reference implementation.

## Deferred work

This contract does not define:

- file operations, rendering, or the in-file extension-point marker syntax
  ([FT-06.07](https://github.com/Sandsy09/forge-template/issues/38)); output
  targets, dispositions, and collision handling are now defined by
  [file-conflicts.md](file-conflicts.md)
  ([FT-06.04](https://github.com/Sandsy09/forge-template/issues/35));
- the option-schema and template-variable vocabulary is now defined by
  [template-variables.md](template-variables.md)
  ([FT-06.05](https://github.com/Sandsy09/forge-template/issues/36));
- full composed-output fixtures
  ([FT-06.06](https://github.com/Sandsy09/forge-template/issues/37));
- component discovery, a stable rendering API, or structured engine errors
  ([FT-06.07](https://github.com/Sandsy09/forge-template/issues/38)); or
- organisation-policy resolution (Stage 09).

Until those coordinated contracts are complete, v0.1.x continues to pass its
plain answer mapping directly to Copier. No generated project depends on
`forge_template.composition` during normal development or runtime.
