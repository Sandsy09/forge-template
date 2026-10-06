# 83. Validate batch generated projects and distributions

Date: 2026-10-01

## Status

Accepted

Implements the generated-project, Python-endpoint and regression rows that
[ADR 0081](0081-batch-composition-compatibility-and-acceptance.md) assigned to
FT-28.02. It follows [ADR 0072](0072-validate-streamlit-generated-projects.md),
the same validation for Streamlit, and amends none of the Stage 27 or Stage 28
records.

## Context

[ADR 0082](0082-batch-archetype-implementation.md) built the `batch`
archetype. Its evidence was by construction: fast render-level tests and the
engine-side contract/gate pins. None of it was yet an executable, repeatable
check against a real generated project: restoration from a committed lock,
the per-run and per-project smoke bounds, deterministic sample-job output,
idempotency, fail-fast-with-no-output, module-only distributions, Forge-free
installs, a byte-level regression pin on the other archetypes, provenance
reproduction, and the exclusion of `data/output.json` from update planning.

Running a real check against a new archetype for the first time has found a
real defect at every earlier stage: two in FT-12.03, the NumPy stub
incompatibility at FT-20.01, and the harness's socketpair detail at FT-20.03.
This record therefore also states what this validation found.

## Decision

1. **Follow the Streamlit shape, with one necessary difference.** A slow
   endpoint module (`tests/test_batch_endpoints.py`), a fast harness module
   (`tests/batch_harness.py`), fast harness proofs
   (`tests/test_batch_harness.py`), a validation document and this record —
   mirroring `tests/streamlit_harness.py` / `tests/test_streamlit_endpoints.py`
   / `tests/test_streamlit_harness.py`. Batch starts no server, so there is no
   listen guard; the smoke instead runs the generated job itself (the console
   script and `python -m <package_name>`) and asserts its output.
2. **One cell per selection per window edge.** `tests/test_batch_endpoints.py`
   (`archetype`-marked) runs the four accepted selections at Python 3.11 and
   3.14. Each cell locks; restores from that lock in a clean copy with no
   virtual environment; shows that a copy whose dependency declaration
   drifted from the lock is refused (batch itself declares no runtime
   dependency, so the drift is injected by prepending a new one to the
   project's `dependencies` list rather than editing an existing pin, the way
   Streamlit's cell does; `scientific-python` makes that list non-empty, which
   an earlier empty-list assumption missed); runs `uv run
   --locked poe check`; runs the job via both entry points and asserts the
   transformed output, idempotent rerun, and fail-fast-with-no-output on a
   malformed record; builds a wheel and an sdist; installs the wheel in an
   isolated environment and imports the package and `<package>.job`,
   reporting `__version__`, `Requires-Python` and `py.typed`; and checks that
   neither the lock nor the installed environment names a Forge package.
3. **Bounds are enforced, and are the contract's numbers.**
   `tests/batch_harness.py` runs each command exactly once under a
   `subprocess` timeout and raises on expiry; the generated `poe check` gets
   600 seconds and the job itself 5, as the contract fixes. A fast test
   proves a timeout fails and the command ran once, and another pins both
   numbers and the endpoints to the contract's constants table. Nothing
   retries and nothing raises a bound.
4. **Audit the artefacts, worst case first.** A planted `data/secret.json` is
   built into a wheel and an sdist. Both must carry the module tree and
   distribution metadata only: no marker, no `data/`, no `tests/`. This turns
   the contract's "deliberate consequence" that the sample input is a
   source-tree file into an enforced property.
5. **Add the batch cell to the full-composition build.**
   `tests/test_full_composition_build.py` gains its fifth cell, with `github`
   and every capability batch can carry. It runs the coverage gate at 80
   percent, `pyright`, and a real `pre-commit run --all-files`, none of which
   had ever run against batch output.
6. **Pin the other archetypes byte for byte.** The recorded digests gain
   `batch` (four selections). The fourteen existing `library`, `cli`,
   `data-science` and `streamlit` digests are unchanged, so they are
   protected by construction rather than by assertion.
7. **Extend provenance and update evidence to every archetype, not just
   three.** `tests/test_generation_provenance.py`'s reproduction-guarantee
   parametrisation had never been updated past FT-17.04's original three
   archetypes; it gains `streamlit` and `batch`. A new test proves ADR 0081
   choice 2 directly: `data/output.json` is absent from every render and
   never appears as an `plan_update` target for a batch-containing project.
8. **Derive the distribution audit from the source tree.** `scripts/check_wheel.py`
   already required every file on disk under the Foundation and component
   trees (FT-20.03) and already rendered a batch project from the installed
   artefact (FT-28.01); no further change was needed there.

**What the validation found.** One real defect in the archetype's own content:
`job.py`'s atomic-overwrite used `os.replace(tmp_path, path)`, which forge-
template's own `poe check` never saw because the file is `.py.jinja`, not
`.py` — ruff does not lint template sources. The first real `uv run --locked
poe check` against a *rendered* batch project failed `ruff`'s `PTH105`
(`os.replace()` should be `Path.replace()`). Fixed to `tmp_path.replace(path)`,
which keeps ADR 0080 choice 7's atomic-rename guarantee (`Path.replace` calls
the same platform `os.replace` under the hood) and removed the now-unused
`import os`. The regression digests and composition fingerprints were
regenerated to reflect the corrected bytes; no other file the archetype owns
changed, and no engine module, public signature, `EngineErrorCode` value,
protocol integer, Foundation file or sibling component changed. The package
stays `0.6.0` and untagged; `batch` stays at component `1.0.0`.

## Consequences

- Every Generated-project, Python-endpoint and Regression row of the
  acceptance matrix now names a command that runs and passes, so FT-28.03's
  entry criteria can be evidenced rather than asserted.
- `library`, `cli`, `data-science`, `streamlit` and `batch` output is
  byte-pinned across every selection each accepts. Any change that moves
  their rendered bytes fails `tests/test_data_science_composition.py` until
  the digests are regenerated with `--update-goldens` and the diff reviewed.
- `tests/composition_fingerprints.py`'s recorded baseline was regenerated
  once, for the `job.py` fix; any future content change to an existing
  archetype must do the same and the diff must be reviewed, never trusted
  blind.
- `uv run poe archetype` gains the batch endpoint module and its full-
  composition cell.
- `tests/test_generation_provenance.py`'s archetype-parametrised tests now
  cover every catalogue archetype, closing a gap that had silently persisted
  since Streamlit shipped (FT-20.0x never updated it).
- Nothing here publishes. FT-28.03 still owns the `0.7.0` release and the
  package-line tripwires it moves.
