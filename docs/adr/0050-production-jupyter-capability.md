# 50. Ship Jupyter as a production capability

Date: 2026-09-02

## Status

Accepted

## Context

[ADR 0046](0046-initial-data-science-capabilities.md) defines `jupyter` as
an optionless, reusable capability that owns notebook authoring, execution,
validation, development dependencies, tasks, and guidance. [ADR
0047](0047-notebook-data-and-model-safeguards.md) fixes the validator's
fail-closed order, temporary-copy execution, safe diagnostics, and ten stable
failure codes. [ADR
0049](0049-foundation-capability-tooling-extension-points.md) publishes the
three remaining Foundation extension points required to implement it.

The production engine catalogue still needs a concrete component that applies
those contracts without adding notebooks or runtime dependencies to Library,
CLI Application, or Foundation. The validator must be useful to any selected
archetype, harmless when no notebooks exist, and safe to run through the
generated project's aggregate quality command.

## Decision

Add package-bound component `jupyter` version `1.0.0`, using component
manifest protocol `2`, ProjectSpec protocol `1`, and Python compatibility
`>=3.11`. It has no options schema, requirements, conflicts, runtime
dependencies, or notebook content. It is independently selectable with every
current archetype.

The capability contributes its four bounded development dependencies,
`notebook = "jupyter lab"`,
`"notebook:check" = "python scripts/check_notebooks.py"`, an aggregate
`"notebook:check"` entry, root README guidance, and the unanchored
`.ipynb_checkpoints/` ignore through the published Foundation extension
points. The executable validator is literal component-owned content at
`scripts/check_notebooks.py`; no generated runtime package or engine API is
added.

The generated command supports no flags, exclusions, fix mode, or verbose
mode. It discovers notebooks deterministically while pruning repository,
environment, checkpoint, and accepted Data Science working-tree paths. It
first decodes, parses, validates, and inspects every notebook, aggregating all
structural failures before any execution. When structural validation passes,
it copies source bytes into one temporary directory outside the project and
executes copies sequentially with nbclient's `python3` kernel, errors disabled,
a 300-second per-cell timeout, and the tracked notebook directory as execution
context. It stops after the first execution failure and always attempts
cleanup. An empty notebook set creates neither a kernel nor a temporary
directory.

Diagnostics are deterministic stderr text only. They contain a
project-relative POSIX path, an optional zero-based cell index, one of the ten
codes fixed by ADR 0047, and that code's fixed message. Control characters in
paths and exception type names are escaped. Cell contents, exception messages,
tracebacks, environment data, and absolute paths are never emitted. Executed
notebooks are never persisted and tracked notebook bytes are never modified.

The repository test dependency group includes the imports needed to exercise
the generated validator. Those dependencies are development dependencies of
`forge-template`, not runtime dependencies of the engine package. The
generated project receives the same packages only when `jupyter` is selected.

The package remains version `0.3.2`; this unreleased catalogue addition is
published later on the `0.4.0` line by FT-12.04. ProjectSpec, component
manifest, option-schema, Foundation-source, and public engine protocols and
APIs remain unchanged.

## Consequences

- Discovery from this source tree returns `cli`, `jupyter`, and `library` in
  lexical order. The published `v0.3.2` wheel remains the two-archetype line
  until FT-12.04 publishes `0.4.0`.
- Library and CLI Application can select Jupyter without receiving a notebook
  or runtime dependency; omitting it leaves their output unchanged.
- A selected capability owns `scripts/check_notebooks.py` and contributes only
  through reviewed Foundation points, preserving path ownership and the
  side-effect-free engine facade.
- The aggregate project check now executes notebook validation whenever
  Jupyter is selected. There is deliberately no generated opt-out.
- Tests pin safe failure serialization, structural aggregation, source-byte
  preservation, real-kernel execution, Python endpoint resolution, locked
  aggregate checks, and wheel resources.
- Scientific Python, Data Science content, CLI selection, the `0.4.0` release,
  and cross-capability validation remain owned by later roadmap issues.
