# Generation provenance and reproducible-update inputs

This is the versioned provider contract required by
[FT-15.02](https://github.com/Sandsy09/forge-template/issues/147), the second
child of the [Engine-Default Cutover](roadmap-v3/README.md) roadmap
([FT-EPIC-15](https://github.com/Sandsy09/forge-template/issues/141)). It
defines the metadata the engine hands a client so a generated project can be
reproduced or updated, who owns each rendered target, and how the engine
behaves when that metadata is malformed, unsupported, or refers to a provider
release that can no longer be obtained.

Its review obligation, **FT-ROADMAP-01-AC-02**, is shared: this document is
the contract; [FT-17.01](https://github.com/Sandsy09/forge-template/issues/150)
implements the metadata schema and public hand-off, and
[FT-17.04](https://github.com/Sandsy09/forge-template/issues/153) implements
the reproducible rendering that consumes it.
[ADR 0059](adr/0059-generation-provenance-and-reproducible-updates.md) records
the decisions.

This document is the contract; it decided no runtime behaviour itself.
[FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) /
[ADR 0062](adr/0062-generation-metadata-and-manifest-protocol-3.md) has since
implemented every name it reserves — the `GenerationMetadata` model on
`RenderedProject.metadata`, `parse_generation_metadata` /
`verify_generation_metadata`, the two `EngineErrorCode` values,
`EngineInfo.metadata_version`, `PlannedFile.regeneration`, manifest protocol
`3`, and `DEFAULT_GENERATION_METADATA_TARGET` — additively, with no generated
content or `copier.yml` change and no package version bump. Where this
document still says "reserved" or "FT-17.01's to finalise", read it as the
contract that was fixed before the implementation; the implementation is
recorded in ADR 0062.

## Why this exists

[engine-default-parity.md](engine-default-parity.md) tiered four rows
`cutover-blocking` and delegated them here:

| Parity row | Gap |
| --- | --- |
| `template/.copier-answers.yml` | the engine keeps no provenance state |
| `_answers_file` | no reproducible old render to diff an update against |
| `_skip_if_exists` | no owner-declared never-clobber disposition |
| "No engine-native update" | `copier update`'s three-way merge has no analogue |

Direct Copier makes `copier update` possible by committing
`.copier-answers.yml` into every generated project: the template ref, a commit
hash, and the stored answers. `copier update` checks out the old template
state, re-renders, renders the new state, and three-way merges the diff into
the working tree. The engine emits component content in memory and has none of
that machinery. This contract is its equivalent — expressed as data the client
persists and acts on, never as a filesystem operation the provider performs.

## Scope and boundary

The provider owns:

- the generation-metadata schema, its canonical serialisation, and its version
  negotiation;
- a **reproducibility guarantee** — the same provider release plus the same
  effective `ProjectSpec` renders byte-identical output;
- the rendered-output ownership map and each target's regeneration
  disposition;
- owner-declared rename records that carry a user's local edits across a path
  change;
- the structured failure taxonomy for metadata the engine is asked to read.

The client owns, unchanged from **FT-ROADMAP-01-EX-01**: writing and reading
the metadata file, provisioning a historical provider release, the working-tree
diff and merge, on-disk conflict resolution, Git, hook execution, and all
presentation. Nothing here moves any of those toward the provider.

## The generation metadata document

One JSON document per generated project. The client persists it — at
`DEFAULT_GENERATION_METADATA_TARGET`, `.forge/generation.json`, by documented
default (ADR 0062; the client still owns writing and committing it) — and
passes it back to the engine to reproduce or update. `GenerationMetadata`
models this shape; `GenerationMetadata.to_json()` is its canonical
serialisation (sorted keys, two-space indent, trailing newline, no
`reproduction` key on an `exact` render).

| Field | Type | Meaning |
| --- | --- | --- |
| `metadata_version` | integer | Schema version of this document; see "Version negotiation". |
| `provider` | object | `{ "distribution": "forge-template", "version": "<exact release>" }` — the installable that produced the render. |
| `protocols` | object | `{ "projectspec": <int>, "component_manifest": [<int>, ...] }` — the protocol integers in force for this render. |
| `spec` | object | The effective `ProjectSpec`, verbatim, in its protocol wire form ([project-spec.md](project-spec.md)). |
| `components` | array | `{ "id": <str>, "version": <str> }` for every selected component — archetype, then capabilities, then platforms, each in the order the plan records. |
| `output` | array | One `{ "target", "owner", "digest", "regeneration" }` entry per rendered file; see below. |
| `reproduction` | object | `{ "mode": "exact" \| "degraded", "reason": <str, when degraded> }`. Absent or `exact` for a normal render. |

The document contains no timestamp, no absolute path, no host or environment
value, and no credential. Every value is drawn from the effective spec, the
installed catalogue, the resolved plan, or the fixed distribution name — the
allowlist "Secret-free persisted and displayed data" makes executable.

### `output` entries

- **`target`** — the project-relative POSIX path, identical to
  `RenderedFile.target`.
- **`owner`** — `"foundation"`, or `"component:<id>"` for a catalogue
  component. This is `PlannedFile.owner` restated as a string; the contract
  cannot claim ownership the engine's plan does not already resolve.
- **`digest`** — `"sha256:<hex>"` over the rendered bytes. A rendered file
  cannot hash itself, which is why the metadata is a provider-assembled
  document and not just another rendered target.
- **`regeneration`** — `"replace"` (the default) or `"skip-if-exists"`. The
  owning component declares a target regeneration-unsafe through a manifest
  protocol `3` `[[regeneration]]` record (ADR 0062); the reference set is
  `CHANGELOG.md` and `.env`, matching `copier.yml`'s `_skip_if_exists`, and no
  shipped component declares one yet — [FT-17.03](https://github.com/Sandsy09/forge-template/issues/152)
  adds the first. The flag travels with whoever owns the content, so a
  documentation or changelog owner carries its own. A Foundation-owned target
  is always `"replace"` — Foundation declares no such record (ADR 0062
  decision 2). The engine records the disposition in `PlannedFile.regeneration`
  and the metadata; the client applies the skip.

## Identity and reproduction

To reproduce a project's original output — the *old* side of an update — the
client:

1. reads `provider.version` and `spec` from the metadata document;
2. provisions that exact `forge-template` release into an isolated
   environment;
3. calls the ordinary public `render_project(spec)`.

The provider ships no historical-render API and bundles no past content trees.
The reproducibility guarantee is what makes step 3 sound: for a given release,
`parse_project_spec` followed by `render_project` is a pure function of the
spec. The determinism half of that guarantee is already exercised — repetition,
selection reordering, catalogue-layout changes, and `PYTHONHASHSEED` variation
all produce identical bytes
([data-science-validation.md](data-science-validation.md),
`tests/test_data_science_composition.py`). This contract adds the cross-release
half: a tagged release never retroactively changes what a recorded spec renders
to.

This mirrors how `copier update` checks out the old tag before re-rendering,
without the provider owning a working copy.

## Update inputs

An engine-native update is a diff of three file sets, all keyed by target:

| Set | Source |
| --- | --- |
| **old** | `render_project(recorded spec)` on the provisioned recorded release |
| **new** | `render_project(effective spec)` on the current release |
| **working tree** | the client reads it from disk |

The provider supplies *old* and *new* and the ownership and rename data below.
The client computes the working-tree comparison and performs the merge —
[CF-16.02](https://github.com/Sandsy09/create-forge/issues/156) owns that
dispatch, conflict, dry-run, cancellation and rollback policy.

Each target resolves to one classification:

| Classification | Meaning |
| --- | --- |
| `unchanged` | old and new bytes are equal |
| `added` | present in new, absent from old |
| `removed` | present in old, absent from new |
| `changed` | present in both, bytes differ |
| `renamed` | an owner-declared record maps an old target to a new one |

A repeated update with no intervening release and no spec change classifies
every target `unchanged` — a no-op the client can detect before touching the
working tree.

### Owner-declared rename records

Moving or deleting a templated path breaks a naive update: the user's local
edits go with the old path and a fresh copy of the new path lands beside them
([invariant 3](invariants.md#3-moving-or-deleting-files-under-template-breaks-updates)).
The engine's answer is the same shape as Copier's `_migrations`: the owning
component declares `[[renames]]` records with `from`, `to` and `since`
(manifest protocol `3`, ADR 0062), where `since` is the canonical PEP 440
component version that introduced the move. During an update the provider
surfaces the records whose `since` falls between the recorded component
versions and the current ones; the client applies each move before diffing, so
the edit is preserved. The catalogue declares none today. Foundation declares
no rename records — a Foundation path move waits for a `foundation_version`
bump (ADR 0062 decision 2). Surfacing which records apply between two versions,
and the `unchanged / added / removed / changed / renamed` classifier, are
[FT-17.04](https://github.com/Sandsy09/forge-template/issues/153)'s.

## Unavailable historical provider

When `provider.version` cannot be obtained — a yanked release, an offline
environment, an index that no longer serves it — the default is a **fail-closed
structured failure** carrying the four facts
[compatibility-policy.md](compatibility-policy.md#reporting-an-unsupported-forge-version)
already requires: the failure happens before any render or write, it names the
axis (`provider`), it states the detected value (the recorded version), and it
states the required action (make that release available, or choose the degraded
path below).

A client **may** offer an explicit, user-chosen **degraded two-way update**:
skip the old render entirely and compare the new render against the working
tree. It loses the ability to tell a user's local edit from an old provider
default, so it is never automatic. When taken, the refreshed metadata document
must record `"reproduction": { "mode": "degraded", "reason": ... }` so the
next update knows the merge base was lost.

## Failure taxonomy

Metadata the engine is asked to read fails through two `EngineErrorCode`
values, added by [FT-17.01](https://github.com/Sandsy09/forge-template/issues/150)
/ ADR 0062:

| Code | Raised when |
| --- | --- |
| `invalid-generation-metadata` | the document is malformed, missing required fields, internally inconsistent, or (from `verify_generation_metadata`) a digest does not match a reproduced target |
| `unsupported-generation-metadata` | `metadata_version` is outside the engine's supported set, or a recorded protocol integer is |

`parse_generation_metadata` runs the closed-world structural check and the
negotiation; `verify_generation_metadata` runs the digest and coverage check
against a re-rendered project. `ForgeEngineError.operation` is `parse` or
`validate` for both codes — never `render`. A corrupt provenance document is
always distinguishable from a malformed generation request. Diagnostics carry
the field path and a fixed safe message only: no rendered content, no secret,
no absolute path — the same discipline
[notebook-data-and-model-safeguards.md](notebook-data-and-model-safeguards.md)
holds notebook diagnostics to.

## Secret-free persisted and displayed data

Every string leaf in the serialised document must trace to one of:

- a value already in the effective `ProjectSpec` (project identity, Python
  selection, component selection, component options, selection provenance);
- an identifier from the installed catalogue (`discover_components()`);
- a target from the resolved plan, or a digest computed over rendered bytes;
- the fixed distribution name `forge-template`, or the provider version string
  from `get_engine_info()`.

No environment variable, no working-directory path, no wall-clock time, no VCS
identity. Author name and email are retained: they are already written into the
generated `pyproject.toml` and `SECURITY.md`, so the metadata reveals nothing
new. They are PII the project author supplied about themselves, not a secret in
the sense [secret-handling.md](secret-handling.md) governs — that document is
about credentials and `.env` contents, which never enter generation input.

## Reconciliation with selection and policy provenance

`ProjectSpec.provenance` (`SelectionProvenance`) records *why* a selection is
what it is — the profile and organisation-policy identifiers that shaped the
effective request
([project-spec.md](project-spec.md#effective-selections-and-provenance)).
Generation provenance records *what was produced* — the provider, the plan,
the digests.

They do not merge. The metadata document embeds the effective spec verbatim,
and that spec already carries its `SelectionProvenance`. No `ProjectSpec` field
is added, `SelectionProvenance` is unchanged, and no policy document is ever
embedded — a policy is selection input, never rendered content
([extension-points.md](extension-points.md)).

## Version negotiation

Generation metadata is the **ninth versioned axis**
([compatibility-policy.md](compatibility-policy.md#generation-metadata-metadata_version)),
reserved by this contract and published by
[FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) / ADR 0062
through `get_engine_info().metadata_version` as a backward-compatible addition.
A client reading a document an older engine wrote negotiates `metadata_version`
before parsing it, exactly as it already negotiates the ProjectSpec and
component-manifest protocol tuples. `parse_generation_metadata` fails an
unsupported value closed as `unsupported-generation-metadata` with the four
report facts; there is no automatic downgrade.

## What this contract does not decide

Reserved for other owners:

- the merge algorithm, and the dry-run, cancellation and rollback policy — all
  client-side ([CF-16.02](https://github.com/Sandsy09/create-forge/issues/156));
  the on-disk location is `.forge/generation.json` by the default this contract
  and CF-16.02 agreed (ADR 0062), still written and committed by the client;
- ~~the concrete field names and manifest shape for the rename and
  regeneration-disposition declarations~~ — settled by
  [ADR 0062](adr/0062-generation-metadata-and-manifest-protocol-3.md) as the
  two-array `[[renames]]` / `[[regeneration]]` manifest protocol `3` shape;
- which questions become generation metadata versus a component option — the
  parity inventory's seven unrouted questions are
  [FT-15.03](https://github.com/Sandsy09/forge-template/issues/148)'s to
  assign;
- whether any protocol or package compatibility line must move, and the
  migration and rollback expectations
  ([FT-15.04](https://github.com/Sandsy09/forge-template/issues/149));
- the bounded issues the flagged parity rows still need, and how Stage 17
  scope reconciles
  ([FT-15.04](https://github.com/Sandsy09/forge-template/issues/149)).

FT-15.04 has since settled the last two:
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md)
([ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md))
classifies the cutover as `forge-template` `0.5.0` with component-manifest
protocol `3` — the rename and regeneration-disposition records above are new
`extra="forbid"` manifest fields, so they cannot ride protocol `2` — and
`metadata_version` moving from reserved to a published `1`, every other axis
unchanged. It also fixes the immutable-release and supported-`0.4.x`-window
rollback rules and closes the flagged parity rows by reference to FT-17.03.

## Validation

`tests/test_generation_provenance.py` runs under `uv run poe check` and drives
the shipped surface (`RenderedProject.metadata`, `to_json()`,
`parse_generation_metadata`, `verify_generation_metadata`) directly since
FT-17.01 / ADR 0062. `tests/generation_provenance_contract.py` keeps only what
a test must *not* read out of the engine — the documented field set, the
classification vocabulary, and the `copier.yml`-derived `_skip_if_exists` set;
its former shadow builder and validator are retired. The tests prove, against a
real `library` render:

- the document a render attaches verifies against a fresh render of its own
  embedded spec, and its canonical JSON round-trips through
  `parse_generation_metadata`;
- its `output` ownership and `regeneration` map equals `plan_generation()`'s,
  so the contract cannot over-claim;
- every recorded component id and version is a real `discover_components()`
  entry and `provider.version` is `get_engine_info().package_version`;
- every string leaf traces to the allowlist above;
- the field table here and `GenerationMetadata`'s fields are a bijection;
- both `EngineErrorCode` values are shipped, appear in this document, and every
  static and live negative fails with the documented code and an `operation` in
  `{parse, validate}`;
- `tests/fixtures/generation_metadata/example-library.json` is a fully live
  reference that parses, negotiates and verifies against a real render;
- classifying two real renders yields only the documented vocabulary, with a
  synthetic rename record exercising the `renamed` path the catalogue cannot
  reach yet (FT-17.04 ships the real classifier).
