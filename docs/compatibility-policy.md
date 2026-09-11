# Forge-Blueprint compatibility policy

This document defines how the versioned surfaces the `forge-template` engine
publishes are allowed to move, what a downstream client may depend on, and
what it must do when the installed engine cannot satisfy it. It is the
canonical answer to [FT-09.04 / #47](https://github.com/Sandsy09/forge-template/issues/47),
adopted by [ADR 0041](adr/0041-forge-blueprint-compatibility-policy.md), and
pinned executably by
[`tests/test_compatibility_policy.py`](../tests/test_compatibility_policy.py).

[Blueprint](terminology.md#blueprint) is the future organisation-facing
downstream consumer this document is written for. It is not part of the
current two-repository implementation; this document defines the contract
such a client consumes, not the client itself.

## Scope

This policy governs the **installed engine release**: the `forge-template`
package, its data protocols, the implicit Foundation content source, and its
bundled components. It complements, and does not restate:

- [python-support.md](python-support.md) — the CPython versions Forge offers
  to *generated projects*. A different axis entirely: that policy is about
  what a generated project runs on, this one is about what a client consuming
  the engine can depend on.
- [ADR 0002](adr/0002-copier-over-cookiecutter.md) and
  [ADR 0003](adr/0003-two-repo-split.md) — the direct-Copier `template/` path
  resolves its own compatibility from PEP 440 git tags and `copier update`'s
  three-way merge, governed by [invariants](invariants.md) 3 and 6.
  That mechanism is unrelated to the axes below and is out of scope here.
- Client-side presentation. This document defines what the engine publishes
  and the minimum facts a conformant report must carry, not wording,
  formatting, or exit codes — see "Reporting an unsupported Forge version"
  below.

## The versioned axes

Nine surfaces version independently. Changing one never implicitly changes
another.

| Axis | What it versions | Client-visible today |
| --- | --- | --- |
| `forge-template` package | The installable engine-and-reviewed-assets unit as a whole | Yes — `get_engine_info().package_version` |
| ProjectSpec protocol | The generation-request wire schema | Yes — `get_engine_info().projectspec_protocols` |
| Component manifest protocol | The component TOML metadata schema | Yes — `get_engine_info().component_manifest_protocols` |
| Component content version | One component's own content and compatibility surface (PEP 440) | Yes — `ComponentDescriptor.version` per discovered component |
| Generation metadata | The provenance document's schema (`metadata_version`) | Yes — `get_engine_info().metadata_version` (published by FT-17.01) |
| Option-schema protocol | The `options_schema` JSON shape a component's options follow | No |
| Foundation source protocol | The internal TOML shape of the implicit Foundation content source | No |
| Organisation-policy protocol | The strict JSON policy wire format | No — doc-only by design, see [organisation-policy.md](organisation-policy.md) |
| Extension-point inventory | The published, named set of points owner content exposes | No — pinned by test, carries no integer of its own |

The last three are deliberately unpublished; see "What the engine publishes
for negotiation" below for why that is a considered choice, not a gap.
Generation metadata was reserved by FT-15.02 and moved into this table when
[FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) /
[ADR 0062](adr/0062-generation-metadata-and-manifest-protocol-3.md) published
it through `get_engine_info()`.

[FT-15.03](https://github.com/Sandsy09/forge-template/issues/148) /
[ADR 0060](adr/0060-platform-composition-and-generated-tooling.md) reserved
five additions to the extension-point-inventory axis plus `ci-jobs`,
`ci-steps` and `api-reference` on component content.
[FT-17.02](https://github.com/Sandsy09/forge-template/issues/151) /
[ADR 0063](adr/0063-implement-the-github-platform.md) published three of them —
`pyproject-project-urls`, `contributing-project-shape`,
`security-project-shape` (Foundation inventory 11 → 14) — and `ci-jobs` /
`ci-steps` on the `github` platform's own content.
[FT-17.03](https://github.com/Sandsy09/forge-template/issues/152) /
[ADR 0064](adr/0064-implement-approved-generated-content-parity.md) published
the remaining two Foundation points (`pyproject-named-dependency-groups`,
`pyproject-dependency-group-includes`, inventory 14 → 16) and `api-reference`
on the `documentation` capability. All are backward-compatible additions, and
each carries the package-version bump this document already requires for any
observable Foundation change
([extension-points.md](extension-points.md#stability-and-versioning)); that bump
is FT-17.06's `0.5.0`.

## Classified: the engine-default cutover transition

[FT-15.04](https://github.com/Sandsy09/forge-template/issues/149) /
[ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md)
classifies which axes the engine-default cutover moves, against the rules in
this document. It is a classification, not a transition: nothing below the
"Current compatibility state" table changes until Stage 17 implements and
[FT-17.06](https://github.com/Sandsy09/forge-template/issues/155) publishes.
The classified move is:

- **`forge-template` package** → a new minor line, `0.5.0`. Below `1.0` a
  supported range is minor-scoped, so `create-forge`'s `>=0.4.1,<0.5` cannot
  drift into it and must widen deliberately; `1.0.0` is explicitly not
  promised. FT-17.06 performs this release; `main` stays on `0.4.1` until then.
- **Component manifest protocol** → `(1, 2, 3)`, **done** by
  [FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) /
  [ADR 0062](adr/0062-generation-metadata-and-manifest-protocol-3.md). The
  owner-declared rename and regeneration-disposition records are new manifest
  fields, and the models forbid unknown keys, so they could not ride protocol
  `2`. Protocol-`1` and protocol-`2` manifests stay accepted unchanged — a
  backward-compatible protocol addition.
- **Generation metadata** → published `metadata_version = 1` through
  `get_engine_info()`, **done** by FT-17.01 / ADR 0062; it now sits in the
  "Current compatibility state" table below.
- **Every other axis, and the whole public facade bar the additive
  generation-metadata names** (the `metadata_version` field, the two
  `EngineErrorCode` values, `PlannedFile.regeneration`,
  `RenderedProject.metadata`, and the `GenerationMetadata` surface) →
  unchanged. That is a requirement on Stage 17, not a prediction.

Provider release rollback is immutable-forward: a defective release is yanked
and corrected in a higher version, never mutated, and the `0.4.x` line stays
supported for this document's deprecation window past the cutover so a client
can pin back. Full detail and the acceptance matrix live in
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md).

## Generation metadata (`metadata_version`)

[FT-15.02](https://github.com/Sandsy09/forge-template/issues/147)'s
[generation provenance contract](generation-provenance.md) reserved a ninth
axis: `metadata_version`, the schema version of the document the engine hands
a client so a generated project can be reproduced or updated.
[FT-17.01](https://github.com/Sandsy09/forge-template/issues/150) /
[ADR 0062](adr/0062-generation-metadata-and-manifest-protocol-3.md) published
it through `get_engine_info().metadata_version` as a backward-compatible
addition; it is now in "The versioned axes" and "Current compatibility state"
tables. It is client-visible, negotiated exactly like the protocol tuples, and
governed by every rule in this document; an unsupported recorded value fails
closed as `unsupported-generation-metadata` with the four report facts from
"Reporting an unsupported Forge version". The document itself is
`.forge/generation.json` by documented default
([DEFAULT_GENERATION_METADATA_TARGET](generation-provenance.md#version-negotiation));
the client owns writing, reading and committing it.

## Compatible ranges

**Package.** Below `1.0`, a supported dependency range stays within one minor
line (`>=0.y.a,<0.(y+1)`); from `1.0` onward, within one major line
(`>=n.a,<n+1`). Every downstream declaration carries a tested lower bound and
a strict upper bound — an unbounded engine dependency is unsupported. This
matches `create-forge`'s own
[integration-contract.md](https://github.com/Sandsy09/create-forge/blob/main/docs/integration-contract.md#version-and-protocol-compatibility)
rule; this document is the definition that rule points at, not a competing
one.

**Protocol integers.** The engine publishes the tuple of protocol values it
accepts (see "What the engine publishes for negotiation"). A client is
compatible with a given protocol axis exactly when its own supported set
intersects the engine's published tuple. A protocol integer changes only for
breaking wire/validation/semantic changes to that protocol; backward-compatible
additions stay on the current value.

**Components.** Component `version` is independent PEP 440, unrelated to the
package version or any protocol integer
([component-manifests.md](component-manifests.md#manifest-and-component-versions)).
A version bump's meaning:

- **Patch** — corrected owned content with no selection, option-schema,
  planning-model, error-code, or public-signature change. `library`/`cli`
  `1.0.1` is the existing example
  ([composition-architecture-review.md](composition-architecture-review.md)).
- **Minor** — additive owned content or a new optional component option.
- **Major** — a breaking change to owned content, an option's type or
  required-ness, or one of that component's extension-point contributions.

**Foundation.** Foundation carries no independent, client-visible version —
this is existing design, not new:
[component-manifests.md](component-manifests.md#foundation) already states it
"carries no independent version a `requires`/`conflicts` reference could
name." `foundation_version` is an internal source-format protocol, not a
negotiable client-facing axis. Foundation compatibility is carried entirely
by the package version: a package version bump is required for any
Foundation change a client could observe, including publishing, removing, or
renaming an extension point (see
[extension-points.md](extension-points.md#stability-and-versioning)).

**Python compatibility.** A component's `requires_python` must be satisfied
across the whole selected `PythonSelection.tested_versions` range, not just
one endpoint — already enforced by validation
([component-manifests.md](component-manifests.md#manifest-and-component-versions));
this policy states it as a durable compatibility rule rather than leaving it
implicit in validator behaviour.

## Deprecation windows

A deprecated surface remains functional for at least **90 days** and for at
least **one further tagged `forge-template` release**, whichever is longer —
the same notice period [python-support.md](python-support.md#deprecation-and-removal)
already commits to for CPython releases, extended here to every axis in this
document, plus a release-count floor: a calendar promise alone is not
meaningful against this repository's irregular, manually triggered release
cadence.

Deprecable surfaces: a public name or signature exported from
`forge_template`, a `RenderedProject`/`GenerationPlan`/descriptor result
field, an `EngineErrorCode` value, a protocol integer leaving a published
supported tuple, a published extension-point ID, a component option, a
component itself, or a component's major version line.

Deprecation notice must be layered through:

- this document's current-state table;
- a tracking issue and pull request;
- the release notes of the release that introduces the deprecation; and
- migration guidance for an affected client.

Removal happens only in a later release that opens a new compatibility line,
in a pull request carrying the `breaking-change` label, repeating the
migration path in its release notes — mirroring
[python-support.md](python-support.md#deprecation-and-removal)'s existing
removal rule exactly.

## What the engine publishes for negotiation

`get_engine_info()` and `discover_components()` are both side-effect-free and
both safely callable before any destination decision — neither reads or
writes a filesystem target, and `get_engine_info()` does not even require a
component catalogue to be present. A client can negotiate compatibility, and
fail closed if it must, before choosing a destination, discovering
components, planning, or rendering.

- `get_engine_info()` reports the installed package version and the
  supported ProjectSpec and component-manifest protocol tuples.
- `discover_components()` reports each component's own PEP 440 `version`,
  its supported ProjectSpec protocols, and its `requires_python`.

The option-schema protocol, Foundation source protocol, and organisation-policy
protocol are not independently published because none is independently
pinnable by a client: each moves in lockstep with the package version
(option-schema and Foundation) or is a documentation-only contract with no
executable engine-side parser to negotiate against today
([organisation-policy-fixtures.md](organisation-policy-fixtures.md)). A
future ADR revisiting this must supersede this one.

## Reporting an unsupported Forge version

When a client detects that the installed engine cannot satisfy what it
requires — an out-of-range package version, a protocol integer outside the
published tuple, or a component version outside a declared requirement — a
conformant report must:

1. fail closed, with no automatic fallback, before any component discovery,
   planning, rendering, or destination write;
2. name the mismatched axis (package, a specific protocol, or a specific
   component);
3. state the detected value; and
4. state the supported value or range, together with a concrete upgrade,
   downgrade, or source-correction action.

Presentation is entirely client-owned: message wording, output formatting,
and process exit codes are not defined here.
`create-forge`'s own [ADR 0011](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0011-engine-source-and-version-resolution.md)
reserves exit status `3` for exactly this failure; this document does not
claim or duplicate that reservation. `create-forge`'s existing
["Unsupported combinations"](https://github.com/Sandsy09/create-forge/blob/main/docs/integration-contract.md#unsupported-combinations)
rules already satisfy points 1–4 above.

The [no-copy inheritance proof](no-copy-inheritance.md) validates the other
side of negotiation: once compatible clients construct equivalent effective
ProjectSpecs, policy provenance does not alter the deterministic plan or
rendered bytes.

## Current compatibility state

Living snapshot, reviewed 2026-09-11. Advancing it in line with the rules
above does not require a new ADR; a semantic change to those rules does (see
"Ownership and change process").

| Axis | Current value |
| --- | --- |
| `forge-template` package | `0.4.1` |
| ProjectSpec protocol | `1` |
| Component manifest protocol | `1`, `2`, `3` |
| Generation metadata (`metadata_version`) | `1` |
| `library` component | `1.0.1` |
| `cli` component | `1.0.1` |
| `data-science` component | `1.0.0` |
| `jupyter` component | `1.0.0` |
| `scientific-python` component | `1.0.0` |
| `github` component | `1.0.0` (first shipped platform, FT-17.02) |
| `changelog` component | `1.0.0` (first shipped `manifest_version = 3`, FT-17.03) |
| `coverage` component | `1.0.0` (FT-17.03) |
| `dependabot` component | `1.0.0` (FT-17.03) |
| `documentation` component | `1.0.0` (FT-17.03) |
| `dotenv-example` component | `1.0.0` (FT-17.03) |
| `pre-commit` component | `1.0.0` (FT-17.03) |
| `pyright` component | `1.0.0` (FT-17.03) |
| `renovate` component | `1.0.0` (FT-17.03) |
| Option-schema protocol | `1`, `2` |
| Foundation source protocol | `1` (internal; see above) |
| Organisation-policy protocol | `1` (doc-only; see above) |

Released `create-forge` declares the compatible
`forge-template>=0.4.1,<0.5` engine range
([template-engine-api.md](template-engine-api.md#compatibility-and-current-cutover-boundary)).

The Data Science line advanced the package to `0.4.0`, first available as the
[`v0.4.0` GitHub Release](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0)
and [PyPI distribution](https://pypi.org/project/forge-template/0.4.0/), and
added `data-science`, `jupyter`, and `scientific-python` at component version
`1.0.0`, with every protocol integer unchanged. The
[Data Science compatibility and acceptance contract](data-science-compatibility-and-acceptance.md)
classifies each axis and the release gate. FT-14.03 then republished that
same unchanged catalogue as the reviewed
[`v0.4.1` GitHub Release](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.1)
and [PyPI distribution](https://pypi.org/project/forge-template/0.4.1/) —
see [reviewed-engine-release.md](reviewed-engine-release.md);
[python-support.md](python-support.md) uses the same living snapshot pattern
for its own state.

## Non-guarantees

This policy does not promise:

- that an uninstalled source-tree checkout reports a meaningful version
  (`get_engine_info()` reports `"0+unknown"` in that case, by design — see
  `forge_template.engine._package_version`);
- that an engine newer than a client's declared upper bound is safe to adopt
  without the range actually being widened;
- any commitment about what a future Blueprint-class release may assume
  beyond the axes and rules stated in this document;
- a speculative upper-bound constraint against a future incompatibility that
  has not shipped; or
- that generated projects carry any Forge package as a runtime dependency —
  compatibility here concerns the engine and its clients, never the
  independent output described in
  [terminology.md](terminology.md#generated-project).

## Ownership and change process

`forge-template` owns this compatibility policy and the axes it governs. A
downstream client owns its own negotiation trigger points, presentation, and
what it does after a failed negotiation.

A semantic change to the compatible-range rules, the deprecation window, or
the negotiation/reporting requirements requires a new ADR superseding
[ADR 0041](adr/0041-forge-blueprint-compatibility-policy.md). The living
"Current compatibility state" table above may advance on its own, the same
device [python-support.md](python-support.md#non-guarantees) already uses for
its own living table.
