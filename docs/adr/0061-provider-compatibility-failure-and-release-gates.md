# 61. Provider compatibility, failure and release gates

Date: 2026-09-09

## Status

Accepted

Classifies one compatibility-line transition against the rules in
[ADR 0041](0041-forge-blueprint-compatibility-policy.md), which continues to
govern how every axis moves and is not superseded. Closes
[FT-EPIC-15](https://github.com/Sandsy09/forge-template/issues/141).

## Context

[FT-15.04](https://github.com/Sandsy09/forge-template/issues/149) is the last
child of the Stage 15 provider-contract epic. Its three predecessors each
deferred the same two questions to it in writing: which protocol or package
compatibility lines the engine-default cutover moves with what
migration/rollback expectations
([ADR 0058](0058-inventory-default-copier-parity.md),
[ADR 0059](0059-generation-provenance-and-reproducible-updates.md)), and how
the `needs a bounded issue` parity rows reconcile with Stage 17's filed
children ([ADR 0060](0060-platform-composition-and-generated-tooling.md)).

Nine rows in [engine-default-parity.md](../engine-default-parity.md) still
carry the literal `needs a bounded issue` marker. No document says what the
cutover release is, whether any protocol integer moves, or what the provider
commits to when a published release turns out to be defective. Until this
contract exists, create-forge Stage 16 cannot start —
[CF-16.01](https://github.com/Sandsy09/create-forge/issues/155) and
[CF-EPIC-16](https://github.com/Sandsy09/create-forge/issues/152) are blocked
on FT-15.04 and on nothing else.

The review obligations are **FT-ROADMAP-01-AC-04** (failure and compatibility
contracts preserve validation-before-render and never require the client to
inspect a component resource, shared with
[FT-17.05](https://github.com/Sandsy09/forge-template/issues/154)),
**FT-ROADMAP-01-AC-05** (the ADR states whether any line moves and defines
migration/rollback, owned solely here), **FT-ROADMAP-01-EX-02** (no
engine-default switch here) and **FT-ROADMAP-01-EX-04** (no remote registry or
plugin execution).

The stage is contract-only. Its exclusions forbid any runtime implementation,
generated-content change, protocol increment, package version bump or release,
and forbid preselecting metadata filenames, merge algorithms, Streamlit layout
or deprecation dates without an accepted decision.
[data-science-compatibility-and-acceptance.md](../data-science-compatibility-and-acceptance.md)
(FT-10.04 / [ADR 0048](0048-data-science-compatibility-and-acceptance.md)) is
the direct precedent for the shape: an axis table, an executable matrix, and
named release gates.

Seven choices had to be made and were confirmed with the maintainer before
planning.

## Decision

Publish the classification as a living contract,
[cutover-compatibility-and-acceptance.md](../cutover-compatibility-and-acceptance.md),
and record the choices here.

1. **The cutover publishes `forge-template` `0.5.0`** — a new minor
   compatibility line. Released `create-forge` declares
   `forge-template>=0.4.1,<0.5`, so it cannot drift into `0.5.0` and adopts
   deliberately at [CF-18.01](https://github.com/Sandsy09/create-forge/issues/158),
   the same opt-in step the `0.3.2` → `0.4.0` Data Science line used.
   Rejected: `1.0.0` (declares the engine stable and switches the
   compatible-range rule from minor-scoped to major-scoped for every future
   client, before Stage 18 has validated the integrated cutover — `1.0.0`
   stays a later decision); a `0.5.0`-now-`1.0.0`-later promise (adds a
   commitment this roadmap files no child to keep).

2. **Component manifest protocol moves `2` → `3`.** The rename and
   regeneration-disposition records FT-15.02 reserved
   ([generation-provenance.md](../generation-provenance.md)) are new manifest
   fields, and `ComponentManifest` is `extra="forbid"` — so a protocol-`2`
   manifest carrying them is invalid by definition. Keeping them on `2` would
   make one integer name two incompatible schemas.
   [FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) lands the
   fields at `3`; the engine publishes
   `component_manifest_protocols = (1, 2, 3)` and accepts protocol-`1` and
   protocol-`2` manifests unchanged. Rejected: staying at `2` and treating the
   fields as a backward-compatible addition (the "backward-compatible" reading
   is false while the models forbid unknown keys); deferring the integer
   entirely to FT-17.01 (leaves AC-05's "states whether any protocol line must
   move" half-answered).

3. **The direct-Copier `template/` + `copier.yml` path is retained and not
   deprecated.** Stage 17 changes nothing under `template/` or `copier.yml`,
   so `copier update` keeps working for every project already scaffolded from
   a tag, [invariants](../invariants.md) 3 and 6 are untouched, no `_migrations`
   block is required by this cutover, and no deprecation clock starts.
   Rejected: deprecating it at `0.5.0` (starts the 90-day-plus-one-release
   window and commits to a removal this roadmap files no child for); retiring
   it in the cutover (needs a `_migrations` block over every moved template
   path, a breaking line, and a legacy-project update route Stage 18 does not
   own).

4. **The nine `needs a bounded issue` rows close by reference to
   [FT-17.03](https://github.com/Sandsy09/forge-template/issues/152).**
   FT-15.03 resolved every flagged row to the `documentation` capability or
   the `dependabot` / `renovate` pair — all capabilities, all inside FT-17.03's
   "each assigned provider-content parity row" acceptance criterion. Their
   owner cells in `engine-default-parity.md` move from
   `FT-15.03: needs a bounded issue` to `FT-15.03 → FT-17.03`; the two stale
   validation cells that assert a new issue is needed are corrected. **No new
   GitHub issue is filed**, so the hash-pinned `docs/roadmap-v3/**` mirror
   stays byte-identical and `tests/test_parity_inventory.py`'s
   no-invented-numbers check still passes. This is FT-15.04's explicit mandate:
   the marker's own definition says "FT-15.04 must split one", and the split
   here is recognising the filed child that already fits. Rejected: routing
   the `dependabot`/`renovate` rows to FT-17.02 instead (its scope is
   platforms, not capabilities); filing new issues (breaks the frozen mirror
   and forces a matching create-forge PR for no scope gain).

5. **Provider release rollback is immutable-forward with a supported `0.4.x`
   window and an executable regression row.** A published release is never
   mutated: a `0.5.0` defect is corrected forward as `0.5.1` and the defective
   version is yanked. The `0.4.x` line stays installable and supported for the
   compatibility policy's window — at least 90 days and one further tagged
   release past the cutover — so a client can pin back and keep generating
   while the fix ships. The acceptance matrix carries a row proving a
   `0.4.1`-pinned client still resolves, installs and generates after `0.5.0`
   publishes. Rolling back a *user's project* is
   [CF-18.05](https://github.com/Sandsy09/create-forge/issues/162)'s. Rejected:
   immutable-forward only, with no stated `0.4.x` window or regression proof
   (leaves a client with no supported fallback during a defect); a
   pre-publication downgrade-rehearsal gate on FT-17.06 (adds a gate to a
   release child whose scope this decision does not own).

6. **The pin is a new derived, tripwired test module,
   `tests/test_cutover_gates.py`**, following the three predecessor pins.
   Every "Current"/"Unchanged" claim is checked against the live engine; each
   classified target is tripwired so the module fails deliberately the moment
   Stage 17 moves the line. Rejected: a document-consistency-only check
   (asserts nothing against the real engine, never fires); extending
   `tests/test_compatibility_policy.py` (mixes a living policy pin with a
   stage-scoped, deliberately-expiring one).

7. **Acceptance-matrix ownership is bidirectional over provider children.**
   Every matrix row names a real filed issue, and every filed provider child
   in Stages 17–18 (`#150`–`#156`) owns at least one row — so no row is
   ownerless and no filed child is left without acceptance scope. The check
   reuses `tests/test_parity_inventory.py`'s filing-manifest cross-reference.
   Rejected: row-to-issue only (a Stage 17 child could end up with no
   acceptance row unnoticed); extending the check across create-forge children
   (asserts coverage over issues this repository cannot close).

The cutover therefore moves exactly three axes — the package version to
`0.5.0`, the component-manifest protocol to `(1, 2, 3)`, and generation
metadata from reserved to published `metadata_version = 1`. Every other axis,
and the entire public facade bar three additive names, is unchanged, and that
is a requirement on Stage 17, not a prediction.

This decision changes no runtime code, no generated content, no protocol
integer, no component or package version, no `copier.yml`, and no
`foundation.toml`. It adds one living contract, this record, one test module,
and the wiring that links them, and it rewrites nine owner cells and two
validation cells in `engine-default-parity.md` under FT-15.04's explicit
reconciliation mandate.

## Consequences

- `FT-EPIC-15` closes with all four children complete. Its three acceptance
  criteria are evidenced in the closing comment, not by editing the frozen
  issue body: every mapped review criterion
  ([TRACEABILITY.md](../roadmap-v3/TRACEABILITY.md)) is owned and closed, and
  no release is claimed — `main` stays untagged and the package stays `0.4.1`.
- Stage 17 inherits a fully bounded scope. Every provider child has a
  "fixed by Stage 15 / still owned" row in the contract, and every
  provider-owned parity gap now cites a filed child — FT-15.04 files no new
  issue.
- `create-forge` Stage 16 unblocks. CF-16.01 and CF-EPIC-16 lose their only
  blocker; `FT-EPIC-17` stays blocked on CF-16.03, unchanged.
- FT-17.01 must move `component_manifest_protocols` to `(1, 2, 3)` when it
  adds the manifest-`3` fields; `tests/test_cutover_gates.py` and
  `tests/test_generation_provenance.py` both fail until it does, keeping the
  contract and the implementation in step.
- The `0.4.x` line acquires an explicit support obligation through the cutover
  window: FT-17.06 may not yank `0.4.1` when it publishes `0.5.0`, and
  FT-18.01 carries a row proving the pinned-back path still works.
- `engine-default-parity.md`'s nine reconciled rows change owner cell only;
  their `status`, `disposition` and `tier` are untouched, those surfaces stay
  `gap` until FT-17.03 ships them, and `tests/test_parity_inventory.py` still
  pins every row against a real render.
- No template, Copier answer, component resource, engine module, dependency,
  golden digest, `foundation.toml`, tag, or release changes.
