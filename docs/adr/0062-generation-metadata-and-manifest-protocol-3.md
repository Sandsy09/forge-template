# 62. Generation metadata and manifest protocol 3

Date: 2026-09-10

## Status

Accepted

Implements the contracts accepted in
[ADR 0059](0059-generation-provenance-and-reproducible-updates.md) (generation
provenance) and [ADR 0061](0061-provider-compatibility-failure-and-release-gates.md)
(the cutover axis classification). It does not supersede either; it ships the
names they reserved. First implementation issue of
[FT-EPIC-17](https://github.com/Sandsy09/forge-template/issues/142).

## Context

[FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) is the first
Stage 17 provider-implementation issue. Stage 15 fixed the substance in three
merged living contracts and left FT-17.01 four concrete decisions
([cutover-compatibility-and-acceptance.md](../cutover-compatibility-and-acceptance.md)'s
scope-reconciliation row): the manifest-`3` field names and schema, the
`get_engine_info()` addition, the public metadata hand-off surface, and — from
create-forge [ADR 0041](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0041-engine-project-lifecycle-and-update-dispatch.md) —
adopting one documented default target path so both repositories name one
file.

Six deliberate tripwire tests were planted in `tests/test_cutover_gates.py`
and `tests/test_generation_provenance.py` that fail the moment these names
land, "forcing this contract and the implementation back into step". This ADR
records the choices made turning them over.

The stage exclusions forbid package publication (FT-17.06 owns it), CLI flags
or client configuration, engine-owned Git or destination writes, and any
remote component registry. The public facade may grow only additively.

## Decision

Confirmed with the maintainer before this record.

1. **Manifest protocol 3 uses two dedicated arrays.** `component.toml` at
   `manifest_version = 3` may declare `[[renames]]` (`from`, `to`, `since`)
   and `[[regeneration]]` (`target`, `disposition`). The two concerns are
   independently optional and version independently; a component that only
   needs a never-clobber disposition declares no `[[renames]]`, and the
   shipped catalogue declares neither. `from`/`to`/`target` are validated as
   normalised project-relative POSIX paths (the existing
   `relative_resource_path` rule); `since` is a canonical PEP 440 version; an
   identity move, a duplicate `from`, and a duplicate `target` are rejected.
   `RenameRecord`/`RegenerationRecord` stay internal to `component_manifest` —
   FT-17.04 exposes a rename-surfacing API when it needs one. Rejected: one
   `[[targets]]` table coupling both concerns (forces a row to exist for a
   rename even when the disposition is the default; `copier.yml`'s own
   `_skip_if_exists` is a bare list, unrelated to its migrations); reusing
   Copier's `_migrations` name (Copier's `_migrations` runs shell tasks, not
   path moves).

2. **Manifest protocol 3 is component-only; `foundation_version` stays `1`.**
   `generation-provenance.md` says "the owning component *or Foundation*
   declares" rename records, but ADR 0061's axis table requires the Foundation
   source protocol to stay `1`, and `FoundationSource` is `extra="forbid"` —
   adding the same fields there would change its TOML shape and need an ADR
   superseding that classification. So a Foundation-owned target is always
   `regeneration = "replace"` and is never renamed. Foundation ships in
   lockstep with the engine wheel, so a future Foundation rename can move
   `foundation_version` when a real need appears. Rejected: bumping
   `foundation_version` to `2` now (contradicts ADR 0061 decision "every other
   axis is unchanged — a requirement on the implementing stage" for a
   capability nothing uses yet); adding the fields while keeping
   `foundation_version` at `1` (repeats the exact "backward-compatible while
   the models forbid unknown keys" reasoning ADR 0061 rejected for manifest
   protocol `2`).

3. **The provenance model is a field on `RenderedProject`.**
   `render_project()` always returns `RenderedProject.metadata`, a
   `GenerationMetadata` assembled after `validate_rendered_project` passes, so
   the document can never drift from the bytes it describes. The field is
   `GenerationMetadata | None` with a `None` default only so a caller can
   still construct a bare `RenderedProject` to pass to the still-public
   `validate_rendered_project`; a real render never returns `None`. Digesting
   ~60 small files is one `sha256` pass. `PlannedFile` gains a `regeneration`
   field so the plan and the metadata agree (ADR 0059 decision 8). Rejected: a
   standalone `build_generation_provenance(project)` builder (lets a client
   hand back a document built from a different render than the one it staged);
   emitting the document as an ordinary `RenderedProject.files` entry (ADR
   0059 decision 1 rejected this — a rendered file cannot carry its own
   digest).

