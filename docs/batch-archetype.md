# Batch Archetype Contract

This document defines the `batch` archetype's project shape and ownership
boundaries. It is the canonical living contract accepted by
[ADR 0080](adr/0080-batch-project-shape.md) for
[FT-27.01](https://github.com/Sandsy09/forge-template/issues/199).
[FT-28.01](https://github.com/Sandsy09/forge-template/issues/201) /
[ADR 0082](adr/0082-batch-archetype-implementation.md) implemented this shape:
`discover_components()` now returns `batch`, and
`tests/test_batch_contract.py` pins that fact, updated in step with the
implementation rather than deleted.
[FT-28.02](https://github.com/Sandsy09/forge-template/issues/202) /
[ADR 0083](adr/0083-validate-batch-generated-projects.md) then validated it as
generated projects and distributions; the evidence is in
[batch-validation.md](batch-validation.md).

## Archetype identity and fixed choices

Batch is an independent, package-backed archetype for a single,
scheduling-neutral data-transformation job, composed over the same implicit
Foundation as Library, CLI Application, Data Science and Streamlit. Its
identity and fixed project choices are:

| Concern | Contract |
| --- | --- |
| Component ID | `batch` |
| Display name | Batch Job |
| Component options | none |
| Packaging | `uv-build-static` |
| Build requirement | `uv_build>=0.12,<0.13` |
| Runtime entry point | console script `{{ project.repository_name }}` and `python -m <package_name>`, both calling `main()` in `src/<package_name>/job.py` |
| Console script | `{{ project.repository_name }}` |
| Intrinsic runtime dependencies | none — standard library only |
| Input / output format | JSON, via the standard library `json` module |

The component ID names the domain, as `library`, `cli`, `data-science` and
`streamlit` do. It declares no option schema: a valid batch ProjectSpec uses
`components.archetype = "batch"` and adds no `batch` entry to
`component_options`. The component version, the engine-package line that
first ships it, the supported Python window and the capability matrix are
[FT-27.02](https://github.com/Sandsy09/forge-template/issues/200)'s decisions,
recorded once accepted in a compatibility-and-acceptance contract analogous
to [streamlit-compatibility-and-acceptance.md](streamlit-compatibility-and-acceptance.md).

Batch is the one archetype with **no intrinsic runtime dependency**. `cli`
depends on `typer` and `streamlit` on `streamlit`; batch's job is
deliberately schedule- and framework-neutral, so it commits to nothing beyond
the standard library (see [ADR 0080](adr/0080-batch-project-shape.md), choice
3).

## Reserved generated shape

The production component owns this minimal tracked shape:

```text
src/<package_name>/__init__.py
src/<package_name>/__main__.py
src/<package_name>/job.py
src/<package_name>/py.typed
tests/__init__.py
tests/test_job.py
data/sample_input.json
```

The package is independent rather than inherited from any existing
archetype. Its root public API exports only `__version__`, resolved from
installed distribution metadata with the same deterministic `0.0.0` fallback
the other archetypes use. `__init__.py`, `py.typed` and `tests/__init__.py`
are byte-identical to `library`'s copies — copied into the archetype's own
content tree, never read across archetypes.

`data/sample_input.json` is sole-owner `create` content: a small, deterministic
list of JSON records the generated job transforms on every run. Foundation
publishes no file under `data/`, so nothing collides.

## Application entry point

`main()` in `src/<package_name>/job.py` runs the transformation. It is
exposed two ways, exactly as the `cli` archetype exposes its own entry point:

- a console script, `{{ project.repository_name }} = "{{ project.package_name }}.job:main"`,
  through `pyproject-entry-points`; and
- `python -m <package_name>`, through a generated `__main__.py` that imports
  and calls `main()`.

The job takes no command-line arguments. It reads the fixed path
`data/sample_input.json`, applies one deterministic transformation (adding a
normalised, upper-cased `id` field to each record — the same order-of-magnitude
triviality as `cli`'s greeting or Streamlit's starter widget), and writes
`data/output.json`. There is no scheduler, worker, queue, retry or checkpoint
concept: rerunning the console script is the only supported way to re-execute
the job, and doing so is always safe (see below).

## Packaging and dependency contract

Batch uses the same fixed packaging mode as `cli` and `streamlit`:

- `uv_build>=0.12,<0.13` and `uv_build` as the PEP 517 backend;
- `src/<package_name>/` as the build module and source root;
- wheel and source-distribution output; and
- inline typing through `src/<package_name>/py.typed`.

It declares **no runtime dependency**. The job reads and writes JSON with the
standard library only, and takes no arguments, so it needs no CLI-parsing
library either. The distribution contains only `src/<package_name>/`;
`data/sample_input.json` is a source-tree file, consistent with the
no-deployment boundary every archetype shares.

## Rerun, idempotency and failure handling

Rerunning the console script is always safe and idempotent: the
transformation is a pure function of the tracked input, so two runs against
an unchanged `data/sample_input.json` produce byte-identical output. Output
is written atomically — to a temporary file, then renamed into place with
`os.replace` — so a crash mid-run never leaves a truncated `data/output.json`
in place of a good one.

There is no overwrite safeguard, because there is nothing distinct to
protect: `data/output.json` is always regenerable from the tracked input and
is never intended to be hand-edited. On a malformed input record the job
**fails fast**: it logs the failure through the standard library `logging`
module (`ERROR` level, with the offending record's index) and exits `1`
without writing any output file. This is a deliberate choice against
skip-and-continue, which would ship a silently partial result on the exit
code a caller is most likely to treat as success; see
[ADR 0080](adr/0080-batch-project-shape.md), choice 8, for the full
reasoning. `INFO`-level logging reports the record count processed on a
successful run. Batch is not a workflow engine: there is no retry, no
checkpoint and no resumable partial state.

## Tests

The archetype owns `tests/test_job.py`. It asserts:

- running the job against the tracked `data/sample_input.json` produces the
  expected `data/output.json` content;
- running it twice produces byte-identical output (idempotency); and
- a malformed record (built in a temporary directory, never touching the
  tracked fixture) makes the job exit non-zero and write no output file.

As with every archetype, the test asserts behaviour and meaningful content
rather than snapshotting framework internals.

## Foundation extension requirements

Batch uses only points Foundation already publishes; no new extension point
is required and the published inventory in
[extension-points.md](extension-points.md) is unchanged:

| Extension point | Used | Carries |
| --- | --- | --- |
| `pyproject-build-system` | yes | the `uv_build` backend |
| `pyproject-archetype-metadata` | yes | the static initial version |
| `pyproject-build-configuration` | yes | `[tool.uv.build-backend]` module settings |
| `pyproject-classifiers` | yes | archetype classifiers (final list fixed by FT-27.02) |
| `pyproject-entry-points` | yes | the `{{ project.repository_name }}` console script |
| `pyproject-runtime-dependencies` | no | there is no runtime dependency |
| `pyproject-task-definitions` | yes | a `run` task invoking the console script |
| `pyproject-aggregate-check` | no | `check` must terminate; the job itself terminates, but contributes nothing extra |
| `readme-project-shape` | yes | project structure and how to run the job |
| `gitignore-project-shape` | yes | ignoring `/data/output.json` |
| `pyproject-development-dependencies` | no | no development-only constraint is known yet |

## Ownership map

| Concern | Owner |
| --- | --- |
| Neutral project identity, licence, prerequisites, lock and quality guarantees, root guidance, repository hygiene | Foundation |
| Root `pyproject.toml`, `README.md` and `.gitignore` source files | Foundation, accepting only reviewed component contributions |
| Package, test, console-script and job-module paths, packaging and version metadata, classifiers | Batch archetype |
| `data/sample_input.json` and the `/data/output.json` ignore entry | Batch archetype, the latter through `gitignore-project-shape` |
| The `run` task | Batch archetype, through `pyproject-task-definitions` |
| Project-shape and run guidance within the root README | Batch archetype, through `readme-project-shape` |
| CI, repository-provider, delivery and deployment integrations | Selected platform components |
| Discovery-driven input, ProjectSpec construction, staging, lock finalisation and atomic destination placement | `create-forge` |

Batch may reuse Foundation extension points and public template variables. It
may not read or contribute through Library, CLI Application, Data Science or
Streamlit resources, select any of them, or introduce inheritance between
archetypes. The capability and platform matrix is
[FT-27.02](https://github.com/Sandsy09/forge-template/issues/200)'s decision.

Foundation remains provider-, framework-, organisation- and domain-neutral.
Batch's job runner, its JSON contract and its logging configuration never
become universal Foundation dependencies.

## Explicit exclusions

The archetype excludes, for this contract and for its implementation:

- any scheduler, cron integration or scheduling configuration;
- workers, queues and message-broker integrations;
- cloud services, managed compute and deployment targets;
- databases, ORMs and persistence layers;
- retry logic, checkpointing and resumable/partial-run state; and
- orchestration integrations of any kind (workflow engines, DAG runners,
  pipeline frameworks).

Platforms own deployment and delivery. Nothing here introduces a remote
service, and generated code depends on no Forge runtime package.

## Client boundary

`create-forge` discovers component descriptors and constructs an effective
ProjectSpec through the supported public engine facade. It must not copy this
shape, hard-code the `batch` identifier, recreate component requirements or
render archetype content itself. The engine remains the authority for
selection, options, compatibility, planning, rendering and generated-project
validation; the client remains responsible for filesystem effects and lock
finalisation.

## Deferred decisions

[FT-27.02](https://github.com/Sandsy09/forge-template/issues/200) decides the
capability and platform compatibility matrix, the manifest protocol, the
component version, the target provider compatibility line, the supported
Python and dependency window, package build and install requirements,
provenance/skip-if-exists behaviour, update and rename rules, and the
acceptance matrix, in a compatibility-and-acceptance contract analogous to
[streamlit-compatibility-and-acceptance.md](streamlit-compatibility-and-acceptance.md).
No implementation, provider release or client adoption is decided here or in
FT-27.02; those follow in a later implementation stage, mirroring how Stage
20 followed Stage 19 for Streamlit.
