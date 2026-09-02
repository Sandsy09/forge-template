# 54. Ship the Data Science notebook and artefact layout

Date: 2026-09-03

## Status

Accepted

## Context

[ADR 0053](0053-production-data-science-archetype.md) shipped the
`data-science` archetype at component version `1.0.0` — the manifest, the
owned `src/` package and smoke tests, and the four archetype-neutral
`pyproject.toml` contributions — and explicitly left the starter notebook, the
ignored working trees, and the `readme-project-shape` and
`gitignore-project-shape` contributions to FT-12.02.

Three accepted contracts already fix what that means.
[ADR 0045](0045-data-science-project-shape.md) reserves
`notebooks/getting-started.ipynb`, names the five working trees
(`data/raw/`, `data/interim/`, `data/processed/`, `models/`, `artifacts/`),
and forbids any tracked `.gitkeep` or per-directory placeholder.
[ADR 0047](0047-notebook-data-and-model-safeguards.md) fixes the five ignore
entries as root-anchored, reads "guidance markers remain tracked" as prose and
rules only, and requires the starter notebook to be tracked, output-free,
network-free, and limited to the generated package plus modules that ship with
Python. [ADR 0048](0048-data-science-compatibility-and-acceptance.md) makes
three generated-project acceptance rows first-required at this issue.

One acceptance row named `uv run pre-commit run --all-files` *in the generated
project* as its evidence command. The engine path generates no
`.pre-commit-config.yaml` — the
[composition architecture review](../composition-architecture-review.md)
removed it ("Removed until a selected capability owns hook configuration") —
so that command cannot run there. The row needs correcting, not a workaround.

## Decision

Add three files to the `data-science` component and append two contributions
to its manifest. The component version stays `1.0.0`: it has never shipped in
a published wheel, so this content is additive within an unreleased component,
not a change to a released one.

**The starter notebook** is `content/notebooks/getting-started.ipynb.jinja`,
rendered to `notebooks/getting-started.ipynb`. It is nbformat 4.5, every code
cell output-free with a null execution count and no stored widget state. Two
markdown cells explain the clear-output rule and document the five working
trees; one code cell imports the generated package and prints `__version__`;
one code cell runs a `statistics` computation over five literal float
values. It reads no file and writes none — `notebook:check` executes
notebooks in the real project directory with the developer's full ambient
identity, and Foundation CI runs that check, so a side-effect-free notebook is
the only safe default.

**The `gitignore-project-shape` contribution** carries the five ignore
entries, root-anchored (`/data/raw/` … `/artifacts/`) and in the order the
safeguards contract states. Root-anchoring is normative: an unanchored
`models/` rule would silently untrack `src/<package>/models/`.

**The `readme-project-shape` contribution** adds a `## Project structure`
block (package, tests, `notebooks/`) and a `## Working directories` block
naming each tree, what it holds, that Git ignores its contents, that nothing
creates it, and that no dataset, trained model, or credential is committed.
This prose *is* the tracked guidance the safeguards contract requires; no
`.gitkeep` or per-directory `README.md` is introduced.

The [compatibility and acceptance contract](../data-science-compatibility-and-acceptance.md)
is corrected: the no-secret acceptance row is repointed from the
generated-project pre-commit command to evidence that exists — this
repository's own `detect-private-key` and `check-added-large-files` hooks over
the authored fragment sources, plus
`tests/test_data_science_notebook.py::test_notebook_and_fragments_carry_no_payload`.
No `.pre-commit-config.yaml` is generated.

No engine module, public signature, `EngineErrorCode` value, ProjectSpec /
component-manifest / option-schema / Foundation-source protocol integer, or
Foundation file changes. `library` and `cli` stay `1.0.1`; `jupyter` and
`scientific-python` stay `1.0.0`; `data-science` stays `1.0.0`. The package
stays `0.3.2` and untagged; FT-12.04 publishes the `0.4.0` line.

## Consequences

- A Data Science project renders with a clean starter notebook that passes
  the generated project's own `ruff check`, `ruff format --check`, and
  `notebook:check` (now over a real notebook and a real kernel, no longer an
  empty set) from committed lock state.
- The five working-tree ignore entries land root-anchored and in order, ahead
  of the `jupyter`-owned `.ipynb_checkpoints/` entry, shadowing no tracked
  path. A clean checkout still does not contain `data/`, `models/`, or
  `artifacts/` until a user or selected component creates them.
- `library` and `cli` render byte-for-byte as before: the two new
  contributions reach only a selection that includes `data-science`.
- The acceptance matrix's no-secret row now names a command that runs where
  it is pointed. The correction is recorded here and in the contract; the
  safeguard itself is unchanged.
- `scripts/check_wheel.py` needs no change — its existing
  `components/data-science/content/` and `.../extensions/` prefixes already
  require the new files in the built wheel, and `poe check:wheel` confirms it.
- FT-12.03 still owns the full capability-composition and archetype-regression
  matrix and the Python-endpoint sweep; FT-12.04 still owns the `0.4.0`
  release, its tag, and PyPI publication.
- No `copier.yml` question, `template/` file, Copier answer, public API,
  generated-project runtime dependency, tag, or release changes through this
  decision.
