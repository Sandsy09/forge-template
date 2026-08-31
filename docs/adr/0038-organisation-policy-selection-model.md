# 38. Define organisation policy as constrained selection input

## Status

Accepted

## Context

ProjectSpec protocol `1` carries an effective component selection and optional
profile/policy provenance, but deliberately contains no policy document or
unresolved user intent. The terminology contract gives organisation policy
higher authority than explicit choices for required and forbidden constraints,
while keeping Foundation guarantees absolute and policy outside the rendering
component model.

Stage 09 needs a portable contract that a future Blueprint-style client can
apply without copying Forge templates or depending on `create-forge`
internals. It must support multiple policies without caller-order behavior and
must not create a route for arbitrary files, code, secrets, or runtime
dependencies. The later reference fixture and downstream-client issues need
the semantics fixed before they can implement or test them.

## Decision

Define strict JSON organisation-policy protocol `1`. Each document has a
lower-case kebab-case ID and default, required, and forbidden rules over
archetype, capability, and platform selections only. It contains no project
metadata, Python constraints, component options, versions, files, executable
hooks, imports, or remote sources.

Resolve authority per selection kind as profile default, merged policy
default, explicit user choice, then required/forbidden validation. An explicit
choice replaces defaults, including an explicitly empty optional-component
list. Required and forbidden rules reject a non-conforming result rather than
silently rewriting it.

Treat policies as an unordered set. Set-like rules union; identical archetype
defaults or requirements may coexist. Duplicate policy IDs, differing
archetype defaults or requirements, default/required disagreement, and any
default or required selection that is also forbidden fail deterministically.

Validate referenced IDs and kinds against the installed catalogue when the
policy is applied, then run normal ProjectSpec/component validation. On
success, record the lexically sorted policy IDs in existing
`SelectionProvenance.policies`; retain ProjectSpec protocol `1`.

Define structured failure operation `resolve-organisation-policy` with
categories for invalid documents, contradictory policy sets, and selection
violations. Do not add those categories, policy models, parsing, resolution,
or public functions to the current Python facade in this decision-only issue.

## Consequences

- Future downstream clients share one deterministic policy contract while
  retaining ownership of source trust, prompting, explicit-choice tracking,
  ProjectSpec construction, diagnostics presentation, and filesystem work.
- Policy remains selection input rather than a component or rendering layer;
  it cannot weaken Foundation or bypass manifest and engine validation.
- Multiple policy provenance remains order-independent and compatible with
  the existing ProjectSpec wire shape.
- Component options, metadata, Python rules, policy versions beyond protocol
  `1`, executable resolution, and all safe file extension/override decisions
  remain later Stage 09 work.
- No template, Copier answer, package dependency, generated output, public
  Python API, package version, or runtime behavior changes.
