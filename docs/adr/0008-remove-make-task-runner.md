# 8. Remove `make` as a task_runner choice

## Status

Accepted

## Context

An earlier version of `copier.yml` offered `task_runner` as a question, with
`poe` (poethepoet) and `make` as choices. `make` was the widest-blast-radius
conditional in the whole schema — it touched the generated `Makefile`,
README instructions, and `_message_after_copy` — and it was never actually
exercised correctly:

- `make` is absent by default on Windows, the platform this template is
  developed and dogfooded on, so the `make` path could never be run
  end-to-end by its own author.
- Nothing in the validation suite (`scripts/test-combos.sh`) ever invoked
  `make` itself. Combo 4 (the "kitchen sink" combo, which flips every
  remaining conditional) set `task_runner=make` and then ran
  `uv run poe typecheck` directly — bypassing the very thing it was meant to
  test.
- The result, discovered only once combo 4's zero-byte-file assertion was
  added, was a byte-empty generated `Makefile` with an unrunnable
  `make check` instruction left in `_message_after_copy`. A user who
  selected `make` would have hit a broken first command.

## Decision

Remove `task_runner` as a question entirely. Every generated project uses
`poe` (poethepoet) unconditionally — it already was the only path that
worked.

This reverses previously shipped behavior; it is not a case of never having
offered `make`. Tracked for possible reintroduction as
[#1](https://github.com/Sandsy09/forge-template/issues/1).

## Consequences

- `template/pyproject.toml.jinja`'s `[tool.poe.tasks]` section and its
  companion Poe-based instructions in generated `README.md` /
  `CONTRIBUTING.md` no longer need `task_runner` conditionals at all —
  removing the branch removes the class of bug.
- Reintroducing `make` (#1) is scoped deliberately high: a real `Makefile`
  that mirrors every Poe task (not a stub), plus a CI job that runs
  `make check` on Linux as part of this repo's own validation — not just
  `test-combos.sh` invoking a `poe` task while claiming to test `make`. Until
  that CI job exists, `make` stays out.
