# 6. mypy default, pyright optional

## Status

Accepted

## Context

Scaffolded projects need a type checker as a CI gate. mypy and pyright are
the two realistic choices, and they differ enough in philosophy and
strictness defaults that picking one silently would be an opinionated call
made on the user's behalf either way.

## Decision

`type_checking` defaults to `mypy` (strict), with `pyright` (basic) and
`both` (chained via a combined `typecheck` Poe task) as alternatives.

mypy is the default because `strict = true` gives a single, well-known
strictness dial with broad ecosystem familiarity, and it's the option that
needs the least explaining in generated project docs. pyright is offered at
`typeCheckingMode = "basic"` rather than `strict` — its strict mode is
considerably more aggressive than mypy's, and defaulting pyright to
`basic` keeps the two options comparably strict rather than making `pyright`
look like the "harsher" choice by accident.

When `both` is selected, `[tool.mypy]` gains
`enable_error_code = ["redundant-expr", "truthy-bool"]` and a comment
explaining why: pyright owns unused-ignore reporting for its own
`# pyright: ignore` comment dialect, and without that tuning mypy would flag
those comments as its own unused ignores, which it cannot interpret.

## Consequences

- Generated projects that want only pyright, or want mypy at a laxer
  setting, edit `pyproject.toml` after scaffolding — there's no
  `mypy_strictness` sub-question, since a linked-pair-style mechanic (see
  [ADR 0004](0004-build-backend-and-versioning.md)) wasn't judged worth the
  schema complexity for a single tool.
- `both` costs real CI time (two separate typecheck invocations,
  `_typecheck_mypy` and `_typecheck_pyright` chained under `typecheck`) and
  is intended for projects that specifically want pyright's editor-integration
  strengths and mypy's ecosystem coverage simultaneously, not as a default
  recommendation.
