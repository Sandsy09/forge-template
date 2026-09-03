# Data Science generated-project validation

This document records what the `data-science` archetype and its supported
capability compositions are proven to do as generated projects, and what that
proof deliberately leaves to the `0.4.0` release. It is the canonical result
of [FT-12.03 / #111](https://github.com/Sandsy09/forge-template/issues/111),
the third child of
[FT-EPIC-12](https://github.com/Sandsy09/forge-template/issues/98), adopted by
[ADR 0055](adr/0055-validate-data-science-generated-projects.md).

FT-12.01 shipped the archetype and FT-12.02 completed its generated shape.
Each proved one configuration — `data-science` + `jupyter`, on one
interpreter. This issue proves the matrix: both valid compositions, both
window-edge interpreters, deterministic composition, the documented
rejections, and a byte-level regression pin on `library` and `cli`. It
changes no engine code, no manifest, and no version.

## What the proof establishes

### Both valid compositions plan and render deterministically

For `data-science` + `jupyter` and `data-science` + `jupyter` +
`scientific-python`:

- planning and rendering succeed, and
  `GenerationPlan.component_order` is the archetype followed by the selected
  capabilities in lexical order — the single order
  [composition-order.md](composition-order.md) fixes;
- every planned file is owned by Foundation or by a selected component;
- `notebooks/getting-started.ipynb` is owned by `data-science`, and each
  capability's owned file appears exactly when that capability is selected;
- the generated `pyproject.toml` is valid TOML and declares no
  `forge-template` or `create-forge` dependency, and no generated module
  imports `forge_template`.

Rendering is byte-identical under repetition, under the capability list given
in the opposite order, under a fresh copy of the catalogue on disk (a
different filesystem iteration order), and under four values of
`PYTHONHASHSEED` in separate processes — the determinism guarantee
[composition-order.md](composition-order.md) names.

Rendered Python content is `ruff format` clean at every supported floor. Python
3.14 sets `target-version = "py314"`, which changes how ruff formats `except`
groups (PEP 758); generated content stays clean at that target.

### The documented rejections fail closed, with an archetype in play

Every rejection the
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md#valid-and-invalid-selections)
lists that involves the `data-science` archetype surfaces as a structured
`ForgeEngineError` before any content renders — `render_project` raises the
same failure as `plan_generation`, with `operation` `parse` or `validate`,
never `render`:

| Rejected selection | `EngineErrorCode` | `operation` |
| --- | --- | --- |
| `data-science` without `jupyter` | `INVALID_COMPONENT_SELECTION` | `validate` |
| `data-science` + `scientific-python`, no `jupyter` | `INVALID_COMPONENT_SELECTION` | `validate` |
| `jupyter` listed twice | `INVALID_PROJECT_SPEC` | `parse` |
| a second archetype given as a capability | `INVALID_COMPONENT_SELECTION` | `validate` |
| an unknown component id alongside `jupyter` | `INVALID_COMPONENT_SELECTION` | `validate` |
| `data-science` given as a capability | `INVALID_COMPONENT_SELECTION` | `validate` |
| options supplied for the optionless `data-science` | `INVALID_COMPONENT_OPTIONS` | `validate` |

The broader capability-only rejection set is proven separately by
[capability-composition-validation.md](capability-composition-validation.md).

### Both compositions pass their own checks at both window edges

`tests/test_data_science_endpoints.py` (`archetype`-marked, run under `-n 4`)
sweeps each composition across Python 3.11 and 3.14. Each cell:

1. renders with the endpoint as the development interpreter and
   `data-science`'s fixed `>=3.11` floor;
2. `uv lock --python <endpoint>`, `uv sync --all-groups --locked`;
3. `uv build`, then installs the wheel into an isolated `uv venv`;
4. imports the package, and checks `__version__` (`0.1.0`),
   `Requires-Python` (`>=3.11`), and the `py.typed` marker;
5. runs the generated project's own `uv run --locked poe check` — `lock:check`,
   `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`, and
   `notebook:check` over the real starter notebook on a live kernel.

Two further tests, at the 3.13 baseline, plant marker content in all five
ignored working trees and prove it absent from both the wheel and the sdist,
and prove the generated lock and installed environment name neither Forge
distribution.

Dependency *resolution* at the 3.11 and 3.14 endpoints is proven separately
and already, by `tests/test_jupyter_capability_build.py` and
`tests/test_scientific_python_capability_build.py`.

### `library` and `cli` output is byte-pinned

`tests/fixtures/archetype_regression/digests.json` records a SHA-256 for every
`library` and `cli` target across all four capability selections (none,
`jupyter`, `scientific-python`, both). `tests/test_data_science_composition.py`
asserts current output against it. Regenerate with
`uv run pytest tests/test_data_science_composition.py --update-goldens` and
review the diff — the same workflow as the composition-contract goldens
([composition-fixtures.md](composition-fixtures.md)). The existing
`tests/test_library_build.py` and `tests/test_cli_build.py` remain the
single-selection build-and-console-script regression for the two archetypes.

## Two corrections this validation forced

Running a generated `poe check` on a Scientific Python selection, and on a
`py314` target, for the first time surfaced two latent defects in
already-merged content:

| File | Defect | Fix |
| --- | --- | --- |
| `scientific-python` `tests/test_scientific_python.py` | `pandas` and `sklearn` ship no type information; `mypy --strict` failed on their imports | `# type: ignore[import-untyped]` on each, the way this repository handles an untyped dependency |
| `jupyter` `scripts/check_notebooks.py` | at `target-version = "py314"` ruff rewrites `except (OSError, UnicodeError):` to the PEP 758 form, a syntax error below 3.14 | split into two single-exception `except` clauses, stable at any target — behaviour and the ten failure codes unchanged |

Both components stay at `1.0.0`: neither has shipped in a published wheel, so
these are content fixes within unreleased components, consistent with
[ADR 0054](adr/0054-data-science-notebook-and-artefact-layout.md).

## What this proof deliberately leaves open

- **The `0.4.0` release.** Merging is not releasing. The package stays
  `0.3.2` and untagged; FT-12.04 / #112 bumps the version, runs
  `release.yml`, and publishes the wheel and sdist to PyPI.
- **The Copier regression gate.** `uv run poe combos` and `uv run poe update`
  are release gates run once per published line, not per child — no Stage 11
  or 12 change touches `template/` or `copier.yml`
  ([compatibility and acceptance](data-science-compatibility-and-acceptance.md#regression-checks)).
- **create-forge.** Client option and capability selection, `--engine-preview`
  delivery, and the end-to-end console-script proof are create-forge Stages
  13 and 14.
- **A wider Python window.** Admitting a new CPython release or moving the
  floor is owned by [python-support.md](python-support.md).
