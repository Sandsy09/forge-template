# 39. Deny policy-granted file overrides; publish the extension-point inventory as a versioned contract

## Status

Accepted

## Context

[file-conflicts.md](../file-conflicts.md) classifies four dispositions —
`create`, `extend`, `merge`, `override` — but protocol `1` only grants the
first two. It explicitly reserved the question of granting `override`
authority to organisation policy for a specific, documented extension point
as "Stage 09's decision to make."
[terminology.md](../terminology.md) named that decision FT-09.02.

[FT-09.01](../organisation-policy.md) fixed organisation policy as strict,
order-independent *selection* input — required, default, and forbidden
archetypes, capabilities, and platforms — with no route to files, content, or
executable behaviour. It left content-level extension entirely to this issue.

Without a published answer, a downstream Blueprint-style client has no stated
boundary for what is safe to change about generated output, and the
[#45](https://github.com/Sandsy09/forge-template/issues/45) issue summary
names the resulting risk directly: reliance on arbitrary file replacement.
[FT-09.03](https://github.com/Sandsy09/forge-template/issues/46)'s reference
fixture and [create-forge#54](https://github.com/Sandsy09/create-forge/issues/54)'s
downstream integration reference both need this settled before they can
implement or test against it; create-forge#54 has already committed to no
arbitrary file overlays, plugins, or executable policy hooks in anticipation
of this decision.

## Decision

Deny the reserved `override` grant. Organisation policy, in protocol `1`,
never gains authority to replace another owner's target content. `merge` and
`override` remain classified but ungranted; `GRANTED_DISPOSITIONS` stays
`("create", "extend")`, and `OutputContribution.disposition` stays typed
`Literal["create", "extend"]` so an override contribution is unconstructible,
not merely unused.

Publish the complete, closed set of safe extension surfaces in
[extension-points.md](../extension-points.md): component selection, project
metadata, component options, and declared content extension points reached
only through a selected component's own `[[contributions]]`. Publish the
current content extension-point inventory — the eight points Foundation's
`pyproject.toml.jinja`, `README.md.jinja`, and `.gitignore.jinja` declare, and
the six further Foundation files that declare none — as part of the
compatibility surface: adding a point is additive, removing or renaming one
is breaking and needs its own version transition. Pin the inventory with a
regression test.

State explicitly that post-render mutation of a `RenderedProject`, file
overlays, executable hooks, and the private `_CATALOGUE_ROOT_OVERRIDE`/
`_FOUNDATION_ROOT_OVERRIDE` test seams are not extension mechanisms and carry
no engine guarantee.

## Consequences

- An organisation or downstream client that wants content this catalogue does
  not produce must author or select a component, or wait for an owner to
  publish a new extension point in a release. There is no lower-effort route.
- `merge` and `override` remain named for precision — so this contract can
  state exactly what they would mean — without becoming available. A future
  ADR would be required to grant either, superseding this one.
- Downstream clients (FT-09.03, create-forge#54) can build against a closed,
  versioned inventory instead of inferring safety from current behaviour.
- No manifest field, ProjectSpec field, or public Python API changes. No
  `EngineErrorCode` is added; the existing `GENERATION_PLAN_FAILED` collision
  failure is documented rather than replaced. No template, Copier answer,
  package dependency, generated output, or package version changes.
- Organisation-policy parsing, resolution, and structured failures remain
  FT-09.01's standing deferral; this decision does not implement them.
