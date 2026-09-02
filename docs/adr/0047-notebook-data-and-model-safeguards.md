# 47. Define fail-closed notebook validation and repository safeguards

Date: 2026-09-02

## Status

Accepted

## Context

[ADR 0045](0045-data-science-project-shape.md) fixed a tracked, output-free
starter notebook and five ignored working trees for the Data Science
archetype, and deferred every safeguard to FT-10.03.
[ADR 0046](0046-initial-data-science-capabilities.md) gave the `jupyter`
capability nbformat and nbclient and the future `notebook` and
`notebook:check` tasks, and explicitly left the validator's ordering,
temporary-copy execution, timeout, source preservation, deterministic
errors, and safe diagnostics here.

Without a fixed order, a plausible naive validator would execute a notebook
it had not finished parsing, write executed output back over the tracked
file, print cell outputs into a CI log, or exit zero when a project has no
notebooks at all. Each is a real default worth ruling out by contract.

Notebook outputs are the largest accidental disclosure surface in a data
project: a rendered dataframe of personal or licensed data, a printed
environment mapping, or a client object's repr holding a token. They also
make a diff unreviewable.

The `data/`, `models/`, and `artifacts/` ignore entries reach the exact
hazard [ADR 0020](0020-generated-project-secret-safeguards.md) already named
— a broad ignore rule silently untracks a file that `git status` never
mentions — and `data` and `models` are ordinary names for directories inside
`src/`.

Executing a notebook runs arbitrary code with the developer's ambient
credentials and network access, and no execution sandbox is being selected,
so the contract must state that limit rather than let "temporary copy" imply
isolation. Separately, the FT-10.03 scope's phrase "guidance markers remain
tracked" needs an explicit reading against ADR 0045's rule that these trees
carry no tracked placeholder.

## Decision

Adopt the canonical
[notebook, data, and model safeguards](../notebook-data-and-model-safeguards.md)
contract. `notebook:check` is a generated-project Poe task outside the engine
validation boundary; it adds no `ForgeEngineError` code and the engine never
runs it.

The check runs one normative eight-step order: resolve the notebook set,
pass with no side effects on an empty set, parse each notebook with nbformat,
assert `execution_count` is null, `outputs` is empty, and `metadata.widgets`
is absent on the tracked source, short-circuit before any execution if a
structural failure exists, copy each clean notebook, execute the copy, then
discard and report.

Structural failures are collected across every notebook and always
short-circuit execution; the execution stage stops at the first failing
notebook and reports at most one execution failure. Execution uses a
byte-for-byte temporary copy created outside the project tree, run with
nbclient at a 300-second per-cell timeout, with the project's own kernel and
the tracked notebook's directory as the working directory. The temporary
directory is discarded unconditionally, the tracked file is never a write
target, and no in-place or `--fix` mode exists.

Ten stable kebab-case identifiers name the failure classes, ordered by
notebook path, then zero-based cell index, then identifier, with file-level
failures sorting first. The identifiers are part of the `jupyter`
capability's compatibility surface. Diagnostics report the notebook path, a
cell index, an identifier, a fixed safe sentence, and at most an exception
type name; never cell output, a traceback, captured streams, an exception
message, cell source, a data value, an environment value, or an absolute
path.

`notebook:check` is a correctness gate, not a security boundary; Forge
claims no network or filesystem sandboxing, and because ADR 0046 places the
task in the aggregate quality contract, a project whose CI runs that
contract executes its notebooks in CI.

"Guidance markers remain tracked" means the tracked root `README.md` prose
contributed through `readme-project-shape` and the tracked, root-anchored
`.gitignore` entries contributed through `gitignore-project-shape`. No
placeholder file is added and ADR 0045 is not superseded. The ignore entries
are root-anchored so `models/` cannot shadow `src/<package_name>/models/`,
every added entry is audited for shadowing before merging, `.ipynb_checkpoints/`
is a `jupyter`-owned entry, and no secret, dataset, trained model, or
generated binary appears in generated source or a tracked example, with no
numeric size threshold set.

## Consequences

- A committed notebook stays reviewable as source and its diff stays
  meaningful, because outputs and widget state never reach a commit.
- A project with no notebooks passes a selected `jupyter` check with no side
  effects, satisfying ADR 0046's requirement directly.
- CI failure output is terse by design; a developer reproduces a full
  traceback by running the notebook locally.
- Because `notebook:check` joins the aggregate quality contract, a generated
  project whose CI runs that contract executes its notebooks in CI with the
  job's identity; the CI wiring and any opt-out remain Stage 11's.
- Root-anchored entries keep `src/<package_name>/models/` and nested `data/`
  directories tracked, at the cost of deviating from the existing unanchored
  build-output entries.
- ADR 0045's no-placeholder rule and its clean-checkout consequence are
  preserved unchanged; ADR 0045 is not superseded.
- Wall clock is bounded per cell, not per run: a notebook with many cells may
  legitimately exceed 300 seconds in total.
- No DVC, remote storage, model registry, execution sandbox, or deployment
  integration is selected; each remains open, as does the FT-10.04
  compatibility and release classification.
- No manifest, dependency, Foundation extension, catalogue entry, generated
  file, public API, protocol, package version, tag, or release changes
  through this decision.
