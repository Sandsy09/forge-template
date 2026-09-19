# 72. Validate Streamlit generated projects and distributions

Date: 2026-09-19

## Status

Accepted

Implements the generated-project, Python-endpoint and regression rows that
[ADR 0069](0069-streamlit-composition-compatibility-and-acceptance.md) assigned
to FT-20.03. It follows [ADR 0055](0055-validate-data-science-generated-projects.md),
the same validation for Data Science, and amends none of the Stage 19 or Stage 20
records.

## Context

[ADR 0070](0070-streamlit-archetype-implementation.md) and
[ADR 0071](0071-streamlit-tasks-safeguards-and-composition.md) built and completed
the `streamlit` archetype. Their evidence was by construction: fast render-level
tests, a lock-only resolution sweep, and a prototype that rendered each selection
and ran its `poe check` by hand. The compatibility contract also fixes what
acceptance must be, and none of it was yet an executable, repeatable check:
restoration from a committed lock, the per-run and per-project smoke bounds, the
"no persistent server" rule, module-only distributions, Forge-free installs, a
byte-level regression pin on the other archetypes, and wheel and sdist audits that
include every new engine resource.

Running a real check against a new archetype for the first time has found a real
defect at every earlier stage: two in FT-12.03 and the NumPy stub incompatibility
in FT-20.01. This record therefore also states what this validation found.

## Decision

1. **Follow the Data Science shape.** A slow endpoint module, a fast harness
   module, a fast composition addition, a validation document and this record.
   *Rejected:* one large module, which would put the fast proofs of the guard and
   the bound behind a network-bound marker so they would rarely run.
2. **One cell per selection per window edge.** `tests/test_streamlit_endpoints.py`
   (`archetype`-marked, `-n 4`) runs the four accepted selections at Python 3.11 and
   3.14. Each cell locks; restores from that lock in a clean copy with no virtual
   environment; shows that a copy whose dependency declaration drifted from the
   lock is refused; runs `uv run --locked poe check`; builds a wheel and an sdist;
   installs the wheel in an isolated environment and imports the package and
   `<package>.app`, reporting `__version__`, `Requires-Python` and `py.typed`; and
   checks that neither the lock nor the installed environment names a Forge
   package. The clean-copy restoration and the drift refusal are the first
   executable form of the contract's committed-lock steps: the earlier modules lock
   and sync in place.
3. **Prove "no server" with a listen guard.** Each cell's `poe check` runs with a
   temporary `sitecustomize.py` on `PYTHONPATH` that makes `socket.socket.listen`
   raise, so any server started anywhere in the check, Streamlit's included, fails
   the cell. Fast tests prove the guard trips on a plain `listen` and on an asyncio
   server, so it cannot decay into a no-op. *Rejected:* probing a port afterwards,
   which is vacuous because `AppTest` never binds one; and static checks alone,
   which assert nothing about what ran. The guard allows exactly one caller,
   CPython's `socket.py` socketpair fallback (`socketpair` up to 3.11,
   `_fallback_socketpair` from 3.12): on Windows the asyncio proactor loop builds
   its in-process self-pipe with a loopback `listen` that closes at once, and
   without the exception the guard breaks every asyncio program there, `poe`
   included. That detail surfaced twice, first at 3.13 and then at 3.11 where the
   helper has the other name; on a runner where CPython renames it again the cells
   fail loudly rather than pass falsely.
4. **Bounds are enforced, and are the contract's numbers.** `tests/streamlit_harness.py`
   runs each command exactly once under a `subprocess` timeout and raises on
   expiry; the generated `poe check` gets 600 seconds and the smoke's own `AppTest`
   run 10, as the contract fixes. A fast test proves a timeout fails and the command
   ran once, and another pins both numbers and the endpoints to the contract's
   constants table, so neither can drift from it. Nothing retries and nothing raises
   a bound. Steps the contract does not bound (lock, sync, build, install) share a
   generous ceiling so a hung step fails instead of hanging the suite.
5. **Audit the artefacts, worst case first.** A planted `.streamlit/secrets.toml`
   is built into a wheel and an sdist. Both must carry the module tree and
   distribution metadata only: no marker, no `.streamlit/`, no root `app.py`, no
   `tests/`. This turns the contract's "deliberate consequence" that the launcher
   and configuration are source-tree files into an enforced property.
6. **Add the Streamlit cell to the full-composition build.** `tests/test_full_composition_build.py`
   gains its fourth cell, with `github` and every capability Streamlit can carry.
   It runs the coverage gate at 80 percent, `pyright`, and a real
   `pre-commit run --all-files`, none of which had ever run against Streamlit
   output.
7. **Pin the other archetypes byte for byte.** The recorded digests gain
   `data-science` (its two valid selections) and `streamlit` (four), and the test
   that reads them is generalised and renamed. The eight existing `library` and
   `cli` digests are unchanged, so Library, CLI Application and Data Science are
   protected by construction rather than by assertion.
8. **Derive the distribution audit from the source tree.** `scripts/check_wheel.py`
   keeps its hand-kept required list, and additionally requires every file that is
   on disk under the Foundation and component trees, hidden ones included, to be in
   both the wheel and the sdist. Its isolated-install smoke also renders a
   Streamlit project from the installed artefact and checks the launcher, the
   hidden configuration, the `run` task and the secrets ignore rule. *Rejected:*
   extending only the hand list, which is how a new component's nested or hidden
   file goes unlisted.
9. **Finish the deterministic-render obligations.** The fast composition module
   gains byte-identical output under four `PYTHONHASHSEED` values in separate
   processes, and `ruff format` and `ruff check` clean at Python floors 3.11 and
   3.14 for every accepted selection, since 3.14 changes ruff's target and its
   formatting of `except` groups.

**What the validation found.** No defect in the archetype's content: all eight
cells, the full-composition cell and the artefact audit passed against the shipped
component, so `streamlit` stays at `1.0.0` with no change to any file it owns. The
one thing it did find was in the harness, the socketpair detail in decision 3. No
engine module, public signature, `EngineErrorCode` value, protocol integer,
Foundation file or existing component changed, and the package stays `0.5.0` and
untagged.

## Consequences

- Every Generated-project, Python-endpoint and Regression row of the acceptance
  matrix now names a command that runs and passes, so FT-20.04's entry criteria can
  be evidenced rather than asserted.
- `library`, `cli`, `data-science` and `streamlit` output is byte-pinned across
  every selection each accepts. Any change that moves their rendered bytes fails
  `tests/test_data_science_composition.py` until the digests are regenerated with
  `--update-goldens` and the diff reviewed.
- `uv run poe archetype` gains nine endpoint tests and one full-composition cell.
  Run under `-n 4` the endpoint module took about eight minutes and the
  full-composition cell about ten on a local Windows machine.
- The listen guard is maintained code with a known platform dependence. It errs
  toward a false failure, never a false pass, and its own tests fail first.
- Nothing here publishes. FT-20.04 still owns the `0.6.0` release and the
  package-line tripwires it moves.
