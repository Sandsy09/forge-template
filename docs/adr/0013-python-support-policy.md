# 13. Adopt a rolling CPython support policy

## Status

Accepted

## Context

Forge Foundation guarantees that a generated project can restore and validate
itself in a supported environment, but the accepted guarantees deliberately
left the exact Python policy to FT-00.04. The current Library template already
offers CPython 3.11 through 3.14, defaults its minimum to 3.11 and development
interpreter to 3.13, and computes an inclusive test matrix between those two
answers. Those values have no recorded lifecycle rule.

CPython publishes final feature releases annually and supports more releases
upstream than Forge needs to offer as generated-project defaults. Forge also
needs to adopt a new interpreter only after its dependencies and generated
projects work on it, while preserving Copier's recorded answers for projects
created under an older support window.

## Decision

Adopt the [Forge Python support policy](../python-support.md) as the canonical
living contract for generated projects and future compositions.

Forge supports final CPython releases only and maintains an active window of
the latest four feature releases. The default compatibility floor is the
oldest active release. The default development interpreter and tested upper
edge is the release immediately before the newest final release. A generated
project tests every feature release between its selected floor and development
interpreter, inclusive, while `requires-python` retains a lower bound without
an artificial upper cap.

A new final release enters the window only after Forge's dependencies, schema,
rendering, scaffold combinations, builds, and generated CI validate it. The
new release shifts both defaults according to the rules above. The outgoing
oldest release becomes deprecated but remains available, tested, and supported
for at least 90 days, producing a temporary five-release overlap.

Communicate deprecation through the canonical support table, a tracking issue
and pull request, generated prompt or guidance, and release notes. Remove the
version only in a later tagged release, label that removal as a breaking
change, and provide migration guidance.

Default changes affect new projects only. A transition may not silently raise
an existing project's recorded Copier answers. Removal must preserve safe
replay or stop with actionable guidance and require the project owner's
explicit choice.

The living reference owns current version numbers and examples. Changing its
durable window, defaults, implementation scope, notice period, or update rule
requires a superseding ADR.

## Consequences

- Forge has a predictable annual maintenance rule without hard-coding one
  temporary Python release into the architecture.
- New projects receive conservative defaults while the newest validated final
  release remains available to users who want it.
- A generated project's tested claim is explicit even though its package
  metadata permits forward-compatible newer interpreters.
- Python removals have a bounded overlap, visible notice, and an explicit
  migration obligation for Copier updates.
- PyPy, other implementations, and prereleases remain useful for exploration
  but are not supported by implication.
- Repository-local interpreter support for `forge-template` and
  `create-forge` remains independently owned.
- The existing question schema, generated output, application code, public
  APIs, and runtime behaviour do not change as a result of this decision.
