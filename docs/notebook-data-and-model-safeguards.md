# Notebook, data, and model safeguards

This document defines fail-closed notebook validation and the data, model,
artefact, secret, and generated-output safeguards for generated Forge
projects. It is the canonical living contract accepted by
[ADR 0047](adr/0047-notebook-data-and-model-safeguards.md) for FT-10.03.

FT-11.02 now packages the
[`jupyter` capability](data-science-capabilities.md#jupyter-capability) and its
notebook check in the source catalogue under [ADR
0050](adr/0050-production-jupyter-capability.md). FT-12.02 /
[ADR 0054](adr/0054-data-science-notebook-and-artefact-layout.md) adds the
[Data Science archetype](data-science-archetype.md)'s output-free starter
notebook and the five root-anchored working-tree ignore entries this contract
fixes. The published `0.3.2` wheel and direct-Copier Library path remain
unchanged.

## Safeguards are generated-project checks, not engine validation

`notebook:check` is a generated-project Poe task. It runs after `create-forge`
hands the project over, in the project's own environment, and is not part of
the engine's
[generated-project validation](generated-project-validation.md). It adds no
`ForgeEngineError` code, detail code, or operation, and the engine never
executes it.

This follows the existing boundary rather than widening it. Generated-project
validation already lists "secret-example and ignore-file policy", "git
tracking or clean-tree state", and "generated command execution" as checks
that stay outside the in-memory engine. All three of this contract's concerns
are on that side of the line.

The check still borrows the engine's failure *style*: it reports every
independently detectable failure in one run, orders them deterministically,
and identifies each with a stable string. A consumer branches on the
identifier and the notebook path, never on prose.

Ownership is unchanged from the accepted contracts. The
[`jupyter` capability](data-science-capabilities.md#jupyter-capability) owns
the task, its four development dependencies, and its entry in the aggregate
quality contract. The [Data Science archetype](data-science-archetype.md)
owns `notebooks/getting-started.ipynb` and the working-tree ignore entries.
Foundation owns the root `README.md` and `.gitignore` and accepts only
reviewed contributions into them. Forge supplies no path helper, data loader,
model registry, or artefact API — a notebook check does not change that.

## What the notebook check proves

A passing `notebook:check` establishes exactly two properties, and no more:

1. **Every committed notebook is clean.** No code cell carries an execution
   count or a stored output, and the notebook carries no stored widget state.
2. **Every clean notebook runs.** A copy of each notebook executes top to
   bottom, without error, in the project's own environment, on this
   workstation, at this moment.

It does not prove that a notebook is correct, deterministic, reproducible on
another machine, free of network dependence, or safe to run. It proves the
two properties above and is not evidence of anything else.

## Validation order

The check runs one fixed sequence. The order is normative: an implementation
that reorders these steps is non-conformant.

1. **Resolve the notebook set.** Collect every `*.ipynb` file in the project,
   excluding `.ipynb_checkpoints/`, `.git/`, `.venv/`, and the ignored
   working trees below. Sort the results as project-relative POSIX paths.
   Discovery reads the filesystem, not `git ls-files`, so a project exported
   without history stays checkable.
2. **Pass on an empty set.** No notebooks is a success: the task exits zero,
   starts no kernel, creates no temporary directory, and prints nothing. A
   selected `jupyter` capability in a project with no notebooks — a Library
   or CLI Application project, for instance — therefore passes with no side
   effects.
3. **Parse each notebook with nbformat.** Read the file as UTF-8 and parse it
   against its declared schema version. A decode, JSON, or schema failure
   ends that notebook's processing; it is neither cleanliness-checked nor
   executed.
4. **Assert cleanliness on the tracked source.** For every code cell, in
   order: `execution_count` is null and `outputs` is empty. For the notebook:
   `metadata.widgets` is absent. Markdown and raw cells carry neither field
   and are not examined.
5. **Short-circuit before executing anything.** If any notebook failed step 3
   or step 4, report every structural failure across every notebook and exit
   non-zero. No kernel starts and no code runs.
6. **Copy each clean notebook.** Create one temporary directory for the run,
   outside the project tree, and place a byte-for-byte copy of each notebook
   in it.
7. **Execute each copy with nbclient.** Run the copies sequentially, in the
   same sorted order, with a 300-second timeout, with errors disallowed, and
   with the working directory set to the *tracked* notebook's own directory.
8. **Discard and report.** Remove the temporary directory unconditionally,
   then exit zero on a clean run or non-zero with the ordered failure list.

Parsing precedes cleanliness because `execution_count` and `outputs` are
schema fields: asserting on them before the document is known to be a valid
notebook would raise an incidental error instead of a contract failure.

Cleanliness precedes execution because a notebook the check could not fully
parse, or one carrying stale output, is not input the check is willing to
run. Executing a dirty notebook would also produce a second failure for the
same file and push a developer toward fixing the failing cell rather than
clearing the output. Refusing to run is the conservative direction and is
always the direction taken.

Structural failures are collected in full because the checks are cheap and
bounded, matching the engine's "every independently detectable failure"
style. The execution stage instead stops at the first failing notebook and
reports **at most one** execution failure: five notebooks each reaching a
300-second cell timeout is a twenty-five-minute run, and a bounded report is
worth more than a complete one here. A run therefore reports either every
structural failure or one execution failure, never both.

### The 300-second timeout is per cell

The value is nbclient's per-cell execution timeout. It bounds how long the
check waits for a single cell, not how long a notebook or a run may take.
This contract adds no whole-notebook or whole-run budget: a notebook with
many cells may legitimately run longer than 300 seconds in total, and an
arbitrary aggregate cap would fail slow-but-correct notebooks
non-deterministically.

### The kernel is the project's own

The copy executes with the project's `ipykernel`-backed kernel, not with the
kernel named in `metadata.kernelspec`. A recorded kernel name is workstation
state that need not exist elsewhere, and the check exists to prove the
notebook runs in *this* project's environment. A `kernelspec` mismatch is not
a failure; a project kernel that cannot be resolved is.

### Execution runs in the notebook's directory

The copy executes with its working directory set to the directory of the
tracked notebook, so a relative path such as `../data/raw/sample.csv`
resolves exactly as it does in an interactive session. Executing from the
temporary directory would break every notebook that reads project-relative
data, which is most of them in the projects this archetype exists for.
Setting the directory explicitly rather than inheriting the caller's applies
the
[no implicit process context](paths-and-resources.md#no-implicit-process-context)
rule to the check itself.

## Source preservation and the temporary copy

The task has one write root: a per-run temporary directory created through
the standard library's `tempfile`. The tracked notebook is opened for reading
only and is never a write target at any point.

nbclient populates execution counts and outputs on an in-memory notebook node
during execution. That node is never written back. There is no in-place mode,
no `--fix`, no output-stripping rewrite, and no executed-notebook artefact
left anywhere in the project. The check reports; the developer clears
outputs.

The temporary directory is outside the project tree so its contents can never
be staged, matched by an ignore rule, or picked up by a later discovery pass.
It is never placed inside `data/`, `models/`, or `artifacts/`: those trees
hold a user's working material and are ignored, not scratch space. The
directory is removed on success and on failure alike; an interrupted run
leaves the tracked notebook byte-identical and at worst leaks a temporary
directory to the operating system's own cleanup.

FT-11.02's focused validator tests demonstrate the required property: a
tracked notebook's bytes are identical before and after a run, including
after a failing run.

## Fail-closed behaviour

Fail-closed means every condition the check cannot positively confirm
produces a non-zero exit. No condition is skipped, downgraded to a warning,
retried, or resolved by changing the project.

| Failure | Stage | Behaviour |
| --- | --- | --- |
| File unreadable or not UTF-8 | Parse | Notebook not checked further; run keeps collecting structural failures |
| Invalid JSON | Parse | As above |
| Invalid notebook schema | Parse | As above |
| Execution count present | Cleanliness | Collected; execution stage never starts |
| Cell output present | Cleanliness | Collected; execution stage never starts |
| Stored widget state present | Cleanliness | Collected; execution stage never starts |
| Temporary copy cannot be created | Copy | Run ends immediately; nothing executes |
| Project kernel unavailable | Execution | Run ends immediately; not a skip, not a pass |
| Cell raised an exception | Execution | Run ends at that notebook |
| Cell exceeded 300 seconds | Execution | Run ends at that notebook |

A missing kernel is never read as "notebook checking unavailable, pass". A
notebook with zero cells passes. A notebook with only markdown cells passes.
A notebook outside `notebooks/` is checked identically to one inside it: the
`jupyter` capability owns no notebook, and any component may own one.

### Stored widget state

The [FT-10.03 scope](https://github.com/Sandsy09/forge-template/issues/103)
names execution counts and cell outputs. This contract adds `metadata.widgets`
as a third cleanliness assertion because stored widget state is
output-derived, can embed rendered values, and survives an outputs-only clear
in some tools. Treating it as a fourth failure class rather than silently
tolerating it keeps the cleanliness guarantee whole.

## Deterministic failure identifiers

Every failure carries one stable kebab-case identifier, in the spirit of the
engine's `missing-pyproject` and `unordered-plan-targets` detail codes:

| Identifier | Stage |
| --- | --- |
| `unreadable-notebook` | Parse |
| `invalid-notebook-json` | Parse |
| `invalid-notebook-schema` | Parse |
| `execution-count-present` | Cleanliness |
| `cell-output-present` | Cleanliness |
| `widget-state-present` | Cleanliness |
| `temporary-copy-failed` | Copy |
| `kernel-unavailable` | Execution |
| `cell-execution-failed` | Execution |
| `cell-execution-timeout` | Execution |

Failures are ordered by project-relative POSIX notebook path, then by
zero-based cell index, then by identifier. Cell indices count every cell,
including markdown and raw cells, because a clean notebook has no execution
count to refer to. A failure with no cell index — every parse, copy, and
kernel failure — sorts before any indexed failure for the same path.

The identifiers are part of the `jupyter` capability's observable surface.
Adding one for a newly detectable condition is a compatible change. Renaming,
removing, or redefining one is a breaking change that requires a
component-version assessment under the
[compatibility policy](compatibility-policy.md).

## Safe diagnostics

A failure report may contain only:

- the project-relative POSIX notebook path;
- the zero-based cell index, where the failure has one;
- the failure identifier;
- a fixed sentence associated with that identifier; and
- for `cell-execution-failed`, the raised exception's type name.

A failure report must not contain cell output of any mime type, a traceback,
captured standard output or error, an exception message or its arguments,
cell source text, a data value or dataframe rendering, an environment
variable name or value, or an absolute filesystem path — including the
temporary directory, which would disclose a home directory or user name.

The path and the cell index locate the failure exactly, and the tracked
notebook is the reviewable source. A developer reproduces the full traceback
by running the notebook through the `notebook` task; the check is a gate, not
a debugger. This is deliberately terser than a test runner's output, because
a notebook's output surface is the one most likely to carry rendered data,
printed configuration, or a client object's repr.

The principle is already stated in full by
[exception ownership](exception-ownership.md#messages-and-diagnostics-carry-no-secrets);
this section applies it to one tool.
[Structured logging](structured-logging.md) does not apply: it governs a
generated project's runtime events, while `notebook:check` is a development
task that writes plain task output, so its defensive redaction is not a
fallback the check may lean on.

## Execution is a correctness gate, not a sandbox

Executing a notebook executes arbitrary code with the developer's full
ambient identity: their environment variables, their credential files on
disk, their cloud session, their network access, their filesystem
permissions. Forge claims no network isolation, no filesystem confinement, no
resource limit, and no credential scrubbing for `notebook:check`. The
temporary copy isolates the *file*, not the *process* — a distinction the
phrase "temporary copy" can hide.

The check answers one question: does this notebook run to completion in this
project's environment. It is not a security boundary and must not be used as
one. A notebook is executable source; running `notebook:check` over an
untrusted notebook is running an untrusted script, and the review that would
apply to a `.py` file applies to a `.ipynb` file.

The consequences are concrete. A notebook that reaches the network reaches it
during the check. A notebook that reads a credential reads it. A notebook
that writes a file writes it into the real project directory, because step 7
executes there. Keeping network calls, credential reads, and expensive work
out of a notebook that must pass the check is a project responsibility, not
something the check enforces.

This reaches CI. [ADR 0046](adr/0046-initial-data-science-capabilities.md)
places `notebook:check` in the aggregate quality contract, and
[Foundation guarantees](foundation-guarantees.md) that platform CI runs that
same contract. A generated project whose CI runs the aggregate contract
therefore executes its notebooks in CI, with the workflow job's identity and
secrets. FT-11.02 wires `notebook:check` unconditionally into the aggregate
contract whenever `jupyter` is selected and provides no per-notebook opt-out.
Selecting an execution sandbox remains outside this contract's accepted
scope.

## Ignored working trees and prose-only guidance

The [Data Science archetype](data-science-archetype.md#local-working-trees)
contributes these entries to the root `.gitignore`, root-anchored:

```text
/data/raw/
/data/interim/
/data/processed/
/models/
/artifacts/
```

These five are the complete accepted set. Adding a sixth is an archetype
ownership decision, not an implementation detail.

Root-anchoring is normative, and it is how this contract discharges the audit
rule that
[secret handling](secret-handling.md#secret-bearing-files-stay-out-of-version-control)
already binds every ignore change to: "An ignore rule must never shadow a
file the project intentionally tracks", and the mistake is silent because an
ignored file is invisible to `git status`. An unanchored `models/` rule would
match `src/<package_name>/models/`, an ordinary package directory in exactly
these projects, and untrack it without a trace. A bare `data/` rule would
reach any nested `data/` directory the same way. The existing unanchored
`dist/` and `build/` entries are left as they are: those names are
unambiguous build outputs, whereas `data` and `models` are domain words that
also name source directories. No entry here may shadow `notebooks/`, `src/`,
`tests/`, or any tracked root file.

`.ipynb_checkpoints/` is a `jupyter`-owned ignore entry, not an archetype
one: JupyterLab writes it beside whichever notebook is open, so it is
unanchored, and the capability that causes it owns it. It is also in the
check's discovery exclusion set, so a checkpoint copy is never validated or
executed. FT-11.01 resolved the extension point a capability contributes a
`.gitignore` entry through: it is the **existing** `gitignore-project-shape`
point, which now accepts contributions from any selected owner — archetype or
capability — in composition order, rather than a new capability-specific point
([extension-points.md](extension-points.md#capability-tooling-extends-the-same-foundation-content),
[ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md)).
FT-11.02 now supplies that exact contribution through the production Jupyter
manifest ([ADR 0050](adr/0050-production-jupyter-capability.md)).

**The FT-10.03 scope requires that guidance markers for these trees remain
tracked. The tracked guidance is prose and rules, not placeholder files.**
The archetype's `readme-project-shape` contribution documents each tree and
its purpose in the root `README.md`, and its `gitignore-project-shape`
contribution carries the ignore entries in the root `.gitignore`. Both are
tracked, reviewed files. No `.gitkeep`, per-directory `README.md`, or other
placeholder is introduced. The
[Data Science archetype contract](data-science-archetype.md#local-working-trees)
therefore stands unchanged and
[ADR 0045](adr/0045-data-science-project-shape.md) is not superseded: the
trees still carry no tracked placeholder, and a clean checkout still does not
contain them until a user or a selected component creates them.

Nothing in the generated project creates these directories eagerly, and no
check fails because they are absent. A stray notebook saved into `artifacts/`
is neither validated nor executed, because discovery excludes the ignored
trees.

## Generated source and tracked examples carry no payloads

[Secret handling](secret-handling.md) already owns the mechanics: the `.env`
family and credential and key artefacts are ignored with an explicit
`!.env.example` negation, the tracked `.env.example` carries placeholder
assignments only, a `detect-private-key` pre-commit hook runs locally, and
generation-time inputs — Copier answers, ProjectSpec fields, policy — are
never secret sources. This contract does not restate those rules.

What it adds for a data project:

- **The no-output rule is a secret safeguard, not only diff hygiene.** An
  executed notebook's outputs routinely carry a printed environment mapping,
  a rendered dataframe of personal or licensed data, or a client object's
  repr holding a token. Clearing outputs removes that surface before it can
  reach a commit, which is why the cleanliness assertions run against the
  tracked source and not only against the executed copy.
- **No dataset, trained model, or generated binary is tracked** — in
  generated source, in this repository's fixtures, or in a tracked example.
  The ignore entries keep the conventional locations out of history; this
  rule covers the same content stored anywhere else.
- **No byte threshold is set.** "Large" has no natural boundary, and an
  arbitrary number would be unenforced prose or an unrequested new check. The
  category rule, the ignore entries, and review are the enforcement. A
  threshold is deferred.
- **A tracked notebook reads configuration the way runtime code does**,
  through the
  [environment-variable conventions](environment-variables.md). The absence
  of a Forge data loader is not licence to hard-code a credential, an
  absolute path, or a tokenised data-source URL in a tracked notebook — and
  `.copier-answers.yml` is permanently public, so a generation-time answer
  must never carry one either.

The starter notebook is the worked example: tracked, output-free, standard
library and the generated package only, no embedded data, no network access.
Its shape is [ADR 0045](adr/0045-data-science-project-shape.md)'s; its
output-free property is what this check enforces.

## Alignment with existing contracts

Each FT-10.03 acceptance criterion resolves against an existing owner plus a
narrow new decision here.

| Acceptance criterion | Already owned | New here |
| --- | --- | --- |
| Contract and ADR define validation order, deterministic failures, safe diagnostics | ADR 0046 assigned ordering, timeout, source preservation, errors, and diagnostics to FT-10.03; exception ownership owns the no-secrets-in-diagnostics principle; generated-project validation supplies the ordered, code-addressable failure style | The eight-step order, the empty-set pass, the short-circuit rule, the ten identifiers and their sort order, the per-class fail-closed table, and the diagnostic allow and deny lists |
| Notebook checks preserve the tracked source | ADR 0045 fixed the notebook path and its output-free property; ADR 0046 assigned temporary-copy execution to nbclient | The single write root, the outside-the-tree temporary location, unconditional discard, the ban on any in-place or fix mode, and the byte-identity property demonstrated by FT-11.02 |
| Tracked guidance and ignore rules cover every accepted path | ADR 0045 fixed the five trees, the no-placeholder rule, and the two extension points; secret handling owns the anti-shadowing audit | The prose-only reading of "guidance markers", root-anchoring as the concrete way that audit is discharged, and `.ipynb_checkpoints/` as a `jupyter`-owned entry |
| Alignment with secret, path/resource, and generated-project validation policies | Secret handling owns ignore, example, and hook policy; paths and resources owns no-implicit-context; generated-project validation excludes ignore policy, git state, and command execution from the engine | That `notebook:check` is a generated-project task adding no `ForgeEngineError` code, introduces no runtime path helper, and sets the executed copy's working directory explicitly |

## Deferred decisions

This contract does not decide or implement:

- DVC or any data-versioning tool, remote object storage, a model registry,
  an experiment tracker, or deployment and serving integration;
- an execution sandbox, network isolation, credential scrubbing, or resource
  limits for `notebook:check`;
- automated output stripping — `nbstripout`, a pre-commit hook, or a `--fix`
  mode — and any notebook or data size threshold;
- per-notebook exclusions or a verbose diagnostic mode; and
- the Scientific Python packaged manifest, resources, implementation, and
  tests, owned by FT-11.03.

FT-10.04 subsequently accepted compatibility, the executable acceptance
matrix, and the `forge-template` `0.4.0` release classification in the
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md);
it makes this contract's `notebook:check` a required generated-project
acceptance row at both Python endpoints and changes nothing in the validation
order, identifiers, diagnostics, or safeguards above. FT-11.01 then delivered
the Foundation extension points for development dependencies, Poe tasks, and
aggregate-check entries, and resolved the capability-contributed ignore entry
onto the existing `gitignore-project-shape` point
([ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md)).
FT-11.02 then delivered the package-bound Jupyter manifest, generated
validator, fixed tasks, aggregate-check entry, README guidance, and checkpoint
ignore contribution ([ADR 0050](adr/0050-production-jupyter-capability.md)).

The Jupyter implementation adds its package-bound manifest and generated
content on `main`; it changes no public API, ProjectSpec, template, Copier
answer, tag, or release.
