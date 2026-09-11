# 66. Validate provider parity, reproducibility and distributions

Date: 2026-09-11

## Status

Accepted

Executes the acceptance matrix
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md)
(FT-15.04 / [ADR 0061](0061-provider-compatibility-failure-and-release-gates.md))
fixed and FT-17.01 through FT-17.04 implemented against. It does not
supersede any prior record; it is the validation issue those four records
each deferred rows to. Fifth implementation issue of
[FT-EPIC-17](https://github.com/Sandsy09/forge-template/issues/142), after
[ADR 0062](0062-generation-metadata-and-manifest-protocol-3.md) (FT-17.01),
[ADR 0063](0063-implement-the-github-platform.md) (FT-17.02),
[ADR 0064](0064-implement-approved-generated-content-parity.md) (FT-17.03),
and [ADR 0065](0065-implement-reproducible-rendering-for-updates.md)
(FT-17.04).

## Context

[FT-17.05](https://github.com/Sandsy09/forge-template/issues/154) is the
fifth implementation issue of Stage 17. FT-17.02 and FT-17.03 tripled the
discovered catalogue — five components to fourteen — but every new component
was proven only by fast, in-memory render assertions. Auditing the
`archetype`-marked build suite (six modules, the only place the engine's
output is really built, installed, and checked) found four concrete gaps
FT-17.05 exists to close:

- **No `archetype`-marked test selects the `github` platform or any of the
  eight FT-17.03 capabilities.** Every module hardcodes `"platforms": []` and
  uses only `jupyter` / `scientific-python`. `coverage`'s CI gate,
  `pyright`'s type-check task, `docs:build`, and a real
  `pre-commit run --all-files` had never executed against engine-rendered
  output, and invariant 1 (generated output is pre-commit clean) had never
  been checked on the engine path at all.
- **"Every valid composition" was stale.** Three hand-written literals
  (`tests/test_composition_architecture_review.py`,
  `tests/test_cross_repository_validation.py`,
  `tests/test_capability_composition.py`) each still meant the pre-Stage-17
  ten. The real count, derived from the installed catalogue's own
  `requires` / `conflicts` edges, is 2240.
- **The provider's own sdist had never been audited.**
  `scripts/check_wheel.py` built and checked a wheel only.
- **Two acceptance-matrix rows cited evidence that did not prove them.** The
  no-resource-read row named `tests/test_compatibility_policy.py`, which
  contained no such assertion; the signature-stability row named
  `tests/test_engine.py`, which pinned a name set only, never an actual
  parameter list.

## Decision

Execute the seven FT-17.05-owned acceptance-matrix rows (E1, E2, G1, G2, I1,
I2, R1) with real evidence, and ship the tests that make each one durable.
Record the four confirmed calls here.

1. **Three full-composition build cells, one per archetype.** `library`,
   `cli` and `data-science`, each paired with `github` and every capability it
   can carry (`renovate` excluded — it conflicts `dependabot`;
   `documentation` excluded outside `library` — it `requires` `library`).
   Each cell: lock, sync, build (wheel + sdist), isolated install, the
   generated project's own locked `poe check` (now genuinely exercising
   `coverage`, `typecheck:pyright`, and `notebook:check`), then a real
   `git init` + `pre-commit run --all-files`, then the Forge-freedom probe at
   both build time (the lockfile) and install time (a clean venv). Rejected:
   one `library`-only cell (leaves `cli` / `data-science` full compositions
   unbuilt); twelve cells across both dependency-updater capabilities and
   both Python window edges (45+ minutes; `dependabot` and `renovate` differ
   only by a static config file, not a code path worth doubling for).

2. **The composition sweep is exhaustive — all 2240, twice over — under its
   own marker with two parallel CI jobs.** `tests/composition_matrix.py`
   derives every accepted selection from `discover_components()`'s own
   path-free `requires` / `conflicts` edges (needing no component resource to
   compute — itself a demonstration of the no-resource-read rule the sweep
   separately proves), applying exactly the rule
   `component_manifest.validate_manifest_selection` enforces. `poe check`
   stays fast and unchanged; a new `sweep` marker carries the cost, with
   `--no-cov` — coverage.py's branch tracing measurably slows this many
   CPU-bound in-process calls, unlike `combos`/`archetype`/`crossrepo`, where
   subprocess wall time dominates and the same instrumentation is noise, and
   every line the sweep exercises is already covered elsewhere by `poe
   check`. Measured, single-process, no coverage: ~1 s per composition.
   Decision 3 adds a second, equally exhaustive sweep under the same marker
   (the independent-client proof), so the real combined total is 4481 cases
   (2 × 2240 + one tripwire) — measured, locally, at ~47 minutes in one
   `-n 4` job, an underestimate this ADR's first draft made by budgeting for
   only one sweep. Split into two parallel CI jobs (`sweep-composition`,
   `sweep-independence`), each still `-n 4`, on the reasoning that this would
   keep the critical path near the existing `archetype` job's local-measured
   cost. The real GitHub Actions numbers, once observed, were far better than
   either local figure suggested: 4m02s and 7m23s respectively — a Linux CI
   runner with a warm `uv` cache and datacenter network resolves this
   in-memory, no-network workload much faster than the Windows dev machine
   this ADR's estimates came from (the `archetype` job's own real CI cost was
   similarly overestimated beforehand, at ~1m43s). The split was still the
   right call — it keeps the critical path parallel rather than serial — even
   though the magnitude of the problem it solves turned out smaller than
   measured locally. `uv run poe sweep` locally still runs both as one task.
   Rejected: a bounded ~100-composition derived sample (narrows the
   contract's literal "every valid composition"); an opt-in marker CI never
   runs (issue #154 itself forbids a local-green-only claim); one combined CI
   job (confirmed-real ~47-minute critical path, needlessly serial when the
   two sweeps share no state).

3. **The independence row is proven provider-side in-repo; the create-forge
   half is recorded as a contract-sanctioned lag, not patched.**
   `tests/no_copy_downstream.py` (already facade-only, already AST-enforced
   against a `create_forge` or private-seam import by
   `tests/test_no_copy_inheritance.py`) grows an exhaustive sweep over the
   same 2240 compositions, proving a policy-driven client's render is
   byte-for-byte identical to a direct `render_project` call for every one of
   them. `poe crossrepo` is still run and its result recorded: 19 passed, 1
   failed. The one failure shells out to create-forge's own canonical
   `tests/test_engine_cross_repository.py`, which fails at collection —
   create-forge `main` constructs `EngineInfo(...)` there without the
   FT-17.01 `metadata_version` field (the same root cause recurs in four more
   of create-forge's own test helpers per a source grep, though `poe
   crossrepo` itself exercises only the one file) — expected, since the
   cross-repository gate table places client adoption at CF-18.01, strictly
   after the `0.5.0` release this repository has not yet performed. Rejected:
   marking the row simply "blocked"
   (leaves an FT-17.05-first-required row unevidenced, weakening the FT-17.06
   release gate, which requires every Independence row to have passed on
   `main`); editing the sibling `../create-forge` checkout (a standing
   constraint, and it would pre-empt CF-18.01's own reviewed adoption step).

4. **`poe check:wheel` is extended to the sdist.** Both artefacts are built
   (`uv build`, not `uv build --wheel`); the same `_MUST_CONTAIN` positive
   list applies to the sdist's members (prefix-adjusted for
   `<name>-<version>/src/forge_template/...`); the wheel's
   `_MUST_NOT_CONTAIN` exclusion list does **not** apply to the sdist — by
   design (no `[tool.hatch.build.targets.sdist]` override), the sdist
   correctly contains the full repository, including `adr.py` and
   `render.py`, so a client can rebuild the wheel or run this repository's
   own tests from it; applying the wheel's exclusion list there would always
   fail, for the right reason. A new `_MAX_SDIST_BYTES` ceiling (2 MiB,
   measured ~726 KB) and an isolated-import smoke run apply to it too. Both
   artefacts' name, size, and sha256 are now printed as acceptance evidence.
   Rejected: wheel-only with a recorded narrowing (FT-17.06 publishes both
   artefacts, and the release gate names "the PyPI wheel/sdist" explicitly).

### A defect the validation itself found

Building the first full-composition cell surfaced a real, previously
unreachable defect: `pre-commit`'s `check-added-large-files` hook (no
`args` or `exclude` override) rejected the generated project's own `uv.lock`
once `jupyter` and `scientific-python` were both selected — a fully valid,
unremarkable composition, not a synthetic edge case. Measured: no-capability
lock 100 KB, `jupyter`-only 340 KB (already close to the hook's 500 KB
default), `jupyter` + `scientific-python` + every other capability 636 KB.
This is exactly the class of gap FT-17.05 exists to find — the first time
`pre-commit run --all-files` had ever executed against engine-rendered
output.

Confirmed with the maintainer before fixing: **fix it in this issue.**
`pre-commit`'s own upstream documentation names lockfiles as the standard
exclusion for `check-added-large-files` (they are large by design, not
"added by mistake") — the same remedy real-world templates apply to
`poetry.lock` / `package-lock.json`. One line,
`exclude: ^uv\.lock$`, added to the hook in
`src/forge_template/components/pre-commit/content/.pre-commit-config.yaml.jinja`.
`pre-commit` moves `1.0.0` → `1.0.1` (a content change, the compatibility
policy's patch-bump rule for a non-breaking fix); the content-tree size pin
in `tests/test_composition_architecture_review.py` moves 68,378 → 68,954
bytes (file count and duplicate overhead unaffected). Rejected: filing a
follow-up issue and narrowing the pre-commit step's capability set (leaves a
real generated-project defect on `main` for longer, for a one-line fix with
an obvious correct remedy); dropping the pre-commit step from this issue
entirely (weakens FT-17.05's own G1 row more than the alternatives).

### What ships

- `tests/test_full_composition_build.py` — decision 1's three cells
  (`archetype`-marked).
- `tests/composition_matrix.py` (`valid_compositions()`, `Composition`) and
  `tests/test_composition_sweep.py` — decision 2's exhaustive sweep, plus a
  size tripwire against the catalogue changing under it. New `sweep` pytest
  marker and `poe sweep` task (`--no-cov`, `-n 4`).
- `tests/no_copy_downstream.py` / `tests/test_no_copy_inheritance.py` grow
  `test_downstream_client_renders_every_valid_composition_identically`,
  parametrised over the same 2240 compositions and `sweep`-marked.
- `.github/workflows/test-template.yml` gains two new jobs,
  `sweep-composition` and `sweep-independence`, running the two sweeps above
  in parallel (each its own `pytest -m sweep <path> -n 4 --no-cov`) rather
  than as one serial job — see decision 2.
- `tests/test_compatibility_policy.py` gains
  `test_client_selection_reads_no_component_resource` (row I2), reusing the
  path-leak token list now named `PATH_LEAK_TOKENS` in
  `tests/test_capability_composition.py` rather than duplicated.
- `tests/test_engine.py` gains a signature pin
  (`test_public_callable_signatures_are_pinned`, `inspect.signature` over
  every public callable) and a result-model field-set pin
  (`test_public_result_model_fields_are_pinned`) — row E2, evidenced for
  real rather than by the existing name-only `_FROZEN_PUBLIC_API` set.
- `scripts/check_wheel.py` — decision 4's sdist audit, plus an
  isolated-import smoke that now also negotiates via `get_engine_info()` and
  renders one composition end to end (not only `discover_components()`), and
  an `_identity()` helper printing name/size/sha256 for both artefacts.
- `src/forge_template/components/pre-commit/` — the `uv.lock` exclusion,
  `1.0.0` → `1.0.1`.
- `docs/provider-acceptance-validation.md` — the canonical evidence record:
  validated revisions, commands, platforms, Python versions, the seven-row
  result table, artefact identities, measured coverage floors, and the
  recorded create-forge lag.

### Recorded narrowings

- The independence row (I1) is proven exhaustively on the provider side; the
  client-consumption half stays evidenced only against create-forge `main`'s
  current (lagging) state, not a `metadata_version`-aware client — CF-18.01
  and FT-18.01 close that gap after the `0.5.0` release.
- The sdist audit's negative obligation (`_MUST_NOT_CONTAIN`) does not apply
  to the sdist itself, only the wheel — a deliberate, documented asymmetry,
  not an oversight.

## Consequences

- `pre-commit` moves `1.0.0` → `1.0.1`; every other component, Foundation,
  `copier.yml`, and `template/**` are unchanged. `main` stays `0.4.1` and
  untagged — FT-17.06 releases `0.5.0`.
- The content-tree size pin in
  `tests/test_composition_architecture_review.py` moves to 112 files,
  68,954 bytes; `tests/fixtures/archetype_regression/digests.json` and the
  composition golden fixtures are untouched — no component in their pinned
  combinations changed.
- `poe check` gains two new fast tests (rows I2, E2) but stays fast; `poe
  archetype` gains one new slow module (decision 1); a new `poe sweep` task
  and CI job carry decision 2 and the independence sweep.
- `_MAX_SDIST_BYTES` joins `_MAX_WHEEL_BYTES` in `scripts/check_wheel.py`;
  both artefacts' identities are now printed as release-adjacent evidence.
- `FT-EPIC-17` moves to 5/6; `FT-17.06` (blocked only by FT-17.05) is
  unblocked.
