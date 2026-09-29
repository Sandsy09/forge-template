# 80. Define the batch project shape and ownership

Date: 2026-09-29

## Status

Accepted

Records the decisions for
[FT-27.01](https://github.com/Sandsy09/forge-template/issues/199), the first
child of [FT-EPIC-27](https://github.com/Sandsy09/forge-template/issues/189).
The epic stays open: [FT-27.02](https://github.com/Sandsy09/forge-template/issues/200)
is not yet decided.

## Context

The 21 September 2026 engineering review asked for a scheduling-neutral
Pipeline/Batch Job archetype, with the identity and shape decided ahead of
implementation, exactly as [ADR 0068](0068-streamlit-project-shape.md) did
for Streamlit and [ADR 0045](0045-data-science-project-shape.md) did for Data
Science. The released `0.6.0` catalogue contains no batch component,
resource or generated content.

FT-27.01's acceptance criteria require deciding the component ID/name, src
layout, entry command/module, input/config format, a sample transformation,
output location and exit-code semantics; rerun/idempotency, overwrite
safeguards, failure handling and logging without pretending to provide a
workflow engine; independent runnability with no Forge runtime dependency;
and recording Python support, dependencies, extension points, user stories
and acceptance examples in a living contract and this ADR. The issue
explicitly excludes scheduling, workers/queues, cloud services, databases,
retries/checkpoint engines and orchestration integrations unless separately
approved — none are approved here.

Nine choices were needed. Each is decided against the direct CLI Application
(ADR 0034/0035) and Streamlit (ADR 0068) precedents.

## Decision

Publish the shape as the living contract
[batch-archetype.md](../batch-archetype.md) and record the choices here.

1. **Identity is `batch` / Batch Job**, an optionless archetype. Rejected:
   `pipeline` (the epic's title names "Pipeline and Batch Job" together, but
   this contract ships one concrete, schedule-agnostic job runner, not a
   multi-step pipeline engine; `pipeline` overstates the scope and invites
   scheduling/orchestration expectations the exclusions forbid); `batch-job`
   (breaks the one-word pattern `library`, `cli`, `data-science` and
   `streamlit` set).

2. **The entry point is a console script and a `python -m` module,
   mirroring `cli`'s pattern exactly**: `main()` in
   `src/<package_name>/job.py`, exposed as
   `{{ project.repository_name }} = "{{ project.package_name }}.job:main"`
   through `pyproject-entry-points`, and re-exposed by
   `src/<package_name>/__main__.py` for `python -m <package_name>`. Rejected:
   a root launcher script as Streamlit uses (that pattern exists because
   Streamlit's own runner executes a script by path; batch has no such
   external runner, so the installable-console-script pattern that `cli`
   already established is the correct precedent, not Streamlit's).

3. **No runtime dependency: the job reads and writes JSON using only the
   standard library, with no CLI-parsing or scheduling framework.** This is
   the one place batch deliberately diverges from every other archetype
   (`cli` depends on `typer`, `streamlit` on `streamlit`). A "scheduling-neutral"
   contract should not quietly commit to a workflow, queue or CLI-argument
   library the exclusions otherwise forbid mentioning by name. Rejected:
   `typer` or `click` for argument parsing (the job takes no arguments — see
   choice 6 — so a CLI-parsing dependency has nothing to parse); a workflow
   library such as `prefect` or `luigi` (exactly what the exclusions forbid).

4. **Input and output are JSON**, read and written with the standard
   library's `json` module. Rejected: TOML (`tomllib` is read-only in the
   standard library; writing output would need a third-party dependency,
   which choice 3 rules out); YAML (needs a third-party dependency); CSV (fits
   flat tabular data only and cannot represent the nested sample record the
   contract ships).

5. **The sample transformation reads a tracked `data/sample_input.json`
   (a small list of records) and writes `data/output.json`**, adding one
   derived field per record (a normalised, upper-cased `id` field, mirroring
   the "greets the name entered" triviality of `cli`'s and `streamlit`'s
   starters) using only the standard library. Rejected: reading from stdin
   (gives the generated project nothing to inspect or version, and no fixed
   path for the test in choice 9 to assert against); shipping no sample data
   (leaves the "executable example job" criterion undemonstrated).

6. **The job takes no command-line arguments; the input and output paths are
   the fixed relative paths from choice 5.** Rejected: configurable paths via
   `argparse` (adds a parsing surface and a dependency-free CLI contract to
   maintain for a scaffold whose purpose is demonstrating the shape, not
   general argument handling — that need is already met by the `cli`
   archetype, which a project can add alongside batch's own generated code if
   it needs one).

7. **Output is overwritten on every run with no safeguard, written
   atomically (temp file plus `os.replace`).** The transform is a pure,
   deterministic function of the tracked input, so re-running it is always
   safe and produces byte-identical output; there is nothing to protect by
   refusing to overwrite it. The atomic write means a crash mid-run leaves
   the previous good output in place rather than a truncated file. Rejected:
   an opt-in `--force`/`--no-clobber` flag (adds a flag with nothing to
   distinguish — the output is always regenerable, never hand-edited);
   timestamped or versioned output files (accumulates artefacts with no
   cleanup story, which is exactly the "retries/checkpoint engine" surface
   the issue excludes).

8. **On a malformed record the job logs the failure with `logging`, raises,
   and exits non-zero (`1`) without writing any output.** This is fail-fast,
   not skip-and-continue: a partial output file is a worse failure mode than
   no output file, because a caller checking only the exit code could ship
   incomplete results. Skip-and-continue would also need a resumability or
   partial-success concept, which is checkpoint/retry territory the issue
   excludes. Logging goes to `stderr` via the standard library `logging`
   module at `INFO` for a per-record summary and `ERROR` for the failure;
   there is no third-party logging dependency. Rejected: skip-and-continue
   with a non-zero exit only if any record failed (silently ships partial
   output on the happy path of "some records worked"); printing instead of
   `logging` (no configurable verbosity, and every other archetype's tooling
   already assumes standard `logging`).

9. **The pin is `tests/test_batch_contract.py`, a tripwire**, following ADR
   0068's choice 9 exactly: it asserts against the live engine that `batch`
   is not yet in the catalogue and that every Foundation extension point
   this contract names exists, so it fails deliberately when a future
   implementation stage lands the component.

The contract excludes scheduling, worker/queue integration, cloud services,
databases, retries and checkpoint engines, and orchestration integrations, as
the issue requires.

This decision changes no runtime code, generated content, engine module,
public signature, `EngineErrorCode`, protocol integer, component, dependency,
extension point, `copier.yml`, `template/` file or `foundation.toml`. The
package stays `0.6.0` and untagged.

## Consequences

- FT-27.02 is unblocked with a fixed shape on which to build its capability
  matrix, manifest protocol choice, Python window and acceptance strategy. It
  still decides the component version and the target provider compatibility
  line, which are not fixed here.
- A future implementation stage has an exact file list, manifest identity and
  set of Foundation contributions, and inherits the rule that no sibling
  archetype's resources are read.
- No new extension point is needed: `pyproject-build-system`,
  `pyproject-archetype-metadata`, `pyproject-build-configuration`,
  `pyproject-classifiers`, `pyproject-task-definitions`,
  `gitignore-project-shape` and `readme-project-shape` already cover every
  concern this contract names, so the extension-point inventory and its pin
  are unchanged.
- `tests/test_batch_contract.py` fails when `batch` first appears in
  `discover_components()`, forcing the contract and implementation into step,
  the same tripwire discipline ADR 0068 and ADR 0061 established.
- `docs/roadmap-v5/**` and its hash-pinned issue mirrors are untouched.
  FT-EPIC-27 stays open until FT-27.02 is complete.
