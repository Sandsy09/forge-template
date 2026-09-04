# 57. Validate the cross-repository Data Science line

Date: 2026-09-04

## Status

Accepted

## Context

ADR 0056 (FT-14.01) reviewed the three-archetype, capability-bearing
composition and handed FT-14.02 a decision-complete `0.4.0` candidate with an
explicit mandate: validate current `forge-template` and `create-forge` `main`
together through the local sibling source, exercise all accepted Data Science
compositions plus Library and CLI, confirm deterministic failure cleanup,
re-check wheel resources and measured size, and record evidence without an
unpublished registry dependency.

Every existing check is one-sided. `uv run poe archetype` drives only the
engine path — a payload rendered in memory and written to a temporary
directory, never through `create-forge`. `create-forge`'s own suites drive the
real `new --engine-preview` console script, but its `uv.lock` resolves
`forge-template 0.4.0` from PyPI; nothing installs the two working trees
together. `create-forge`'s canonical
[`tests/test_engine_cross_repository.py`](https://github.com/Sandsy09/create-forge/blob/main/tests/test_engine_cross_repository.py)
and its documented sibling-checkout command exist specifically to close this
gap, but only from the client side, and only as a manual step a contributor
must remember to run.

The Data Science line adds real cost to skipping this: a real `uv lock`
resolution and a live Jupyter kernel per generated project. A CI job that
re-ran the full sweep on every `forge-template` push would also break
whenever `create-forge`'s `main` moved, coupling two independently released
repositories' CI in a way [ADR 0003](0003-two-repo-split.md) deliberately
avoided.

## Decision

Add `tests/test_cross_repository_validation.py` under a new `crossrepo`
pytest marker and `poe crossrepo` task. It builds one isolated virtual
environment holding both local working trees as path installs — never an
index — and through it:

- confirms neither distribution resolved from PyPI (a `direct_url.json` check
  on each);
- confirms the installed engine's `get_engine_info()` and
  `discover_components()` results match the FT-14.01 handoff table exactly
  (package `0.4.0`; ProjectSpec protocol `(1,)`; manifest protocols `(1, 2)`;
  five components at their reviewed versions; `data-science` requiring
  `jupyter>=1,<2`), and that the version satisfies `create-forge`'s declared
  `>=0.4,<0.5` range;
- generates all ten valid archetype/capability compositions through the real
  `create-forge new --engine-preview` console script, asserting project
  shape, a clean `uv lock --check`, no Forge dependency in the lock, and no
  surviving staging artefact;
- proves render determinism by regenerating two compositions into fresh
  destinations and comparing every rendered byte;
- proves deterministic failure cleanup across four rejected requests
  (`data-science` missing its required capability two ways, an unknown
  component, an unknown component-option owner), each asserting the
  destination was never created;
- runs the two Data Science compositions' own generated `poe check` —
  including live-kernel `notebook:check` — at Python 3.11, 3.13, and 3.14; and
  finally
- runs `create-forge`'s own `tests/test_engine_cross_repository.py` against
  that same paired environment, using its documented invocation.

This is deliberately **not** added to `.github/workflows/test-template.yml`.
It is opt-in and sibling-gated: a new `--create-forge-root` pytest option
(mirroring `create-forge`'s own `--forge-template-root`) defaults to
`../create-forge`, and the whole module skips with a clear message when no
such checkout is present. `poe check`'s `pytest` invocation excludes the new
marker alongside `combos`/`update`/`archetype`, so an ordinary contributor
checkout — with no sibling `create-forge` present — is unaffected.

Also pin, rather than merely restate, ADR 0056's package-size review
figures. Foundation plus every catalogue component's tree (excluding
`__pycache__`) reproduces exactly as 60 files and 39,182 bytes, and the seven
duplicate-resource groups reproduce exactly as 892 bytes of overhead — both
deterministic sums of tracked file sizes, now asserted by
`tests/test_composition_architecture_review.py`. The built wheel's exact byte
count is not pinned the same way: zip metadata (timestamps, compression) is
not byte-reproducible across machines. `scripts/check_wheel.py` instead gains
a generous ceiling (128 KiB) around the reviewed 72,566/72,544-byte
measurements, failing loudly on unbounded growth without chasing an
unreproducible exact figure.

Record the full run — commands, both validated revisions, the composition
matrix, failure-cleanup evidence, and re-measured size figures — in
[docs/cross-repository-validation.md](../cross-repository-validation.md).

## Consequences

- forge-template and create-forge `main` are proven compatible through their
  real local sources, closing the one gap FT-14.01 could not: every prior
  check exercised one repository's path in isolation.
- The validation is repeatable by any contributor with both repositories
  checked out as siblings, and by no one else — it costs nothing when absent.
- `forge-template`'s own CI stays hermetic and independent of `create-forge`'s
  `main`. Cross-repository regressions are only caught when someone runs
  `poe crossrepo` locally, which is the accepted trade-off: `create-forge`'s
  own release process already re-validates this pairing before every
  `create-forge` release ([integration-contract.md](https://github.com/Sandsy09/create-forge/blob/main/docs/integration-contract.md#release-coordination)),
  so the risk this leaves open is bounded to the window between a
  forge-template merge and the next deliberate cross-repository check.
- The package-size figures are now regression-pinned; a deliberate content
  change must update the pin, the wheel ceiling, and the recorded prose
  together, the same discipline `tests/test_compatibility_policy.py` already
  applies to protocol and version figures.
- No template, Copier answer, Foundation/component resource, manifest, engine
  module, public signature, `EngineErrorCode`, protocol integer, component
  version, golden digest, package version, tag, release, or `create-forge`
  file changes. The package stays `0.4.0` and untagged; FT-14.03 alone bumps
  and publishes `0.4.1`.
