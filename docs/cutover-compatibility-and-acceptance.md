# Cutover compatibility, failure and acceptance

This document classifies which versioned provider surfaces the engine-default
cutover moves, defines the failure and reproducibility guarantees the provider
commits to, and fixes the executable acceptance matrix and cross-repository
release gates that admit the cutover release. It is the canonical living
contract accepted by
[ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md) for
[FT-15.04](https://github.com/Sandsy09/forge-template/issues/149), the last
child of
[FT-EPIC-15](https://github.com/Sandsy09/forge-template/issues/141).

It is the direct analogue, one roadmap later, of
[data-science-compatibility-and-acceptance.md](data-science-compatibility-and-acceptance.md)
(FT-10.04): an axis-classification table, an executable matrix with a command
and a repository owner per row, and named release gates with entry and exit
criteria. This contract reuses that shape rather than inventing one.

This contract bumps no version and publishes no package. It classifies the
increments [Stage 17](https://github.com/Sandsy09/forge-template/issues/142)
will perform; it does not perform them. Its review obligations are
**FT-ROADMAP-01-AC-04** (failure and compatibility contracts preserve
validation-before-render and never require `create-forge` to inspect a
component resource — shared with
[FT-17.05](https://github.com/Sandsy09/forge-template/issues/154)),
**FT-ROADMAP-01-AC-05** (this contract and its ADR state whether any protocol
or package line moves and define migration and rollback — owned solely here),
**FT-ROADMAP-01-EX-02** (no engine-default switch here) and
**FT-ROADMAP-01-EX-04** (no remote component registry or plugin execution).

## Why this exists

The three predecessor contracts each deferred the same two questions to this
issue, in writing:

- [engine-default-parity.md](engine-default-parity.md) — *"which protocol or
  package compatibility lines move, and the migration/rollback expectations"*
  and *"the bounded issues the `needs a bounded issue` rows require, and how
  they reconcile with Stage 17's filed children"*;
- [generation-provenance.md](generation-provenance.md) — the same two, verbatim;
- [platform-and-tooling-parity.md](platform-and-tooling-parity.md) — the same
  two, plus whether the nine flagged parity rows can be closed by reference.

Nine parity rows still carry a literal `needs a bounded issue` marker, no
document says what the cutover release is or whether any protocol integer
moves, and no document says what happens when a published provider release
turns out to be defective. Until this contract exists, create-forge Stage 16
cannot start:
[CF-16.01](https://github.com/Sandsy09/create-forge/issues/155) and
[CF-EPIC-16](https://github.com/Sandsy09/create-forge/issues/152) are both
blocked on FT-15.04 and on nothing else.

## Scope and boundary

This contract classifies and gates. It decides no runtime behaviour,
introduces no protocol increment, changes no generated content, and bumps no
version. The provider renders component content in memory and negotiates
protocol compatibility; per **FT-ROADMAP-01-EX-01** it never stages, writes to
a destination, spawns a process, initialises Git, installs or runs a hook, or
presents an error to a person. Each concrete row below restates that boundary
rather than asserting it once in the abstract.

The [compatibility policy](compatibility-policy.md)
([ADR 0041](adr/0041-forge-blueprint-compatibility-policy.md)) defines the
rules every axis moves under. This contract classifies one line's transition
against those rules; it does not change them, and it does not supersede
ADR 0041.

## Every versioned axis is classified

The compatibility policy governs eight independently versioned surfaces, the
extension-point inventory, and — reserved by FT-15.02 — a ninth axis,
generation metadata. The cutover moves exactly three of them: the package
version, the component-manifest protocol, and the published state of
generation metadata. Every other axis is unchanged, and that is a requirement
on the implementing stage, not a prediction. FT-17.01 / ADR 0062 has since
moved the component-manifest protocol to `(1, 2, 3)` and published
`metadata_version = 1`; FT-17.02 / ADR 0063 has since published the `github`
platform (`1.0.0`) and grown the Foundation inventory 11 → 14; FT-17.03 / ADR
0064 has since published the eight tooling capabilities (`1.0.0` each), the two
`[dependency-groups]` Foundation points and `api-reference` (inventory 14 →
16), all additive, with `library` / `cli` / `data-science` content and
versions unchanged. **FT-17.06 has since released `0.5.0`** — the cutover
line this contract fixed. The "Current" column below is the live engine
state.

| Axis | Current | Cutover line | Change class |
| --- | --- | --- | --- |
| `forge-template` package | `0.5.0` | `0.5.0` | **Moved (FT-17.06)** — new minor compatibility line |
| ProjectSpec protocol | `1` | `1` | Unchanged — every unrouted question became a selection or a component option (FT-15.03), so no request-schema field is added |
| Component manifest protocol | `1`, `2`, `3` | `1`, `2`, `3` | **Moved (FT-17.01)** — the owner-declared rename and regeneration-disposition records are manifest protocol `3` fields, and the manifest models forbid unknown keys, so they could not ride protocol `2`; protocol-`1` and protocol-`2` manifests are accepted unchanged |
| Option-schema protocol | `1`, `2` | `1`, `2` | Unchanged — `coverage`'s `fail_under` is an `integer` option with a `default`, already expressible at protocol `2` |
| Foundation source protocol | `1` | `1` | Unchanged — the new Foundation extension points are content, not a change to the source's TOML shape, exactly as FT-11.01 / ADR 0049 added three points without moving `foundation_version`; FT-17.02 / ADR 0063 added three more and FT-17.03 / ADR 0064 two more, the same way; the rename and regeneration records are component-only (ADR 0062) |
| Organisation-policy protocol | `1` | `1` | Unchanged (documentation-only by design) |
| Extension-point inventory | 16 Foundation points, plus `ci-jobs` / `ci-steps` on `github` and `api-reference` on `documentation` | 16 Foundation points, plus `ci-jobs` / `ci-steps` / `api-reference` on component content | Additive only; no rename, no removal. FT-17.02 / ADR 0063 took Foundation 11 → 14 and published `ci-jobs` / `ci-steps`; FT-17.03 / ADR 0064 published the two `[dependency-groups]` points (14 → 16) and `api-reference` |
| Generation metadata (`metadata_version`) | `1` | `1` | **Published (FT-17.01)** through `get_engine_info().metadata_version`; was reserved and unpublished at `0.4.1` |
| `library` component | `1.0.1` | `1.0.1` | Unchanged — FT-17.03 / ADR 0064 left the archetypes untouched (no `ci-jobs` fill; the Copier scaffold has no publish job) |
| `cli` component | `1.0.1` | `1.0.1` | Unchanged — as `library` |
| `data-science` component | `1.0.0` | `1.0.0` | Unchanged — as `library` |
| `jupyter` component | `1.0.0` | `1.0.0` | Unchanged unless it fills a new point |
| `scientific-python` component | `1.0.0` | `1.0.0` | Unchanged unless it fills a new point |
| `github` component | `1.0.0` | `1.0.0` | **New (FT-17.02)** — the first shipped `kind = "platform"` component |
| `changelog` component | `1.0.0` | `1.0.0` | **New (FT-17.03)** — first shipped `manifest_version = 3` component |
| `coverage` component | `1.0.0` | `1.0.0` | **New (FT-17.03)** |
| `dependabot` component | `1.0.0` | `1.0.0` | **New (FT-17.03)** |
| `documentation` component | `1.0.0` | `1.0.0` | **New (FT-17.03)** — publishes `api-reference` |
| `dotenv-example` component | `1.0.0` | `1.0.0` | **New (FT-17.03)** |
| `pre-commit` component | `1.0.1` | `1.0.1` | **New (FT-17.03)**, patched (FT-17.05) — `check-added-large-files` excludes `uv.lock`, the first false positive FT-17.05's full-composition build actually ran the hook against |
| `pyright` component | `1.0.0` | `1.0.0` | **New (FT-17.03)** |
| `renovate` component | `1.0.0` | `1.0.0` | **New (FT-17.03)** |

The rule that bounds the conditional component rows: an existing component
moves its version only if the cutover changes its owned content or one of its
extension-point contributions — a minor bump for an additive fill, per the
compatibility policy's component-version rules. FT-17.02 and FT-17.03 fixed
which components move: **none of the archetypes**.
[FT-17.03](https://github.com/Sandsy09/forge-template/issues/152) / ADR 0064
left `library` / `cli` / `data-science` untouched — the `ci-jobs` point is
filled only by capabilities (`documentation`, `pyright`) and `api-reference`
is self-filled by `documentation`, so no archetype gains content. An archetype
`ci-jobs` fill and the matching `1.1.0` move are a later child.

### Why `0.5.0` and not `1.0.0`

Below `1.0`, a supported dependency range stays inside one minor line
([compatibility-policy.md](compatibility-policy.md#compatible-ranges)).
Released `create-forge` declares `forge-template>=0.4.1,<0.5`, so it cannot
drift into `0.5.0` and must widen its bound deliberately at
[CF-18.01](https://github.com/Sandsy09/create-forge/issues/158) — the same
opt-in step the `0.3.2` → `0.4.0` Data Science line used. `1.0.0` would
declare the engine stable and change the compatible-range rule from
minor-scoped to major-scoped for every future client, before
[Stage 18](https://github.com/Sandsy09/forge-template/issues/143) has
validated the integrated cutover. `1.0.0` is therefore **not** promised by
this contract; it remains a later decision.

### Why manifest protocol `3`

`ComponentManifest` and its nested models are strict: unknown fields fail
validation ([component-manifests.md](component-manifests.md#authoring-and-schema-source),
`model_config = ConfigDict(extra="forbid", …)`). A protocol-`2` manifest that
carried an owner-declared rename record would therefore be *invalid by
definition* today. Keeping the new fields on `2` would make one protocol
integer name two incompatible schemas — the exact thing a protocol integer
exists to prevent. So the rename and regeneration-disposition records FT-15.02
reserved land at manifest protocol `3`, which
[FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) /
[ADR 0062](adr/0062-generation-metadata-and-manifest-protocol-3.md)
implemented as the two-array `[[renames]]` / `[[regeneration]]` shape; the
engine now publishes `component_manifest_protocols = (1, 2, 3)` and accepts
protocol-`1` and protocol-`2` manifests unchanged. This is a
backward-compatible protocol addition under the compatibility policy: the
integer moves because a new schema shape exists, not because an old one broke.
Foundation declares neither record — `foundation_version` stays `1` — so a
Foundation-owned target is always `replace` and never renamed (ADR 0062).

## The public facade is additive only

Every name exported from `forge_template` keeps its signature and its result
fields through the cutover. Nothing is renamed, removed, or narrowed, and no
deprecation is opened. The cutover *adds* — FT-17.01 / ADR 0062 and FT-17.04 /
ADR 0065 have landed all of these:

- `metadata_version` on `EngineInfo`;
- the two `EngineErrorCode` values FT-15.02 reserved,
  `invalid-generation-metadata` and `unsupported-generation-metadata`, each
  carrying `operation` only in `{parse, validate}` — FT-17.04 / ADR 0065
  additionally uses `unsupported-generation-metadata` to report an
  unavailable historical provider (a deliberate widening of its documented
  meaning; no new code was added, as `EngineErrorCode` stayed frozen at nine
  values through the cutover);
- the generation-metadata hand-off surface: `GenerationMetadata` (and its
  nested `ProviderIdentity` / `MetadataProtocols` / `SelectedComponent` /
  `OutputRecord` / `ReproductionRecord` models) on `RenderedProject.metadata`,
  the `parse_generation_metadata` and `verify_generation_metadata` functions,
  and the `GENERATION_METADATA_VERSION` and
  `DEFAULT_GENERATION_METADATA_TARGET` constants. `PlannedFile` gains a
  `regeneration` field.
- the reproducible-render update surface FT-17.04 / ADR 0065 built on top:
  `plan_update(recorded, *, old, new) -> UpdatePlan`, and `UpdatePlan`'s
  nested `UpdateTarget` / `AppliedRename` models.

A client written against `0.4.1` that ignores the new names keeps working
against `0.5.0` within a widened range. That is the whole content of the
"additive" classification, and the acceptance matrix proves it with an
isolated-import row.

## Validation before render

The client-facing operation order is fixed and total:

1. **negotiate** — `get_engine_info()` and `discover_components()` are both
   side-effect-free and callable before a destination exists; a package,
   protocol, component-version or `metadata_version` mismatch fails closed
   here, with no automatic fallback
   ([compatibility-policy.md](compatibility-policy.md#reporting-an-unsupported-forge-version));
2. **parse** — `parse_project_spec()` rejects a malformed request;
3. **validate** — component selection, options, `requires` and `conflicts`
   are checked; every rejection is a structured `ForgeEngineError` with
   `operation` in `{parse, validate}`;
4. **plan** — `plan_generation()` resolves deterministic ownership;
5. **render** — `render_project()` produces bytes in memory;
6. **validate rendered** — `validate_rendered_project()` runs the
   side-effect-free output checks before a client may stage.

Everything a client can get wrong is rejected before step 5. The client never
inspects a component resource to do any of this: it negotiates on
`get_engine_info()` and chooses on path-free `ComponentDescriptor`s
(**FT-ROADMAP-01-AC-04**). No `create-forge` change in Stage 16 or Stage 18
adds a component-resource read, and the acceptance matrix has a row that
asserts it.

## Structured safe failures

The `EngineErrorCode` set is the seven original values plus the two FT-15.02
reserved, which FT-17.01 shipped. `operation` is the engine's own string for
the phase that failed:

| Code | `operation` today | Class |
| --- | --- | --- |
| `invalid-project-spec` | `parse` | request |
| `component-discovery-failed` | `discover` | environment |
| `invalid-component-selection` | `validate` | request |
| `invalid-component-options` | `validate` | request |
| `generation-plan-failed` | `plan` | planning |
| `template-render-failed` | `render` | rendering |
| `generated-project-invalid` | `validate-output` | post-render |
| `invalid-generation-metadata` | `parse` or `validate` | request |
| `unsupported-generation-metadata` | `parse` or `validate` | request |

No request, selection, options or metadata failure carries
`operation="render"`: a corrupt request is always distinguishable from a
rendering fault, and the two metadata codes stay in the `parse` /
`validate` band the same way. Diagnostics carry a field path and a fixed safe
message only — no rendered content, no secret, no absolute path — the same
discipline
[notebook-data-and-model-safeguards.md](notebook-data-and-model-safeguards.md)
holds notebook diagnostics to.

## Reproducibility and rollback

**Reproduction** is unchanged from
[generation-provenance.md](generation-provenance.md): to reproduce a
project's original output the client reads `provider.version` and `spec` from
the metadata document, provisions that exact `forge-template` release into an
isolated environment, and calls the ordinary public `render_project(spec)`.
The provider ships no historical-render API and bundles no past content trees;
the reproducibility guarantee — for a given release, `parse_project_spec`
followed by `render_project` is a pure function of the spec — is what makes
that sound. This contract adds nothing to it.

**Provider release rollback** is decided here (**FT-ROADMAP-01-AC-05**):

- A published release is **immutable**. A defect in `0.5.0` is never fixed by
  mutating the artefact; it is corrected forward as `0.5.1` (or `0.6.0` if it
  needs a new line), and the defective version is yanked from the index so no
  new install resolves it. This matches
  [CONTRIBUTING.md](../CONTRIBUTING.md#releasing) — `release.yml` rejects an
  existing or non-increasing tag.
- The `0.4.x` line stays installable and supported for the compatibility
  policy's window — **at least 90 days and at least one further tagged
  release** past the cutover — so a client that hits a `0.5.0` defect can pin
  back to `>=0.4.1,<0.5` and keep generating while the fix ships. The
  acceptance matrix carries a regression row that proves a `0.4.1`-pinned
  client still resolves, installs and generates after `0.5.0` publishes.
- Rolling back a **generated project** — restoring a user's working tree and
  its stored generation metadata after a bad update — is
  [CF-18.05](https://github.com/Sandsy09/create-forge/issues/162)'s, never the
  provider's. The provider's contribution to that is only the immutable-release
  and reproducibility guarantees above.

## Migration expectations

- **A downstream client** moves from `forge-template>=0.4.1,<0.5` to
  `>=0.5,<0.6` in one reviewed change: widen the bound, refresh the lock,
  re-run negotiation. A `0.3` or out-of-range engine still fails closed before
  generation. This is the client's to schedule (CF-18.01); the provider only
  guarantees the release is an immutable, reviewed target.
- **A generated project** does nothing. No generated project imports
  `forge_template` or carries any Forge package as a runtime dependency
  ([compatibility-policy.md](compatibility-policy.md#non-guarantees)), so a
  provider release never reaches it.
- **The direct-Copier path** is retained and not deprecated. Stage 17 changes
  nothing under `template/` or `copier.yml`, so `copier update` keeps working
  for every project already scaffolded from a tag, [invariants](invariants.md)
  3 and 6 are untouched, and no `_migrations` block is required by this
  cutover. Retiring `template/` in favour of the catalogue stays a separate
  future initiative with its own `_migrations` moment.

## The acceptance matrix

Every row names one non-interactive command with a binary outcome and one
repository owner. "Executable" reads as FT-10.04 fixed it: a row is executable
once its command exists and can be run the moment its stage arrives, not once
it passes. Every provider child of
[Stage 17](https://github.com/Sandsy09/forge-template/issues/142) and
[Stage 18](https://github.com/Sandsy09/forge-template/issues/143) owns at
least one row, and no row names an unfiled issue —
`tests/test_cutover_gates.py` checks both directions.

### Engine and catalogue

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| Discovery returns the `github` platform and eight capabilities with the accepted metadata, in lexical order | FT-17.02, FT-17.03 | `uv run pytest tests/test_platform_composition.py` | FT-17.02 |
| Every approved Foundation extension point is published; empty points render `library` / `cli` / `data-science` byte-for-byte unchanged bar approved fills | FT-17.03 | `uv run pytest tests/test_extension_points.py tests/test_capability_extension_points.py` | FT-17.03 |
| The `dependabot`→`github` requires edge, the `dependabot`⇔`renovate` conflict, and `documentation`→`library` reject before render as `invalid-component-selection` / `validate` | FT-17.02 | `uv run pytest tests/test_platform_composition.py` | FT-17.02 |
| `get_engine_info()` publishes `metadata_version` and `component_manifest_protocols = (1, 2, 3)`; the ProjectSpec protocol tuple is still `(1,)` | FT-17.01 | `uv run pytest tests/test_compatibility_policy.py tests/test_generation_provenance.py` | FT-17.01 |
| Descriptor results carry no filesystem or package-resource path | FT-17.02 | `uv run pytest tests/test_platform_composition.py` | FT-17.02 |
| The two reserved `EngineErrorCode` values are shipped and carry only `operation` in `{parse, validate}` | FT-17.01 | `uv run pytest tests/test_engine.py tests/test_generation_provenance.py` | FT-17.01 |
| The built wheel ships every new manifest, contribution and owned resource and still excludes repo tooling, under the size ceiling | FT-17.05 | `uv run poe check:wheel` | FT-17.03 |
| Public engine signatures and result fields are unchanged except the additive `metadata_version`, the two codes, and the metadata hand-off | FT-17.05 | `uv run pytest tests/test_engine.py` plus an isolated import of the candidate build | every Stage 17 child |

### Generated projects

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| A `library` / `cli` / `data-science` project reproduced from recorded metadata on the provisioned release is byte-identical to the original render | FT-17.04 | `uv run pytest tests/test_generation_provenance.py` | FT-17.04 |
| A project with `github` and selected capabilities builds, installs, and passes its own `poe check` including the type-check, coverage and pre-commit gates | FT-17.05 | `uv run poe archetype` | FT-17.03 |
| Every generated target has an explicit Foundation, archetype, platform or capability owner | FT-17.03 | `uv run poe check` | FT-17.03 |
| `added` / `removed` / `renamed` / `changed` / `unchanged` targets classify correctly across a supported update history, including an owner-declared rename | FT-17.04 | `uv run pytest tests/test_generation_provenance.py` | FT-17.04 |
| The generated project needs neither Forge repository for development, build or runtime | FT-17.05 | `uv run poe archetype` in an isolated venv | FT-17.03 |

### Downstream-client independence

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| An independent client consuming only the public facade negotiates compatibility and renders every valid composition without a `create-forge` dependency | FT-17.05 | `uv run poe crossrepo` plus `create-forge` facade tests | FT-17.05 |
| The client never reads a component resource: negotiation uses `get_engine_info()`, selection uses path-free descriptors, both callable before a destination exists | FT-17.05 | `uv run pytest tests/test_compatibility_policy.py` | FT-17.05 |
| An unavailable historical provider fails closed with the four report facts; the opt-in degraded two-way update is recorded as `reproduction.mode = "degraded"` | FT-17.04 | `uv run pytest tests/test_generation_provenance.py` | FT-17.04 |

### Regression

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| `library` / `cli` / `data-science` single-selection output is byte-identical to `0.4.1` save for approved additive extension-point fills | FT-17.05 | `uv run poe archetype` plus the `tests/fixtures/archetype_regression/digests.json` pin | FT-17.03 |
| All four direct-Copier combos render and pass their own `poe check`; `copier update` from the last tag preserves local edits and reaches HEAD | FT-17.06 | `uv run poe combos`, `uv run poe update` in the protected release run | FT-17.06 |
| A `create-forge` pinned to `forge-template>=0.4.1,<0.5` still resolves, installs and generates after `0.5.0` publishes | FT-18.01 | `create-forge` regression suite against the `0.4.1` pin | FT-18.01 |
| The integrated cutover — the immutable released provider plus the candidate client — passes the full cross-repository acceptance matrix | FT-18.01 | `create-forge` end-to-end suite against the published `0.5.0` release | FT-18.01 |

### Publication

| Check | Owner | Evidence command | First required at |
| --- | --- | --- | --- |
| `0.5.0` is published only through CONTRIBUTING's protected `release.yml` with `dry_run: true` inspected first | FT-17.06 | `release.yml` dry run then dispatch | FT-17.06 |
| The tag, GitHub Release and PyPI wheel/sdist name one commit SHA; the artefacts install into an isolated environment and expose the negotiation facts | FT-17.06 | published-artefact audit | FT-17.06 |
| The provider hand-off records immutable evidence and the supported client bound without asserting that client cutover has shipped | FT-17.06 | ADR and living-doc review | FT-17.06 |

## Cross-repository release gates

The one-way dependency `create-forge → forge-template → generated project`
holds, and the roadmap rule is that the provider merges and releases before
the client adopts the line. `create-forge`'s
[integration contract](https://github.com/Sandsy09/create-forge/blob/main/docs/integration-contract.md#release-coordination)
is authoritative for the client-side mechanics; this contract states the
gates, bound to the recorded
[dependency matrix](roadmap-v3/github-issues/CROSS-REPO-DEPENDENCIES.md).

| Gate | Owner | Entry criteria | Exit criteria |
| --- | --- | --- | --- |
| FT-15.04 contract accepted | FT-15.04 / #149 | FT-15.01, FT-15.02 and FT-15.03 merged; this ADR and document reviewed | Merged on protected `main`; `FT-EPIC-15` closed with every review criterion evidenced; **no version bump — `main` stays untagged** |
| `create-forge` Stage 16 contracts | CF-EPIC-16 / create-forge#152 | FT-15.04 accepted (this gate's exit) | The engine-default selection, source-resolution and update-ownership contracts accepted; CF-16.03 filed with its dependency graph |
| `forge-template` Stage 17 implementation | FT-EPIC-17 / #142 | CF-16.03 accepted | FT-17.01–FT-17.05 merged; every Engine, Generated-project, Independence and Regression row above passed on protected `main` |
| Reviewed `forge-template` `0.5.0` | FT-17.06 / #155 | Every Stage 17 acceptance row passed; the dry run inspected | The release run, tag, GitHub Release and PyPI artefacts name one commit SHA; the published-artefact audit passed; `0.4.x` remains installable |
| `create-forge` `>=0.5,<0.6` adoption | CF-18.01 / create-forge#158 | `v0.5.0` is an immutable published target | Engine bound widened; lock refreshed; `0.3` and out-of-range engines fail before generation; plain installs unaffected |
| Integrated cutover validation | FT-18.01 / #156, CF-18.07 / create-forge#164 | The released provider paired with the candidate client | The full cross-repository matrix passes together; a provider defect requires a corrected reviewed release and renewed client adoption evidence |

Merging is not releasing. A merge to `main` leaves it untagged and invisible
to `copier update` and to a version-pinned engine client until `release.yml`
runs. No version in this repository changes when this contract merges.

## Stage 17 scope reconciliation

Each Stage 17 and Stage 18 provider child inherits fixed answers from this
contract and the three earlier Stage 15 decisions. What remains open per child
is narrow.

| Issue | Fixed by Stage 15 | Still owned by the issue |
| --- | --- | --- |
| [FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) | The metadata document shape, the reproducibility guarantee, the reserved axis and the two error codes (FT-15.02); manifest protocol `3` as the home for the rename and regeneration-disposition records (here) | **Done ([ADR 0062](adr/0062-generation-metadata-and-manifest-protocol-3.md))** — the two-array manifest-`3` schema, `EngineInfo.metadata_version`, `RenderedProject.metadata`, `parse_generation_metadata` / `verify_generation_metadata`, `DEFAULT_GENERATION_METADATA_TARGET`; Foundation deferred |
| [FT-17.02](https://github.com/Sandsy09/forge-template/issues/151) | One `github` platform, one required `organisation` option, the two CI points, the three Foundation host-link points, the `requires`/`conflicts` edges (FT-15.03) | The manifest bytes, the content trees, the CI matrix shape, the pinned action SHAs, whether `library`/`cli`/`data-science` move a version |
| [FT-17.03](https://github.com/Sandsy09/forge-template/issues/152) | The eight-capability set, the two dependency-group points, the `api-reference` point (FT-15.03); the nine `needs a bounded issue` rows resolve here (below) | Each capability's owned files, options, tasks and dependency bounds; whether a `pyproject` tool-config point is published or `[tool.coverage]` / `[tool.pyright]` relocate to standalone files |
| [FT-17.04](https://github.com/Sandsy09/forge-template/issues/153) | The old/new/working-tree diff model, the classification vocabulary, the unavailable-provider fail-closed rule and the degraded path (FT-15.02) | **Done ([ADR 0065](adr/0065-implement-reproducible-rendering-for-updates.md))** — `plan_update(recorded, old=..., new=...) -> UpdatePlan`, the five-value classifier, `[[renames]]` window-surfacing, and the fail-closed unavailable-provider path (reusing `unsupported-generation-metadata`) |
| [FT-17.05](https://github.com/Sandsy09/forge-template/issues/154) | The acceptance matrix above; validation-before-render and the no-resource-read rule (here, AC-04) | **Done ([ADR 0066](adr/0066-validate-provider-parity-reproducibility-and-distributions.md))** — every Engine/Generated-project/Independence/Regression row FT-17.05 owns executed, evidenced in [provider-acceptance-validation.md](provider-acceptance-validation.md); one content defect found and fixed (`pre-commit` `1.0.0` → `1.0.1`) |
| [FT-17.06](https://github.com/Sandsy09/forge-template/issues/155) | `0.5.0` as the line; the immutable-release and `0.4.x`-window rules (here, AC-05) | **Done** — no new decision executed; [cutover-provider-release.md](cutover-provider-release.md) records the protected release and dry run, the tag/Release/PyPI artefact audit, the direct-Copier regression, and the client-bound hand-off |
| [FT-18.01](https://github.com/Sandsy09/forge-template/issues/156) | The integrated matrix rows and the corrected-release rule (here) | Pairing the candidate client with the released provider and executing the provider-owned integrated rows |

**The nine `needs a bounded issue` rows close by reference.** FT-15.03
resolved every flagged row in
[engine-default-parity.md](engine-default-parity.md) to the `documentation`
capability or the `dependabot` / `renovate` pair — all three are capabilities,
and [FT-17.03](https://github.com/Sandsy09/forge-template/issues/152)'s
acceptance criteria already cover *"each assigned provider-content parity row,
including approved tooling/configuration/tasks"*. So those rows' owner cells
move from `FT-15.03: needs a bounded issue` to `FT-15.03 → FT-17.03`, and **no
new issue is filed**. This keeps the hash-pinned `docs/roadmap-v3/**` mirror
byte-identical and `tests/test_parity_inventory.py`'s no-invented-numbers
check satisfied. It is FT-15.04's explicit mandate: `engine-default-parity.md`
states the marker means *"FT-15.04 must split one"*, and splitting here means
recognising the existing child that fits.

## Explicit exclusions

- **FT-ROADMAP-01-EX-02 — no engine-default switch here.** This contract flips
  no default. The provider has no notion of a "default generator"; making the
  engine the default is a `create-forge` CLI decision owned by
  [CF-16.01](https://github.com/Sandsy09/create-forge/issues/155) and the
  Stage 18 client-delivery children. Nothing in this contract or Stage 17
  changes which path `create-forge` runs by default.
- **FT-ROADMAP-01-EX-04 — no remote registry or plugin execution.** The
  catalogue is package-bound and discovered from the installed wheel. Nothing
  here introduces a remote component registry, a downloadable component, or
  code execution during discovery, planning or rendering.
- No new shared Forge runtime dependency for generated projects — every
  capability contribution is development-time only.
- No Streamlit archetype; that is [roadmap-v4](roadmap-v4/README.md) Stages
  19–21 and begins only after these cutover contracts are accepted.
- No metadata filename, merge algorithm, or deprecation date is preselected —
  each is either decided above with its rationale or explicitly left to its
  owner below.

## What this contract does not decide

Reserved for other owners:

- the concrete manifest-`3` field names and schema, and the public
  generation-metadata hand-off surface —
  [FT-17.01](https://github.com/Sandsy09/forge-template/issues/150);
- each capability's owned content, options and dependency bounds, and whether
  a `pyproject` tool-configuration extension point is published —
  [FT-17.03](https://github.com/Sandsy09/forge-template/issues/152);
- the persisted metadata filename and on-disk location, the merge, dry-run,
  cancellation and rollback policy for an engine-native update, and a user
  project's rollback —
  [CF-16.02](https://github.com/Sandsy09/create-forge/issues/156) and
  [CF-18.05](https://github.com/Sandsy09/create-forge/issues/162);
- the CLI default switch, the explicit legacy route, and any deprecation
  timeline for the direct-Copier path —
  [CF-16.01](https://github.com/Sandsy09/create-forge/issues/155) and the
  Stage 18 client children;
- whether a future release promotes the engine to `1.0.0`, and retiring
  `template/` in favour of the catalogue;
- the Streamlit archetype and its layout —
  [roadmap-v4](roadmap-v4/README.md).

## Validation

`tests/test_cutover_gates.py` runs under `uv run poe check`. Following the
three predecessor pins, it is derived and tripwired — every "Current" and
"Unchanged" claim is checked against the live engine, never against the
document itself. It proves:

- the recorded current package version and manifest-protocol tuple equal
  `get_engine_info()`; the ProjectSpec protocol equals
  `SUPPORTED_PROJECTSPEC_PROTOCOLS`; the Foundation source protocol equals
  `foundation.toml`'s `foundation_version`; each shipped component's recorded
  current version equals its `discover_components()` descriptor; the unpublished
  protocol axes agree with `compatibility-policy.md`'s living state table;
- every acceptance-matrix row names a filed issue (cross-checked against both
  roadmap packs' `filing-manifest.json`), and every provider child FT-17.01
  through FT-17.06 and FT-18.01 owns at least one row;
- the literal marker `needs a bounded issue` no longer appears in any matrix
  row of `engine-default-parity.md`, and every provider-disposition `gap` row
  there now cites a filed issue;
- every `EngineErrorCode` in the failure table permits only `operation` in
  `{parse, validate}` where this contract says so, confirmed at runtime by
  driving one real invalid selection through both `plan_generation` and
  `render_project`;
- the contract names FT-ROADMAP-01-EX-02 and FT-ROADMAP-01-EX-04 literally.

Tripwires — each was written to fail deliberately when Stage 17 lands, forcing
this contract back into step with the implementation, exactly as FT-15.02's
reserved-code and FT-15.03's reserved-point tripwires did. FT-17.01 / ADR 0062
turned four of them over; FT-17.06 has since turned over the fifth:

- `get_engine_info().package_version` has moved to the `0.5` line —
  **FT-17.06** released `0.5.0`;
- `SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS == (1, 2, 3)` — protocol `3` is
  published, and a protocol-`1` or protocol-`2` manifest is still accepted;
- `set(EngineErrorCode)` is the seven original values plus
  `invalid-generation-metadata` and `unsupported-generation-metadata`, each
  restricted to `operation` in `{parse, validate}`;
- `EngineInfo` publishes `metadata_version == 1`;
- `forge_template.__all__` adds the generation-metadata models, functions and
  constants and renames or removes nothing;
- `copier.yml` carries no `_migrations` block — decision 3's retention,
  checked rather than asserted; **holds**.
