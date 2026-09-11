# 65. Implement reproducible rendering for updates

Date: 2026-09-11

## Status

Accepted

Implements the update half of the contract fixed in
[ADR 0059](0059-generation-provenance-and-reproducible-updates.md) (generation
provenance and reproducible-update inputs) and
[ADR 0062](0062-generation-metadata-and-manifest-protocol-3.md) (generation
metadata and manifest protocol 3), which built the document and its
`parse` / `verify` surface but deliberately left the classifier and
rename-surfacing as a placeholder for this issue. It does not supersede either
record; it ships the reproducible-render path and the update inputs a client
applies. Fourth implementation issue of
[FT-EPIC-17](https://github.com/Sandsy09/forge-template/issues/142), after
[ADR 0062](0062-generation-metadata-and-manifest-protocol-3.md) (FT-17.01),
[ADR 0063](0063-implement-the-github-platform.md) (FT-17.02), and
[ADR 0064](0064-implement-approved-generated-content-parity.md) (FT-17.03).

## Context

[FT-17.04](https://github.com/Sandsy09/forge-template/issues/153) is the
fourth implementation issue of Stage 17. FT-17.01 shipped the provenance
document — a client can persist what was produced — but could not *use* it:
two `cutover-blocking` rows in
[engine-default-parity.md](../engine-default-parity.md) were still `gap`
(`_skip_if_exists`, `_answers_file`), the "No engine-native update"
cross-cutting row was still open, and ADR 0062 decision 8 left
`RenameRecord`/`classify_update` as an explicit placeholder in
`tests/generation_provenance_contract.py` "for the update classifier
FT-17.04 ships".

[generation-provenance.md](../generation-provenance.md) fixed the shape: an
update is a diff of three file sets (old, new, working tree) classified into
`unchanged` / `added` / `removed` / `changed` / `renamed`; the provider
supplies the old and new sides plus ownership and rename data, and the client
computes the working-tree comparison and performs the merge
(FT-ROADMAP-01-EX-01). It left the entry-point shape, the parse-strictness
interaction with FT-17.01's exact reproduce-path version check, the
unavailable-provider error code (with `EngineErrorCode` frozen at nine values
since ADR 0061), and the depth of the reproduction proof unresolved — each
confirmed with the maintainer before planning.

## Decision

Ship one `plan_update()` entry point and the result models it returns. Record
the four confirmed calls here.

1. **One `plan_update()` entry point.** Mirrors `plan_generation` /
   `render_project`: one call, one immutable result (`UpdatePlan`) carrying
   classified targets, applied renames, and the reproduction record. The
   classifier and rename surfacing are public — create-forge consumes only the
   `forge_template` facade — so `_FROZEN_PUBLIC_API` grows by four additive
   names (`plan_update`, `UpdatePlan`, `UpdateTarget`, `AppliedRename`).
   Rejected: two loose functions (`classify_update` / `renames_between`),
   which leaves the client to wire them together itself; keeping the surface
   internal, which leaves acceptance criterion 1 ("provide the approved
   new-render inputs for client update application") unmet.

2. **`parse_generation_metadata` is untouched; `plan_update` reads leniently.**
   FT-17.01's exact recorded-component-version equality is correct for the
   *reproduce* path, where the recorded release and the running engine must be
   the same release — nothing about that function's behaviour changes.
   `plan_update` runs the same structural check and protocol negotiation
   (`_validate_recorded_selection`, refactored to take
   `require_version_match: bool = True` rather than duplicated) but calls it
   with `require_version_match=False`: an update is by definition an old
   document read on a newer engine, so a drifted component version is expected
   input, not a validation failure. No shipped signature moves.

3. **The unavailable historical provider reuses
   `unsupported-generation-metadata`.** ADR 0061 froze `EngineErrorCode` at
   nine values ("nothing else may join it in the cutover"), so no new code was
   available. `unsupported-generation-metadata` already carries the
   compatibility policy's unsupported-version report shape, and the contract
   says the failure "names the axis (`provider`)" — a deliberate widening of
   that code's documented meaning to cover a recorded provider release the
   client could not supply as reproduced input, not only an out-of-range
   schema or protocol integer. `plan_update` raises it when `old` is empty
   against a non-empty recorded `output`, naming the `provider` axis, the
   recorded version, and both remedies in one message: provision that release
   and reproduce it, or record an explicit degraded two-way update. Rejected:
   reusing `invalid-generation-metadata` (loses the axis/unsupported-version
   framing); reporting without raising (moves the "fails closed" guarantee
   from the provider to client discretion).

4. **Reproduction is proven same-release, across all three archetypes.** Fast
   and offline, inside `poe check`: render → attach metadata → re-render from
   the embedded spec → byte-identical, for `library`, `cli` and
   `data-science` (`tests/test_generation_provenance.py`'s
   `test_reproduction_is_byte_identical_across_archetypes`; previously only
   `library` was covered, via the checked-in fixture). The cross-release half
   of the guarantee — a real historical `forge-template` release, provisioned
   over the network — stays the client's step (CF-16.02), proven against the
   real released artefact at FT-17.05 / FT-18.01. Rejected: a real
   cross-release install in this repository's `poe check` (network-bound,
   slow, and this repository has no second release to install against until
   `0.5.0` itself ships); a local two-release simulation against an unpublished
   wheel (proves determinism, not cross-release stability, and would overstate
   the evidence).

### What ships

`plan_update(recorded, *, old, new) -> UpdatePlan` in `engine.py`. `recorded`
is the generation-metadata document a client persisted (the same
`GenerationMetadataPayload` union `parse_generation_metadata` accepts); `old`
is the bytes the client obtained by provisioning `recorded.provider.version`
and calling `render_project` there; `new` is a fresh
`render_project(effective_spec)` result on this release. Six steps, all
validation-first and all before any classification:

1. Read `recorded` leniently (decision 2).
2. Fail closed on an unavailable historical provider (decision 3).
3. Check the merge base is genuine: every recorded `output` digest must match
   the supplied `old` bytes, reusing `verify_generation_metadata`'s digest
   comparison; a mismatch is `invalid-generation-metadata` / `validate`.
4. Surface applicable renames: for each component recorded in `document` that
   is still selected in `new`, keep the installed manifest's `[[renames]]`
   records where `recorded < since <= installed` (`packaging.version.Version`
   comparison), restated as public `AppliedRename` values. A component the new
   selection dropped contributes none.
5. Classify every target into `unchanged` / `added` / `removed` / `changed` /
   `renamed`, applying renames first so a moved-and-edited file is reported
   once, under its new target — the old target never also appears as
   `removed`. This is the ADR 0062 placeholder's exact semantics, promoted
   from `tests/generation_provenance_contract.py` into `engine.py`.
6. Return `UpdatePlan` with `reproduction=ReproductionRecord(mode="exact")`.
   `owner` / `regeneration` on each `UpdateTarget` come from the *new* plan for
   a surviving target and from the recorded document for a `removed` one, so
   the result never claims ownership the engine cannot resolve.

The **degraded two-way update stays entirely client-side** — "skip the old
render entirely and compare the new render against the working tree" is a
filesystem diff the provider never performs (FT-ROADMAP-01-EX-01). The
provider's obligations are the two halves it already owns: naming degraded as
a remedy in step 2's message, and accepting/round-tripping
`reproduction.mode = "degraded"` on a refreshed document — already shipped by
FT-17.01 (`GenerationMetadata` is frozen; a client sets it with
`model_copy`). No new engine surface was needed for that half.

No production component declares a `[[renames]]` record — the catalogue has
no real path move, and inventing one would fabricate provenance. The
`renamed` path is exercised by a synthetic fixture catalogue,
`tests/fixtures/update_renames/renaming-widget/`, overlaid through the
existing private `_CATALOGUE_ROOT_OVERRIDE` seam (the pattern
`tests/test_capability_composition.py` established for `requires` /
`conflicts`), with three `[[renames]]` records covering the three window
edges (inside, at-or-below the recorded version, above the installed
version) in one fixture.

### Recorded narrowings

- `unsupported-generation-metadata`'s documented meaning widens to include an
  unobtainable recorded `provider.version`, not only an out-of-range schema or
  protocol integer (decision 3).
- The reproduction acceptance row is evidenced same-release only inside this
  repository's `poe check`; the cross-release half is FT-17.05 / FT-18.01's to
  evidence against a real published release (decision 4).

## Consequences

- The public facade gains four names: `plan_update`, `UpdatePlan`,
  `UpdateTarget`, `AppliedRename`. `_FROZEN_PUBLIC_API` in
  `tests/test_cutover_gates.py` is updated; nothing is renamed or removed.
- `EngineErrorCode` is unchanged — still the seven original values plus the
  two FT-17.01 generation-metadata codes.
  `tests/test_cutover_gates.py::test_generation_metadata_error_codes_are_shipped`
  stays green with no edit.
- The `_skip_if_exists` and `_answers_file` rows in
  [engine-default-parity.md](../engine-default-parity.md) flip `gap` →
  `shipped`; the "No engine-native update" cross-cutting bullet closes. Every
  provider-owned parity row is now `shipped`.
- `tests/generation_provenance_contract.py`'s placeholder `RenameRecord`
  dataclass and `classify_update` reference implementation are retired;
  `tests/test_generation_provenance.py` drives `forge_template.plan_update`
  directly.
- No component, Foundation, `copier.yml`, or `template/**` change; no
  component version moves. `main` stays `0.4.1` and untagged. FT-17.06
  releases `0.5.0`.
- `tests/fixtures/archetype_regression/digests.json` and the composition
  golden fixtures are untouched — no content changed, so no digest moved.
