# 70. Implement the independent Streamlit archetype

Date: 2026-09-19

## Status

Accepted

Amends, without superseding, two statements of the Stage 19 records: the
development-dependency row of [ADR 0068](0068-streamlit-project-shape.md) and
the resolution-only dependency evidence of
[ADR 0069](0069-streamlit-composition-compatibility-and-acceptance.md). Both
remain immutable and otherwise govern.

## Context

[ADR 0068](0068-streamlit-project-shape.md) fixed the `streamlit` archetype's
shape and [ADR 0069](0069-streamlit-composition-compatibility-and-acceptance.md)
fixed its component version, capability matrix, Python window and acceptance
matrix. Both were decisions ahead of any implementation, and two suites
(`tests/test_streamlit_contract.py`, `tests/test_streamlit_gates.py`) were built
to fail the moment the component entered the catalogue.
[FT-20.01](https://github.com/Sandsy09/forge-template/issues/159) is the first
implementation issue: an independent archetype and an immutable, path-free
descriptor, using only reviewed Foundation points, with discovery, ownership,
shape and malformed-selection tests.

[ADR 0053](0053-production-data-science-archetype.md) and
[ADR 0054](0054-data-science-notebook-and-artefact-layout.md) split the
precedent archetype across two issues, and
[FT-20.02](https://github.com/Sandsy09/forge-template/issues/160) owns the
`run` task, configuration safeguards and capability composition here.

Rendering the archetype for the first time and running the generated project's
own `poe check` found a defect in the Stage 19 evidence. Streamlit requires only
`numpy<3`, so at the default floor 3.11 and development interpreter 3.13 the lock
selects NumPy 2.5.3, whose type stubs use PEP 695 `type` statements. Foundation's
`mypy` targets the project's floor, so `mypy` failed with "Type statement is only
supported in Python 3.12 and greater" and a default Streamlit project could not
pass its own quality gate. FT-19.02 had proved the lock *resolves*; it had not run
the generated type check.

## Decision

1. **Ship the DS-precedent half.** Add package-bound component `streamlit`
   `1.0.0`: manifest protocol `2`, ProjectSpec protocol `1`, Python `>=3.11`, no
   options, `requires`, `conflicts`, published extension point or
   `[[regeneration]]`/`[[renames]]` record. It owns the launcher `app.py`, the
   package `__init__.py`, `app.py` and `py.typed`, and `tests/__init__.py` and
   `tests/test_app.py`. It contributes six points: `pyproject-build-system`,
   `-archetype-metadata`, `-build-configuration`, `-runtime-dependencies`,
   `-classifiers` and `-development-dependencies`. FT-20.02 adds `run`,
   `.streamlit/config.toml`, the secrets ignore rule and the README section.
   *Rejected:* shipping the whole component now, which would leave FT-20.02 with
   no content of its own and depart from the precedent; and deferring
   `pyproject-runtime-dependencies` to FT-20.02, which would let an intermediate
   `main` render a project whose `app.py` imports a package it never declares.
2. **Copy, never share.** `__init__.py.jinja`, `py.typed` and `tests/__init__.py`
   are byte-identical to `library`'s; the `archetype-metadata`,
   `build-configuration` and `build-system` extensions are byte-identical to
   `cli`'s. They are copied into the archetype's own tree and the architecture
   review's duplicate-resource groups grow to name it.
3. **The starter page is a greeting.** A title, one sentence and a text input that
   greets the name entered, `Hello, World!` by default, mirroring the CLI
   archetype's `hello`. The launcher is a guarded import of `main`; the page code
   is typed package code. The smoke test locates the launcher from `__file__`,
   builds its `AppTest` with `default_timeout=10`, and asserts the title, the
   default greeting and the greeting after input.
   *Rejected:* a slider, which shares no vocabulary with the CLI starter.
4. **Free text reaches exactly one literal.** The project name is held in a
   `TITLE` constant, escaped for backslash, double quote and line breaks; the test
   compares against `TITLE` rather than repeating the literal. Generated
   docstrings carry no name, so a backslash in a name cannot form an invalid
   escape. *Rejected:* `tojson`, which escapes every non-ASCII character as `\uXXXX` in source and whose
   output `ruff format` rewrites for a name with a double quote; and embedding the
   name in a call, which `ruff format` re-wraps when long. A name containing a
   double quote remains valid Python that `ruff format` may re-quote; the owner
   runs `poe format`. Long names already exceed the line limit in the
   byte-identical shared `__init__.py` docstring of every archetype.
5. **Cap NumPy for development only.** The archetype contributes `"numpy<2.5"`
   through `pyproject-development-dependencies`, which renders into the generated
   `dev` group and never into the wheel metadata, mirroring the
   `numpy>=2.4,<2.5` ceiling `scientific-python` carries. With it the lock selects
   NumPy 2.4.6 and the generated `poe check` passes at Python 3.11, 3.13 and 3.14
   in about 55 seconds, its three `AppTest` cases in about 4 to 5. The contract's
   "unused" row for that point becomes "used", and the statement that strict type
   checking adds no dependency is corrected to "no *runtime* dependency".
   *Rejected:* a second runtime dependency, which contradicts "exactly one
   intrinsic runtime dependency" and ships an application-unused cap to every
   consumer; a `[tool.uv] constraint-dependencies` table, which Foundation already
   owns so a second one is invalid TOML; a Foundation extension point for `mypy`
   overrides, a wider decision touching every archetype that belongs in its own
   issue if it is ever wanted; and raising the Streamlit Python floor, which
   contradicts the accepted window.
6. **Turn the tripwires over, do not delete them.** The Stage 19 "not yet in the
   catalogue" tests now assert the shipped state. `test_streamlit_contract.py`
   compares the live manifest with the contract's extension-point table, less an
   explicit `_DEFERRED_TO_FT_20_02` set that empties there. The gates file reads
   the live catalogue instead of a synthetic descriptor, and the sweep count is
   2880. The v3 "no new archetype" tripwire (FT-ROADMAP-01-EX-03) is turned over
   to four archetypes the way earlier tripwires were, and every catalogue
   enumeration gains `streamlit`.
7. **Re-measure, never guess.** The architecture-review pin becomes 125 files,
   72,784 bytes and 1,338 duplicate-overhead bytes (from 112, 68,954 and 892). The
   built wheel is 113,503 bytes and the sdist 792,271, both inside their ceilings,
   which do not move.
8. **Leave the build evidence to FT-20.03.** The full-composition cell, the
   archetype regression digests, the endpoint sweep and the formal committed-lock
   and artefact audits are FT-20.03's. The prototype run behind decision 5 is
   evidence for this record, not acceptance.

## Consequences

- `discover_components()` returns fifteen components in lexical order, with
  `streamlit` last, on an unreleased line. `forge-template` stays `0.5.0` and
  untagged; FT-20.04 publishes `0.6.0`.
- `library`, `cli` and `data-science` render byte-for-byte unchanged, and the
  sweep grows from 2240 to 2880 compositions (`cli`'s 640).
- The NumPy cap is a ceiling that needs a review when Forge's Python floor moves
  past 3.11 or the type-check target otherwise changes; it is not silent debt.
  The same gap could appear for any future framework whose dependencies ship
  newer-syntax stubs, which is what FT-20.03's executable endpoint check is for.
- `scripts/check_wheel.py` asserts the `streamlit` manifest, content and
  extensions ship and the embedded catalogue list includes it.
- The compatibility-policy table lists the `streamlit` component at `1.0.0`; its
  package row stays `0.5.0` until FT-20.04.
- No engine module, public signature, `EngineErrorCode`, protocol integer,
  Foundation file, existing component, `copier.yml` question, `template/` file,
  Copier answer, generated-project runtime dependency, tag or release changes
  through this decision. Selecting `streamlit` remains possible only through the
  engine; the direct-Copier path stays Library-only.