4. **`GenerationMetadata` is a new module, `generation_metadata.py`, not
   named `…Provenance`.** `ProjectSpec.provenance` is `SelectionProvenance`,
   and `generation-provenance.md` insists the two never merge; both
   repositories call the artefact the "generation-metadata document", its axis
   is `metadata_version`, and both error codes say `generation-metadata`. The
   module holds only the closed-world models and `to_json()` (sorted keys,
   two-space indent, trailing newline, `reproduction` omitted on an exact
   render). `parse_generation_metadata` and `verify_generation_metadata` live
   in `engine.py` because they need the catalogue and the renderer;
   `generation_metadata.py` imports neither. `spec` is held as an opaque
   `dict` in the model so a recorded protocol integer is negotiated before the
   spec is parsed; a client calls `parse_project_spec(metadata.spec)`.

5. **`metadata_version = 1` is published through `get_engine_info()`.**
   `EngineInfo` gains a `metadata_version: int` field — the ninth versioned
   axis, moved from "Reserved axis" into "The versioned axes" and "Current
   compatibility state" in `compatibility-policy.md`. `parse_generation_metadata`
   fails closed as `unsupported-generation-metadata` on an out-of-range
   `metadata_version` or a recorded protocol integer outside the engine's
   supported set, and `invalid-generation-metadata` on a malformed,
   internally-inconsistent, or digest-mismatched document. Both codes carry
   `operation` in `{parse, validate}`, never `render`, and diagnostics carry a
   field path and a fixed safe message only.

6. **`DEFAULT_GENERATION_METADATA_TARGET = ".forge/generation.json"` is a
   published constant.** ADR 0059 decision 1 commits FT-17.01 to "one
   documented default target", and create-forge ADR 0041 asks the provider to
   adopt `.forge/generation.json`. Exporting it as a name makes the cross-repo
   agreement executable rather than prose-only. The client still owns writing,
   reading, and committing the file — the constant is the agreed default, not
   an engine-performed filesystem operation. Rejected: leaving the filename a
   client-side string (leaves ADR 0041's explicit ask unanswered).

7. **`project.version` stays `0.4.1` and `main` stays untagged.** FT-17.06
   bumps to `0.5.0` and runs the protected release workflow, mirroring the
   FT-12.01 precedent ("the package stays `0.3.2` and untagged"). The
   `tests/test_cutover_gates.py` package-line tripwire stays green until then.

8. **The 379-line shadow implementation in
   `tests/generation_provenance_contract.py` is retired.** Its `MetadataError`,
   `build_metadata`, `validate_metadata` and plain-string `RESERVED_ERROR_CODES`
   are deleted; `tests/test_generation_provenance.py` now drives the shipped
   surface. What stays is only what a test must *not* read out of the engine:
   the documented field set, the classification vocabulary, and the
   `copier.yml`-derived `_skip_if_exists` set. `RenameRecord` and
   `classify_update` stay as a placeholder for FT-17.04's classifier.

## Consequences

- The public facade adds ten names — `GENERATION_METADATA_VERSION`,
  `DEFAULT_GENERATION_METADATA_TARGET`, `GenerationMetadata`,
  `ProviderIdentity`, `MetadataProtocols`, `SelectedComponent`, `OutputRecord`,
  `ReproductionRecord`, `parse_generation_metadata`,
  `verify_generation_metadata` — and renames or removes nothing.
  `EngineInfo.metadata_version`, `PlannedFile.regeneration` and
  `RenderedProject.metadata` are additive result fields. `EngineErrorCode`
  gains `invalid-generation-metadata` and `unsupported-generation-metadata`.
- `SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS` and
  `get_engine_info().component_manifest_protocols` become `(1, 2, 3)`; a
  protocol-`1` or protocol-`2` `component.toml` is accepted unchanged and the
  shipped five components stay `manifest_version = 2`.
- `compatibility-policy.md`, `component-manifests.md`,
  `cutover-compatibility-and-acceptance.md`, `generation-provenance.md` and
  `template-engine-api.md` move from "reserved" to shipped for these names;
  the compatibility state table is reviewed to 2026-09-10.
- Four `tests/test_cutover_gates.py` tripwires and the
  `tests/test_generation_provenance.py` reserved-code tripwire are inverted;
  the package-line and `_migrations` tripwires stay green. The composition
  golden fixtures gain `"regeneration": "replace"` on every `PlannedFile`;
  `tests/fixtures/generation_metadata/example-library.json` is regenerated as
  a fully live reference.
- FT-17.04 is unblocked: it inherits the manifest-`3` schema, the metadata
  model, and the `parse` / `verify` seam, and builds the reproduce-from-metadata
  render path and the rename-record surfacing and classifier on top.
- No generated content, no `copier.yml` change, no package version bump, no
  release. `main` stays on `0.4.1` and untagged until FT-17.06.
