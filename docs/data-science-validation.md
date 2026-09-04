# Data Science generated-project validation

This document records what the `data-science` archetype and its supported
capability compositions are proven to do as generated projects, together with
the published `0.4.0` release evidence. It is the canonical result
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

Both components stayed at `1.0.0`: the corrections landed before their first
published wheel, so they were fixes to unreleased component content,
consistent with
[ADR 0054](adr/0054-data-science-notebook-and-artefact-layout.md). They now
ship unchanged in `forge-template 0.4.0`.

## Published 0.4.0 release verification

FT-12.04 prepared the release in
[PR #128](https://github.com/Sandsy09/forge-template/pull/128), merged as
commit `91f1cc5606778379a10b1b7591c9d924e0ba6218`. The protected
[`main` run](https://github.com/Sandsy09/forge-template/actions/runs/33736737699)
passed the aggregate gate, all four Copier combinations, update compatibility,
archetype builds, Windows smoke, and wheel-content validation. The
[`release.yml` dry run](https://github.com/Sandsy09/forge-template/actions/runs/33737131150)
derived `v0.4.0`, displayed the complete squash-commit release notes since
`v0.3.2`, and created no tag, GitHub Release, or PyPI file.

The real
[`release.yml` run](https://github.com/Sandsy09/forge-template/actions/runs/33737307302)
created the annotated
[`v0.4.0` tag and GitHub Release](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0)
at that same commit and published exactly one wheel and one source distribution
to [PyPI](https://pypi.org/project/forge-template/0.4.0/):

| Artefact | SHA-256 |
| --- | --- |
| `forge_template-0.4.0-py3-none-any.whl` | `ea731259f65c553c09b7b9fd33eb23c0cc4ea297359b34b11b713fcdaaeb6d5f` |
| `forge_template-0.4.0.tar.gz` | `07b3df2c1845646de16971df11af3016acec4915971e47a2e746e7db95bc726e` |

The downloaded hashes match PyPI metadata. Wheel `METADATA` and sdist
`PKG-INFO` both report `0.4.0`. An isolated install reports ProjectSpec
protocol `(1,)`, manifest protocols `(1, 2)`, and lexical discovery order
`cli`, `data-science`, `jupyter`, `library`, `scientific-python`, with the
accepted component versions and `data-science` → `jupyter>=1,<2` requirement.
The wheel contains Foundation, all five manifests and their owned resources,
and `py.typed`; repository-only checking modules remain excluded.

Both accepted Data Science compositions were rendered from the downloaded
wheel into temporary projects. Each resolved a lock, restored with
`uv sync --all-groups --locked`, passed `uv run --locked poe check`, built a
wheel and sdist, and installed in isolation. Their generated runtime metadata
and lock state contain neither Forge package.

Stage 14 reviewed this line and republished it unchanged as `forge-template`
`0.4.1` — see
[reviewed-engine-release.md](reviewed-engine-release.md#published-artefact-audit)
for that audit, including the byte-identical catalogue diff against this
`0.4.0` wheel.

## What remains open

- **create-forge.** Client option and capability selection, `--engine-preview`
  delivery, and the end-to-end console-script proof are create-forge Stages
  13 and 14.
- **A wider Python window.** Admitting a new CPython release or moving the
  floor is owned by [python-support.md](python-support.md).
