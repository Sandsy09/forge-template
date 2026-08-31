# 37. Align Foundation after the two-archetype composition review

## Status

Accepted

## Context

Stage 08 added two independent production archetypes: `library` and `cli`.
Both render through the same implicit Foundation and public engine, and both
are exercised by the `create-forge` reference client. That makes accidental
coupling observable rather than hypothetical.

The comparison found deliberate duplicate package files, but also found four
Foundation leaks. Foundation emitted the typed-package classifier despite the
archetype owning `py.typed`; its Ruff, mypy, and pytest settings named the
current `src`/`tests` layout; and it installed coverage and pre-commit tooling
that ADR 0012 assigns to optional capabilities. The engine path also handed
off no `uv.lock`, contradicting ADR 0011's committed-lock guarantee.

## Decision

Keep the duplicate package-root `__init__.py`, `py.typed`, and test-package
markers independently owned by each archetype. Coincidental equality is not
a component dependency, and moving them into Foundation would create the
shared generated runtime/package layer ADR 0012 forbids.

Move `Typing :: Typed` into each archetype's existing classifier contribution.
Remove Foundation's hard-coded Ruff source roots, mypy file list/test override,
and pytest test path; repository-wide discovery preserves every mandatory gate
without encoding one project shape. Remove generated `pre-commit` and
`pytest-cov` dependencies, coverage configuration, and unsupported hook
guidance until real capabilities own them.

Expose `lock:check = "uv lock --check"` through Poe and document
`uv run --locked poe check` as the aggregate contract. Keep engine rendering
side-effect-free: dependency resolution belongs to client finalisation. The
reference client must run `uv lock` inside its adjacent staging directory
after writing rendered files and before atomic rename; failure must clean up
and leave the destination unchanged.

Bump both component versions to `1.0.1` and `forge-template` to `0.3.2`.
Retain ProjectSpec protocol `1`, manifest protocol `2`, option-schema protocol
`2`, Foundation protocol `1`, and every documented public API signature.

## Consequences

- Foundation remains provider-, framework-, domain-, and layout-neutral while
  still guaranteeing formatting, linting, typing, testing, aggregate quality,
  and lock-drift detection.
- Library and CLI keep complete, independent ownership of their package shape;
  no inheritance or cross-component resource access is introduced.
- Engine output no longer includes optional coverage or pre-commit feedback.
  The direct-Copier path is unchanged and retains both.
- `RenderedProject` remains deterministic and in-memory. A completed client
  generation additionally contains the finalisation-created `uv.lock`.
- `create-forge` needs uv in its optional engine installation and changes its
  engine-path happy path from network-free rendering to dependency resolution
  before handoff.
- No unrelated Foundation dependency, component kind, protocol, selection,
  schema, prompt, stored answer, or migration is added.
