# Batch generated-project validation

This document records what the `batch` archetype and its accepted capability
selections are proven to do as generated projects and as distributions. It is
the canonical result of
[FT-28.02](https://github.com/Sandsy09/forge-template/issues/202), the second
implementation child of
[FT-EPIC-28](https://github.com/Sandsy09/forge-template/issues/190), adopted
by [ADR 0083](adr/0083-validate-batch-generated-projects.md).

FT-28.01 built the archetype and proved it by construction. This issue proves
the matrix that [the compatibility and acceptance
contract](batch-compatibility-and-acceptance.md) fixes: all four capability
selections, both window-edge interpreters, restoration from a committed lock,
the bounded deterministic smoke, module-only artefacts, Forge-free installs, a
byte-level regression pin on the other archetypes, and provenance/update
evidence. It changes one file the archetype owns — a real defect the first
real check found — and no engine code, manifest, version or protocol.

## What the proof establishes

### Every selection passes at both window edges

`tests/test_batch_endpoints.py` (`archetype`-marked) sweeps the four accepted
selections — no capability, `jupyter`, `scientific-python` and both — across
Python 3.11 and 3.14. Each of the eight cells:

1. renders with the endpoint as the development interpreter and the
   archetype's fixed `>=3.11` floor, then runs `uv lock --python <endpoint>`;
2. **restores from the committed lock**: a clean copy with no virtual
   environment runs `uv sync --all-groups --locked`, and a second copy whose
   dependency declaration was edited (a new dependency is prepended to the
   project's list, since batch itself declares none) without re-locking is
   refused;
3. runs the restored project's own `uv run --locked poe check` (`lock:check`,
   `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`, and
   `notebook:check` when `jupyter` is selected) inside the 600-second project
   bound;
4. runs the job via both entry points — the console script and `python -m
   <package_name>` — and checks the transformed output against the
   deterministic fixture, that a rerun is byte-for-byte idempotent, and that
   a malformed record exits `1`, logs the failure and writes no output;
5. builds a wheel and an sdist, installs the wheel into an isolated
   environment on the endpoint interpreter, imports `<package>` and
   `<package>.job`, and checks `__version__` (`0.1.0`), `Requires-Python`
   (`>=3.11`) and the `py.typed` marker; and
6. checks that the lock names neither `forge-template` nor `create-forge`,
   and that the installed environment cannot import `forge_template`.

### Nothing serves, and a timeout is a failure

Batch has no server to guard against — it is a plain script, not a web
framework — so the one property `tests/batch_harness.py` enforces is the
bound: **a bound is a failure and never retried.** Each command runs exactly
once under a `subprocess` timeout and raises when it expires. A fast test
proves the command ran once and the run failed, and another pins the 5 and
600 second bounds and the two endpoints against the contract's constants
table. The rendered aggregate `check` never lists `run` for any selection.

### Built artefacts carry the module only

A planted `data/secret.json` is built into a wheel and an sdist. The wheel
holds `demo_job/{__init__,__main__,job}.py`, `py.typed` and its `dist-info`
only; the sdist holds the same module under `src/` plus `pyproject.toml`,
`README.md`, `LICENSE` and their metadata. Neither contains the marker,
`data/` or `tests/`. That the sample input is a source-tree file is the
contract's deliberate consequence, now enforced.

### Every archetype is byte-pinned

`tests/fixtures/archetype_regression/digests.json` records a SHA-256 for
every target of every recorded archetype: `library` and `cli` (four
selections each, from FT-12.03), `data-science` (its two valid selections),
`streamlit` (four, from FT-20.03) and `batch` (four, added here).
`tests/test_data_science_composition.py::test_recorded_archetype_output_matches_digests`
asserts current output against it. Regenerate with `uv run pytest
tests/test_data_science_composition.py --update-goldens` and review the diff
([composition-fixtures.md](composition-fixtures.md)). This change added four
entries and left the fourteen existing ones byte-identical, once the one real
defect below was fixed.

### Provenance, reproduction and update evidence cover every archetype

`tests/test_generation_provenance.py`'s reproduction-guarantee test had only
ever been parametrised over `library`, `cli` and `data-science` — Streamlit
never extended it. This issue adds `streamlit` and `batch`, so render ->
attach metadata -> re-render from the embedded spec -> byte-identical now
holds for every catalogue archetype, not three of five. A new test proves
ADR 0081 choice 2 directly: `data/output.json` never appears as a rendered
target and never appears as a `plan_update` classification for a
batch-containing project — it is the job's own runtime output, written by an
atomic overwrite at a layer `plan_update` never reaches.

### A full composition builds and is pre-commit clean

`tests/test_full_composition_build.py` gained its fifth cell: `batch` with
the `github` platform and every capability it can carry (`changelog`,
`coverage`, `dependabot`, `dotenv-example`, `jupyter`, `pre-commit`, `pyright`
and `scientific-python`). It locks, syncs, builds, installs, runs the
aggregate `check` with the coverage gate at 80 percent and `pyright`, then a
real `git init` and `pre-commit run --all-files`, and the Forge-freedom
probe.

### The distributions are audited from the source tree

`scripts/check_wheel.py` already required every file on disk under the
Foundation and component trees (FT-20.03) and already rendered a `batch`
project from the installed artefact, checking the job module, the console
script and the output ignore rule (FT-28.01). No further change to the
auditor was needed.

## What the validation found

One real defect, in the archetype's own content, not in the engine: `job.py`'s
atomic-overwrite helper used `os.replace(tmp_path, path)`. forge-template's
own `poe check` never saw this because the file ships as `.py.jinja`, not
`.py` — ruff does not lint template sources. The first real `uv run --locked
poe check` against a *rendered* batch project failed ruff's `PTH105`
(`os.replace()` should be `Path.replace()`). Fixed to `tmp_path.replace(path)`,
which calls the same platform `os.replace` under the hood, so ADR 0080
choice 7's atomic-rename guarantee is unchanged; the now-unused `import os`
was removed. The regression digests and the full composition sweep's
fingerprint baseline were regenerated to reflect the corrected bytes.

No other file the archetype owns changed, and no engine module, public
signature, `EngineErrorCode` value, protocol integer, Foundation file or
sibling component changed. `batch` stays at component `1.0.0`, and the
package stays `0.6.0` and untagged.

Earlier stages found defects the same way, which is why the checks are real
rather than derived: two in Data Science
([data-science-validation.md](data-science-validation.md#two-corrections-this-validation-forced)),
the NumPy stub incompatibility in the Streamlit archetype ([ADR
0070](adr/0070-streamlit-archetype-implementation.md)), and the harness's
socketpair detail at Streamlit's own validation
([streamlit-validation.md](streamlit-validation.md#what-the-validation-found)).

## Evidence

Local results, on Windows with `uv` 0.12, at the pull request's branch:

| Check | Result |
| --- | --- |
| `uv run poe check` | 1,178 passed, 2 skipped (8m11s) |
| `uv run poe check:wheel` | ok: wheel 128,916 bytes (ceiling 131,072), sdist 1,190,144 bytes |
| `tests/test_batch_endpoints.py` and `tests/test_batch_harness.py`, `-n 2` | 14 passed (5m53s) |
| `tests/test_full_composition_build.py -k batch` | 1 passed (4m38s) |

The exhaustive sweep was **not** run locally: a full local run is long and
memory-heavy on a development laptop, and CI runs it on every change to
component content. Its evidence is the protected run below.

Protected CI,
[run 37445444559](https://github.com/Sandsy09/forge-template/actions/runs/37445444559)
against commit `7293ccf` (the implementation commit; the evidence commit
after it is docs-only), all checks passing on Linux (`ubuntu-24.04`), with the
Windows smoke also passing:

| Job | Result |
| --- | --- |
| Composition sweep, direct engine | 3,520 of 3,520 executed, 3m34s (203 s in the sweep step) |
| Composition sweep, independent client | 3,520 of 3,520 executed, 7m13s (422 s in the sweep step) |
| Archetype builds | 4m27s |
| Windows smoke | 1m40s |
| Validation budget | `ok`; critical path 9.7 min against a 20-minute fail line |

The same run on the `ubuntu-26.04` canary also passed.

No case failed and none was excluded.

### Budget re-measurement

The sweep steps measured about 0.058 s per composition (direct) and 0.120 s
(independent) over 3,520 compositions, against the recorded 0.104 s and
0.215 s in `.github/validation-budgets.toml`. This is one run on one runner
type, so the recorded figures are left unchanged: they remain conservative,
the growth guard passes, and a single sample is not grounds to loosen it. A
later re-measurement over several runs may lower them.

## Downstream and later work

- **FT-28.03** published `forge-template` `0.7.0` once every Engine,
  Generated-project, Python-endpoint and Regression row of the acceptance
  matrix had passed, and moved the package-line tripwires this issue left
  alone; see [batch-provider-release.md](batch-provider-release.md).
- **`create-forge` Stage 29 / CF-29.01** adopts the `0.7` line and validates
  batch through the installed console; the client checks are not this
  repository's.
