# Streamlit generated-project validation

This document records what the `streamlit` archetype and its accepted
capability selections are proven to do as generated projects and as
distributions. It is the canonical result of
[FT-20.03](https://github.com/Sandsy09/forge-template/issues/161), the third
implementation child of
[FT-EPIC-20](https://github.com/Sandsy09/forge-template/issues/145), adopted by
[ADR 0072](adr/0072-validate-streamlit-generated-projects.md). Its review
obligations are **FT-ROADMAP-02-AC-04** (the deterministic-render half, shared
with FT-19.02 and FT-20.02), **FT-ROADMAP-02-AC-05**, **FT-ROADMAP-02-AC-06**
and **FT-ROADMAP-02-AC-07**.

FT-20.01 built the archetype and FT-20.02 completed it; each proved its part by
construction. This issue proves the matrix that [the compatibility and
acceptance contract](streamlit-compatibility-and-acceptance.md) fixes: all four
capability selections, both window-edge interpreters, restoration from a
committed lock, the bounded non-serving smoke, module-only artefacts, Forge-free
installs, a byte-level regression pin on the other archetypes, and wheel and
sdist audits. It changes no engine code, no manifest, no version and, as it
turned out, no content of the archetype.

## What the proof establishes

### Every selection passes at both window edges

`tests/test_streamlit_endpoints.py` (`archetype`-marked, run under `-n 4`)
sweeps the four accepted selections — no capability, `jupyter`,
`scientific-python` and both — across Python 3.11 and 3.14. Each of the eight
cells:

1. renders with the endpoint as the development interpreter and the archetype's
   fixed `>=3.11` floor, then runs `uv lock --python <endpoint>`;
2. **restores from the committed lock**: a clean copy with no virtual
   environment runs `uv sync --all-groups --locked`, and a second copy whose
   dependency declaration was edited without re-locking is refused;
3. runs the restored project's own `uv run --locked poe check` (`lock:check`,
   `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`, and
   `notebook:check` when `jupyter` is selected) inside the 600-second project
   bound and the listen guard below;
4. builds a wheel and an sdist, installs the wheel into an isolated environment
   on the endpoint interpreter, imports `<package>` and `<package>.app`, and
   checks `__version__` (`0.1.0`), `Requires-Python` (`>=3.11`), the `py.typed`
   marker and that `main` is callable; and
5. checks that the lock names neither `forge-template` nor `create-forge`, and
   that the installed environment cannot import `forge_template`.

The smoke test the check runs is the archetype's own three `AppTest` cases, each
built with the 10-second `default_timeout`; a slower run raises rather than
passing.

### Nothing serves, and a timeout is a failure

The bounds and the no-server rule are enforced by `tests/streamlit_harness.py`,
not trusted:

- **A bound is a failure and never retried.** Each command runs exactly once
  under a `subprocess` timeout and raises when it expires. A fast test proves
  the command ran once and the run failed, and another pins the 10 and 600
  second bounds and the two endpoints against the contract's constants table.
- **A listen guard makes a server impossible to miss.** Each cell's `poe check`
  runs with a temporary `sitecustomize.py` on `PYTHONPATH` that makes
  `socket.socket.listen` raise, so any server started anywhere in the check
  fails the cell. Fast tests prove the guard trips on a plain `listen` and on an
  asyncio server. It allows one caller: CPython's `socket.py` socketpair
  fallback (named `socketpair` up to 3.11 and `_fallback_socketpair` from 3.12),
  which builds Windows' asyncio self-pipe with a loopback `listen` that closes
  immediately.
- The rendered aggregate `check` never lists `run` for any selection.

### Built artefacts carry the module only

A planted `.streamlit/secrets.toml` is built into a wheel and an sdist. The
wheel holds `demo_app/{__init__,app}.py`, `py.typed` and its `dist-info` only;
the sdist holds the same module under `src/` plus `pyproject.toml`, `README.md`,
`LICENSE` and their metadata. Neither contains the marker, `.streamlit/`, the
root `app.py` or `tests/`. That the launcher and configuration are source-tree
files is the contract's deliberate consequence, now enforced.

### Rendering is deterministic and clean at every floor

FT-20.02's composition module already proves byte-identical output under
repetition, capability reordering and a rearranged catalogue, and the nine
documented rejections failing closed before rendering. FT-20.03 adds the two
obligations that remained: identical output under four `PYTHONHASHSEED` values
in separate processes, and `ruff format` and `ruff check` clean for every
selection at Python floors 3.11 and 3.14 (3.14 flips `target-version` and the
formatting of `except` groups).

### Every archetype is byte-pinned

`tests/fixtures/archetype_regression/digests.json` records a SHA-256 for every
target of every recorded archetype: `library` and `cli` (four selections each,
from FT-12.03), `data-science` (its two valid selections) and `streamlit`
(four), added here.
`tests/test_data_science_composition.py::test_recorded_archetype_output_matches_digests`
asserts current output against it. Regenerate with `uv run pytest
tests/test_data_science_composition.py --update-goldens` and review the diff
([composition-fixtures.md](composition-fixtures.md)). This change added six
entries and left the eight existing ones byte-identical.

### The distributions are audited from the source tree

`scripts/check_wheel.py` keeps its hand-kept list of required paths, and now
also requires every file on disk under the Foundation and component trees —
hidden ones such as `.streamlit/config.toml` included — to be in both the wheel
and the sdist. Its isolated-install smoke renders a Streamlit project from the
installed artefact and checks the launcher, the hidden configuration, the `run`
task and the secrets ignore rule, so an artefact is shown to *render* the
archetype, not merely contain it.

### A full composition builds and is pre-commit clean

`tests/test_full_composition_build.py` gained its fourth cell: `streamlit` with
the `github` platform and every capability it can carry (`changelog`,
`coverage`, `dependabot`, `dotenv-example`, `jupyter`, `pre-commit`, `pyright`
and `scientific-python`). It locks, syncs, builds, installs, runs the aggregate
`check` with the coverage gate at 80 percent and `pyright`, then a real `git
init` and `pre-commit run --all-files`, and the Forge-freedom probe. None of
coverage, `pyright` or pre-commit had run against Streamlit output before.

## What the validation found

No defect in the archetype: every cell passed against the shipped component, so
the component stays `1.0.0` and no file it owns changed. The only finding was in
the harness itself: a blanket `listen` guard is unusable on Windows because
asyncio's proactor loop needs one, and the helper that makes it is named
differently at Python 3.11 and 3.12. The guard therefore allows that one caller,
and its own tests fail before a cell would.

Earlier stages found defects the same way, which is why the checks are real
rather than derived: two in Data Science
([data-science-validation.md](data-science-validation.md#two-corrections-this-validation-forced))
and the NumPy stub incompatibility in the Streamlit archetype ([ADR
0070](adr/0070-streamlit-archetype-implementation.md)).

## Evidence

Local results, on Windows with `uv` 0.12:

| Check | Result |
| --- | --- |
| `uv run poe check` | 852 passed, 2 skipped (the pre-existing symlink skips) |
| `uv run poe archetype` | 57 passed in 19 min 49 s (47 before, plus the nine endpoint tests and the `streamlit` full-composition cell) |
| `tests/test_streamlit_endpoints.py`, `-n 4` | 9 passed in 8 min 21 s (eight endpoint cells and the artefact audit) |
| `tests/test_full_composition_build.py -k streamlit` | 1 passed in 9 min 27 s |
| `uv run poe check:wheel` | wheel 115,215 B (ceiling 131,072), unchanged; every engine resource on disk shipped in both artefacts |
| `uv run poe crossrepo` | 20 passed against a sibling `create-forge` checkout |
| Mutation test of the new pins | 12 / 12 mutations caught by the intended tests |

`uv run poe sweep` was not re-run: the catalogue, the composition count and
every piece of component content are unchanged from FT-20.02, whose 5761-case
sweep passed. The mutations were a 601-second project bound, an 11-second smoke
bound, a dropped endpoint, a retried timeout, a guard that allows every
`listen`, a guard that trusts any `socket.py` caller, a changed `streamlit`
byte, a changed recorded digest, a changed `data-science` byte, a file the wheel
drops, a changed `run` task in the installed wheel, and a source-tree file
leaking into the sdist. The guard mutation that trusts any `socket.py` caller
was first missed and led to the `socket.create_server` test.

The pull request records the protected CI run against the exact commit.

## Downstream and later work

- **FT-20.04** published `forge-template` `0.6.0` after every Engine,
  Generated-project, Python-endpoint and Regression row of the acceptance
  matrix passed, and moved the package-line tripwires this issue left alone; see
  [streamlit-provider-release.md](streamlit-provider-release.md).
- **create-forge Stage 21** adopts the `0.6` line and validates Streamlit
  through the installed console; the client checks are not this repository's.
