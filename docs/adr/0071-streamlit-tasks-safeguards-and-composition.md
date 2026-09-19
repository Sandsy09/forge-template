# 71. Complete the Streamlit archetype: run task, safeguards and composition

Date: 2026-09-19

## Status

Accepted

Completes the implementation begun by
[ADR 0070](0070-streamlit-archetype-implementation.md) and fixed in shape by
[ADR 0068](0068-streamlit-project-shape.md) and
[ADR 0069](0069-streamlit-composition-compatibility-and-acceptance.md). It
amends none of them.

## Context

[ADR 0070](0070-streamlit-archetype-implementation.md) followed the Data Science
precedent ([ADR 0053](0053-production-data-science-archetype.md) /
[ADR 0054](0054-data-science-notebook-and-artefact-layout.md)) and shipped the
`streamlit` archetype's first half: the package, the root launcher, the in-process
smoke test and six Foundation contributions. It left three contributions and one
path to
[FT-20.02](https://github.com/Sandsy09/forge-template/issues/160), and made
`tests/test_streamlit_contract.py` fail on purpose until they landed: the `run`
task, `.streamlit/config.toml`, the `/.streamlit/secrets.toml` ignore rule and the
README section.

Every one of those was already decided. The archetype contract fixes the `run`
task, its exclusion from `check`, the two-line configuration and the ignore rule;
the compatibility contract fixes the four valid selections, the rejections, the
deterministic-validation requirements and which acceptance rows FT-20.02 owns.
What remained was to implement them, prove the composition with executable
evidence, and record the small choices the contracts left open.

## Decision

1. **Complete the archetype inside `1.0.0`.** The component gains three
   contributions and one file, reaching the contract's seven owned paths and nine
   points, and stays at version `1.0.0`. `data-science` did the same across
   FT-12.01 and FT-12.02, and the component has never been published, so no
   consumer ever held a `1.0.0` without these. The package stays `0.5.0` and
   untagged; FT-20.04 publishes `0.6.0`. *Rejected:* bumping to `1.1.0`, which
   would record additive content against a version nobody has seen, for a
   component that has never been released.
2. **`run` is a task and never part of `check`.** The archetype contributes
   `run = "streamlit run app.py"` through `pyproject-task-definitions`, composed
   ahead of `jupyter`'s tasks, and contributes nothing to
   `pyproject-aggregate-check`. `check` keeps Foundation's five steps, plus
   `notebook:check` exactly when `jupyter` is selected. A server inside `check`
   would hang every generated project's gate and CI. *Rejected:* a headless flag or
   a bounded server in `check`, which adds a network dependency to a terminating
   gate the in-process `AppTest` smoke already covers without one; and a second
   `smoke` task, which duplicates `test`.
3. **One non-templated configuration file.** `content/.streamlit/config.toml` has
   no `.jinja` suffix, because it holds no variable, and carries exactly
   `[browser] gatherUsageStats = false`, so a generated project never reports
   usage statistics without its owner choosing to. No other setting is
   preselected. *Rejected:* also fixing `server.headless` or a theme, which are the
   owner's choices and would make the file a second source of truth for behaviour
   Streamlit already defaults sensibly.
4. **Ignore the secrets file, not its directory.** The archetype contributes the
   root-anchored `/.streamlit/secrets.toml` through `gitignore-project-shape`,
   composed ahead of `jupyter`'s `.ipynb_checkpoints/`. Naming the file keeps
   `.streamlit/config.toml` trackable beside it, and Foundation's rules contain no
   pattern the entry could duplicate or shadow. *Rejected:* ignoring `.streamlit/`,
   which would hide the tracked configuration; and an unanchored `secrets.toml`,
   which would shadow any file of that name in the tree.
5. **Guidance, but no example secrets file.** The README section carries four
   short blocks: how to run (`uv run poe run`, which is `streamlit run app.py`),
   the project structure including `.streamlit/config.toml`, one line that
   `pages/` adds views, and one line that `.streamlit/secrets.toml` is ignored and
   never committed. It generates no `secrets.toml.example` and names `.env` as the
   only secret channel, so the placeholder-only rule has one enforced target.
   *Rejected:* a tracked example secrets file, which invites putting values in
   Streamlit's file; and a bare structure tree, which would omit the run command
   and `pages/` that the contract requires the README to document.
6. **Discharge the one slow row here, resolution only.** The compatibility matrix
   gives FT-20.02 the row "`streamlit>=1.63,<2`, alone and with the Jupyter and
   Scientific Python lines, resolves at Python 3.11 and 3.14". The new
   `archetype`-marked `tests/test_streamlit_resolution.py` runs a real `uv lock`
   for the four selections at both endpoints, and asserts that Streamlit locks
   inside its declared line, that no NumPy at or above `2.5` is locked (the
   development cap of ADR 0070), and that the lock passes `uv lock --check`.
   Build, isolated install, committed-lock restoration and the generated
   `poe check` remain FT-20.03's. *Rejected:* deferring the row, which leaves an
   owner-assigned criterion without evidence; and running the full sweep here,
   which duplicates FT-20.03.
7. **Prove composition with a fast suite, not a fixture.**
   `tests/test_streamlit_composition.py` covers the four selections, composition
   order, determinism under repetition, capability reordering and a rearranged
   catalogue layout, the nine documented rejections, the secret and non-serving
   safeguards, and the absence of any deployment, container, authentication,
   database, FastAPI or Forge dependency. It asserts against the live engine, and
   the deferred set in `test_streamlit_contract.py` is deleted so the equality
   covers the contract's whole extension-point table.
8. **Re-measure the pin from LF.** The architecture-review pin becomes 129 files
   and 74,226 bytes, measured from the LF blobs `.gitattributes` commits, with the
   duplicate overhead unchanged at 1,338 bytes because no new file is a copy. No
   wheel path list moves, as `scripts/check_wheel.py` names the component's
   `content/` and `extensions/` directories.

## Consequences

- The `streamlit` archetype is complete at component `1.0.0`: seven owned paths,
  nine contributions, no option, `requires` or `conflicts`, and no published
  extension point. `discover_components()` still returns fifteen components, and
  the sweep count stays 2880 because contributions, not selections, were added.
- `library`, `cli` and `data-science` render byte-for-byte unchanged, and no engine
  module, public signature, `EngineErrorCode`, protocol integer or Foundation
  file moved.
- A generated Streamlit project has a `poe run` task and a `.streamlit/config.toml`
  that switches usage reporting off, and `.streamlit/secrets.toml` is ignored
  without hiding the configuration.
- `poe archetype` gains eight lock-only cells. They need the network and take a
  few minutes on a cold cache; they never build or serve anything.
- FT-20.03 inherits only the executable harness: the committed-lock, artefact and
  endpoint audits, the full-composition build cell, the regression digests and the
  sweep. Publication remains FT-20.04's.
