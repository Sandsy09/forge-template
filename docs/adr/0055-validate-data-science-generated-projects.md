# 55. Validate Data Science generated projects

Date: 2026-09-03

## Status

Accepted

## Context

[ADR 0053](0053-production-data-science-archetype.md) shipped the
`data-science` archetype and [ADR 0054](0054-data-science-notebook-and-artefact-layout.md)
completed its generated shape. Both proved the archetype in a single
configuration: `data-science` + `jupyter`, on one interpreter, once
(`tests/test_data_science_build.py`).

[ADR 0048](0048-data-science-compatibility-and-acceptance.md) fixed an
acceptance matrix whose Generated-project and Python-endpoint rows are owned
by FT-12.03 and become first-required here:

- both valid compositions pass `uv run --locked poe check` from committed
  lock state;
- built artefacts carry no ignored `data/`, `models/`, or `artifacts/`
  content;
- repeated renders and manifest-order permutations produce identical output;
- a Data Science project builds, installs, imports, and passes
  `notebook:check` at Python 3.11 and at 3.14, with and without Scientific
  Python.

Running the full aggregate check over the `+ scientific-python` composition,
and over a project targeting the 3.14 language level, for the first time
surfaced two latent defects in already-merged capability content — neither
reachable by any existing test, because no test had run a generated
`poe check` on a Scientific Python selection or at a `py314` target.

## Decision

Add [data-science-validation.md](../data-science-validation.md) as the living
contract and prove it with two new test modules and one recorded fixture.
This is a test-first issue; the two content corrections below are the minimum
needed to make the required compositions pass, folded into their unreleased
`1.0.0` components.

**`tests/test_data_science_composition.py`** (fast) proves both valid
compositions plan and render with selected owners only; that rendering is
invariant to repetition, capability order, catalogue filesystem layout, and
`PYTHONHASHSEED`; that every documented rejection with an archetype in play
fails closed before rendering; that no composition declares a Forge
dependency; that rendered Python content is `ruff format` clean at every
supported floor including `py314`; and that every `library` and `cli` target,
across all four capability selections, matches a recorded SHA-256 in
`tests/fixtures/archetype_regression/digests.json` — regenerated with the
existing `--update-goldens` option.

**`tests/test_data_science_endpoints.py`** (`archetype`-marked, run under
`-n 4`) sweeps both compositions across Python 3.11 and 3.14: lock, sync,
build, isolated install, import, `__version__`, `py.typed`, and the
generated project's own locked `poe check` — which ends in `notebook:check`
over the real starter notebook and a live kernel. The endpoint is the
development interpreter the project locks and runs on; the floor stays
`data-science`'s fixed `>=3.11`. Two further tests plant content in all five
ignored working trees and prove it absent from the wheel and sdist, and prove
the generated project's lock and installed environment name neither Forge
distribution.

`uv run poe archetype` becomes `pytest -m archetype -n 4` so the four sweep
cells land one per worker, matching how `poe combos` already runs. Its
evidence command is unchanged. `tests/conftest.py`'s session-scoped
`_git_identity` fixture gains a retry loop: under `pytest-xdist` every worker
runs it, and on a runner with no configured identity the four
`git config --global` writes race on `~/.gitconfig.lock` — the loop tolerates
the lock failure and returns once any worker's write lands.

**Correction 1 — `scientific-python` `tests/test_scientific_python.py`.**
`pandas` and `sklearn` ship no type information, so the generated project's
`mypy --strict` failed on their imports (`import-untyped`). Each import gains
`# type: ignore[import-untyped]`. This is how the repository's own code
handles an untyped dependency; no stub package is added to the generated
project.

**Correction 2 — `jupyter` `scripts/check_notebooks.py`.** A generated
project with `python.minimum = "3.14"` sets `target-version = "py314"`, and
ruff then reformats `except (OSError, UnicodeError):` to the parenthesis-free
PEP 758 form, which is a syntax error below 3.14 — so the file could not be
clean at every supported floor. The single multi-exception clause is split
into two single-exception clauses, each stable at any target. Behaviour and
the ten failure codes are unchanged; `b"\xff"` still yields
`unreadable-notebook`.

`data-science`, `jupyter`, and `scientific-python` all stay at component
version `1.0.0` — none has shipped in a published wheel, so both corrections
are content fixes within unreleased components, consistent with ADR 0054's
treatment of `data-science`. No engine module, public signature,
`EngineErrorCode` value, ProjectSpec / component-manifest / option-schema /
Foundation-source protocol integer, Foundation file, or existing extension
point changes. `library` and `cli` stay `1.0.1`. The package stays `0.3.2`
and untagged; FT-12.04 publishes the `0.4.0` line.

## Consequences

- The `0.4.0` release gate can be evidenced rather than asserted: every
  Generated-project and Python-endpoint acceptance row now names a command
  that runs and passes on `main`.
- `library` and `cli` output is byte-pinned across all four capability
  selections. Any future change to `library`, `cli`, `jupyter`,
  `scientific-python`, or Foundation that moves their rendered bytes now
  fails `tests/test_data_science_composition.py` until
  `tests/fixtures/archetype_regression/digests.json` is regenerated with
  `--update-goldens` and the diff reviewed — the same workflow as the
  composition-contract goldens.
- `scientific-python` and `jupyter` selections now pass a generated
  `poe check` at every supported Python floor, including `py314`. The two
  corrections are recorded here; the acceptance matrix rows they unblock are
  marked done in the contract.
- `uv run poe archetype` runs its cases in parallel. Wall-clock cost of the
  new sweep is bounded by the slowest single cell rather than their sum. It is
  the first `-n`-parallel suite CI runs, so the `_git_identity` fixture is now
  xdist-safe — closing the last gap in the git-identity bug class CLAUDE.md's
  "Validation" section tracks.
- `tests/test_data_science_build.py` keeps its single-composition 3.13
  baseline; the sweep is additive, not a replacement.
- `scripts/check_wheel.py` needs no change — the two corrected files are
  already inside content trees its prefixes require, and `poe check:wheel`
  confirms it.
- FT-12.04 still owns the `0.4.0` release, its tag, changelog, and PyPI
  publication, and the Copier `combos`/`update` regression gate that runs
  once per published line.
- No `copier.yml` question, `template/` file, Copier answer, public API,
  generated-project runtime dependency, tag, or release changes through this
  decision.
