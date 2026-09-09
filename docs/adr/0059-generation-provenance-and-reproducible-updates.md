# 59. Generation provenance and reproducible-update inputs

Date: 2026-09-09

## Status

Accepted

## Context

[ADR 0058](0058-inventory-default-copier-parity.md) (FT-15.01) inventoried
every default-Copier behaviour and tiered four rows `cutover-blocking`,
delegating them to
[FT-15.02](https://github.com/Sandsy09/forge-template/issues/147): the
`.copier-answers.yml` provenance state, the `_answers_file` /
`copier update` three-way merge, the `_skip_if_exists` never-clobber list, and
the absence of any engine-native update at all.

Direct Copier makes `copier update` possible by committing
`.copier-answers.yml` into every generated project — template ref, commit
hash, stored answers — then checking out the old template state, re-rendering
it, rendering the new state, and three-way merging the diff into the working
tree. The composition engine emits component content in memory and has none of
that machinery. `create-forge` today generates through the engine only behind
`--engine-preview`, and that preview offers no updates.

FT-15.02 is a `type:decision` issue. Its exclusions forbid any runtime
implementation, generated-content change, protocol increment, package version
bump or release, and specifically forbid preselecting metadata filenames or
merge algorithms without maintainer approval. Its review obligation
**FT-ROADMAP-01-AC-02** is shared with FT-17.01 (implement the metadata
schema and public hand-off) and FT-17.04 (implement reproducible rendering).

Eight design choices had to be made about the contract without pre-empting
those implementation issues or CF-16.02's client-side merge policy. Each was
confirmed with the maintainer before this record.

## Decision

Publish the contract as a living document,
[generation-provenance.md](../generation-provenance.md), and record the eight
choices here.

1. **The engine hands the client a typed, versioned provenance result, not a
   rendered file.** FT-17.01 adds a provenance model to the render result plus
   a canonical JSON serialisation and one documented default target; the
   client writes it. A rendered file cannot contain its own digest, would
   enter every golden fixture and byte-regression pin, and would make
   Foundation own a file whose content is not template-derived. The typed
   result avoids all three. Rejected: emitting it as an ordinary
   `RenderedProject.files` entry (Copier's shape); emitting both.

2. **The document records the effective spec, provider and component
   identities, the ownership map, and a digest per rendered target.** Verbatim
   effective `ProjectSpec`; `{ distribution, version }` for the exact
   installable; the protocol integers in force; `{ id, version }` per selected
   component; and `{ target, owner, digest, regeneration }` per rendered file.
   The digests make a local edit or a tampered target detectable without
   provisioning the historical engine — the precondition for AC-3's tamper
   handling. Rejected: omitting digests; recording identity only and
   re-deriving ownership every update.

3. **The client provisions the recorded provider release to reproduce the old
   render.** The client installs the exact `forge-template` version named in
   the metadata into an isolated environment and calls the ordinary public
   `render_project()` with the recorded spec. The provider contributes a
   documented **reproducibility guarantee** — same release plus same effective
   spec yields byte-identical output — and no historical-render API, no
   bundled past content trees. This mirrors `copier update` checking out the
   old tag. Rejected: the current engine reconstructing historical output
   (unbounded package growth); the generated project caching its own old
   rendered bytes (committed bytes that drift and can be tampered with).

4. **Generation metadata is a ninth versioned axis with its own integer.**
   `metadata_version`, added to
   [compatibility-policy.md](../compatibility-policy.md) as a reserved axis and
   published by FT-17.01 through `get_engine_info()` as a backward-compatible
   addition, so a client reading a document an older engine wrote can
   negotiate before parsing it — the case the policy's "independently
   pinnable" test is about. Rejected: reusing `protocol_version` (couples two
   schemas that change for unrelated reasons); leaving it unpublished like the
   option-schema and Foundation source protocols (no negotiation surface for a
   file an older engine wrote).

5. **Renamed targets are represented by owner-declared rename records.** The
   owning component or Foundation declares `{ from, to, since }` pairs
   versioned with that owner; the provider surfaces the records that apply
   between the recorded and current component versions, and the client applies
   each move before diffing. This is the engine's `_migrations`, and the only
   option that preserves a user's local edits across a path change
   ([invariant 3](../invariants.md#3-moving-or-deleting-files-under-template-breaks-updates)).
   Rejected: surfacing a move as an unrelated delete-plus-add (loses the edit
   every time); inferring renames by content similarity (non-deterministic,
   can pair the wrong files).

6. **A missing historical provider fails closed, with an opt-in degraded
   update.** The default is a structured failure carrying
   compatibility-policy.md's four report facts, before any render or write. A
   client may offer an explicit, user-chosen two-way update — new render
   against the working tree — which loses the ability to distinguish a local
   edit from an old provider default and is therefore never automatic. The
   refreshed metadata must record `reproduction.mode = "degraded"` so the next
   update knows the merge base was lost. Rejected: always failing closed with
   no path forward (a yanked release permanently strands its projects);
   automatic silent two-way fallback (hides the lost merge base from the
   user).

7. **Metadata failures use two reserved `EngineErrorCode` values, added by
   FT-17.01.** `invalid-generation-metadata` for malformed, inconsistent or
   digest-mismatched documents; `unsupported-generation-metadata` for an
   out-of-range `metadata_version` or protocol integer.
   `ForgeEngineError.operation` stays `parse` or `validate`, never `render`,
   so a corrupt provenance file is always distinguishable from a malformed
   generation request. Rejected: reusing `INVALID_PROJECT_SPEC` /
   `GENERATION_PLAN_FAILED` (a corrupt file becomes indistinguishable from a
   bad request); keeping all metadata parsing client-side (leaves FT-17.01's
   stated obligation to test malformed and unsupported metadata without a
   provider owner).

8. **Regeneration-unsafe targets are an owner-declared per-target
   disposition.** The owning manifest marks a target `skip-if-exists` — today
   `CHANGELOG.md` and `.env`, matching `copier.yml`'s `_skip_if_exists`; the
   engine records the flag in the plan and the metadata, and the client
   applies the skip. The rule travels with whoever owns the content, so a
   changelog or documentation owner added later carries its own. Rejected: a
   fixed engine-level list (any new such file needs an engine change); a
   purely client-owned list (every client re-invents it and they can
   disagree).

The contract adds no `EngineErrorCode` value, public name, protocol integer,
component or package version, generated content, or `copier.yml` question.
`SelectionProvenance` is unchanged — generation provenance records what was
produced and embeds the spec that already carries the selection provenance;
the two do not merge, and no `ProjectSpec` field is added. The names the
contract reserves are FT-17.01's and FT-17.04's to implement.

`tests/test_generation_provenance.py`, following
[ADR 0040](0040-organisation-policy-reference-fixture.md)'s precedent, pins the
contract through a test-only reference module
`tests/generation_provenance_contract.py` that assembles and validates a
metadata document from the public facade only and raises its own
`MetadataError`, never `ForgeEngineError`.

## Consequences

- FT-17.01 and FT-17.04 inherit a decided contract: the result-field shape,
  the metadata content, the reproducibility guarantee, the negotiation axis,
  the two reserved error codes, and the rename and regeneration declarations
  they must give concrete manifest field names.
- [compatibility-policy.md](../compatibility-policy.md) gains a reserved ninth
  axis. It is not client-visible and does not appear in the "Current
  compatibility state" table until FT-17.01 ships it. This record extends
  [ADR 0041](0041-forge-blueprint-compatibility-policy.md)'s axis set; a
  semantic change to that policy's range, deprecation or negotiation rules
  still requires an ADR superseding 0041.
- The `cutover-blocking` parity rows for `.copier-answers.yml`,
  `_answers_file` and `_skip_if_exists` now have a contract to implement
  against; `tests/test_parity_inventory.py` still classifies all four as gaps,
  because a real `library` render still produces none of them.
- CF-16.02's client-side merge, dry-run, cancellation and rollback policy can
  proceed against this document; FT-15.04's compatibility classification
  gains a concrete new axis to rule on.
- `tests/test_generation_provenance.py` fails deliberately when FT-17.01 adds
  `invalid-generation-metadata` or `unsupported-generation-metadata` to the
  shipped enum — a forcing function that keeps this contract and the
  implementation in step.
- No template, Copier answer, Foundation or component resource, manifest,
  engine module, public signature, `EngineErrorCode`, protocol integer,
  component version, golden digest, package version, tag, or release changes.
