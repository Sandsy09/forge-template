# Safe override and extension points

This document answers one question the earlier composition contracts each
deferred: what may a downstream client — organisation policy, a future
Blueprint-style consumer, or a component author — safely change about
generated output, and what happens when it tries something unsafe. It is
delivered by [FT-09.02](https://github.com/Sandsy09/forge-template/issues/45)
and adopted by [ADR 0039](adr/0039-deny-policy-file-overrides.md).
[FT-11.01 / #105](https://github.com/Sandsy09/forge-template/issues/105) and
[ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md) later
grew the published inventory from eight points to eleven for capability
tooling — an additive change to the inventory, not to any rule here.

## Scope

[file-conflicts.md](file-conflicts.md) defines output targets, dispositions,
and collision mechanics — *how* composed output is resolved.
[organisation-policy.md](organisation-policy.md) defines *what a policy may
select* — required, default, and forbidden archetypes, capabilities, and
platforms. [terminology.md](terminology.md) defines composition authority in
general. This document sits between them: it names the complete, closed set
of places extension is safe, states that no override grant exists, and makes
every unsupported attempt fail deterministically before any file operation.

## The four sanctioned extension surfaces

Every safe way to influence generated output falls into exactly one of these.
Nothing outside them is an extension point, regardless of who is asking.

| Surface | Who uses it | What it can do | What it cannot do |
| --- | --- | --- | --- |
| **Selection** | Organisation policy, explicit user choice | Choose, default, require, or forbid an archetype/capability/platform ([organisation-policy.md](organisation-policy.md)) | Name a file, path, or content; select an unknown or wrong-kind component |
| **Project metadata** | The client constructing `ProjectSpec` | Supply `ProjectMetadata` and `PythonSelection` values that templates render | Add fields outside the strict [ProjectSpec protocol](project-spec.md) schema |
| **Component options** | The client, per selected component | Set a value declared in that component's `options_schema` protocol `2` (today: `library`'s `packaging_mode` and `initial_version`; `cli` declares none — see [cli-application-archetype.md](cli-application-archetype.md)) | Set an option no manifest declares, or one belonging to a component not selected |
| **Content extension points** | A selected component's `[[contributions]]` only | Attach additive content into a point another owner published, in composition order | Be reached by a policy, a client, or any party other than a selected component's manifest |

The first three surfaces are unconditionally available today. The fourth is
the one this document defines the inventory and rules for below.

## The published inventory

Content extension points are declared with `[[extension_points]]` in a
manifest's `component.toml` (or, for the implicit content source, in
`foundation.toml`) — see
[component-manifests.md](component-manifests.md#foundation-content-source)
and [file-conflicts.md](file-conflicts.md#extension-points). The complete set
published by the installed catalogue at the time of this decision is:

| Owner file | Extension point IDs |
| --- | --- |
| `content/pyproject.toml.jinja` | `pyproject-build-system`, `pyproject-archetype-metadata`, `pyproject-build-configuration`, `pyproject-runtime-dependencies`, `pyproject-classifiers`, `pyproject-entry-points`, `pyproject-development-dependencies`, `pyproject-task-definitions`, `pyproject-aggregate-check` |
| `content/README.md.jinja` | `readme-project-shape` |
| `content/.gitignore.jinja` | `gitignore-project-shape` |

All eleven are published by the implicit Foundation content source. **Neither
production archetype publishes an extension point of its own** — `library`
and `cli` only contribute into Foundation's points, through manifest protocol
`2`'s `target.kind = "foundation"`
([component-manifests.md](component-manifests.md#accepted-manifest-protocol-v2-target-owner)).
This is unchanged by [ADR 0037](adr/0037-two-archetype-composition-review.md):
the Stage 08 review found no new point was required.

The last three `pyproject.toml.jinja` IDs were added additively by
[FT-11.01 / #105](https://github.com/Sandsy09/forge-template/issues/105) and
[ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md) so a
selected *capability* — not only an archetype — has a sanctioned way to
attach a development dependency, a task definition, and an aggregate-`check`
entry. The first six existed only for an archetype's packaging shape; a
development-tooling capability needs the other three. See
[capability tooling extends the same Foundation content](#capability-tooling-extends-the-same-foundation-content)
below.

Foundation owns six further files with **no** extension point at all:
`.editorconfig`, `.gitattributes`, `.python-version.jinja`,
`CONTRIBUTING.md.jinja`, `LICENSE.jinja`, and `SECURITY.md.jinja`. These are
sole-owner `create` content, deliberately not extensible — stated here rather
than left to be inferred from the absence of a declaration.

## Capability tooling extends the same Foundation content

[ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md)
publishes three points on `content/pyproject.toml.jinja` for
development-time tooling. Nothing about the extension mechanism changes; only
the published inventory grows.

| Extension point | Region it lives in | What a contribution supplies |
| --- | --- | --- |
| `pyproject-development-dependencies` | Foundation's existing `dev` dependency group | PEP 508 requirement strings, one per line, comma-terminated |
| `pyproject-task-definitions` | `[tool.poe.tasks]`, before the aggregate `check` | `"name" = "command"` task lines |
| `pyproject-aggregate-check` | the `check` task's own array | task-name strings, comma-terminated, that `check` then runs in order |

The rules that already govern every other point apply unchanged:

- **Foundation keeps ownership of the target.** A contribution is `extend`,
  never `override` or `merge`. `pyproject.toml` stays Foundation-owned in the
  [public plan](template-engine-api.md); a capability's contributions surface
  as `PlannedExtension` entries on it, exactly as an archetype's do.
- **Any selected owner may contribute** — archetype *or* capability. The point
  does not care which tier the contributor is in; it only requires the
  contributor to be selected and to declare a `[[contributions]]` entry naming
  the point.
- **Multiple contributions compose in [composition order](composition-order.md)**,
  never last-write-wins: the archetype tier first, then the capability tier,
  lexical by component ID within a tier. Two capabilities that both contribute
  a task line produce both task lines, in that order. This is the property
  [FT-11.01 / #105](https://github.com/Sandsy09/forge-template/issues/105)'s
  acceptance criteria name, pinned by
  `tests/test_capability_extension_points.py`.
- **An unfilled point contributes zero bytes.** The engine's marker line —
  including its trailing newline — is removed when no contribution targets it,
  so `library` and `cli` render byte-for-byte as they did before these three
  points existed. ADR 0049 records the one deliberate exception: the aggregate
  `check` array became multi-line so a marker line can sit inside it, which is
  a semantics-preserving reformat, not a behaviour change.
- **A contribution naming an undeclared point is rejected at catalogue
  validation**, independent of any selection — the same
  `component_manifest.validate_manifest_set` check that already guards every
  other contribution.

A capability contributes a `.gitignore` entry (for example
`.ipynb_checkpoints/`) or root-README usage guidance through the **existing**
`gitignore-project-shape` and `readme-project-shape` points, under the same
"any selected owner may contribute" rule — no capability-specific point is
added for either. This is the surface
[notebook-data-and-model-safeguards.md](notebook-data-and-model-safeguards.md#local-working-trees)
defers to FT-11.01.

A capability does **not** get to declare its own named dependency group: that
would need a second point inside `[dependency-groups]` plus an `include-group`
entry, and is deliberately out of scope. Development dependencies a capability
needs go into Foundation's `dev` group, which `[tool.uv]
default-groups = ["dev"]` already installs.

## When an override is allowed

**Never, in protocol `1`.** [file-conflicts.md](file-conflicts.md#foundation-and-policy-overrides)
and [terminology.md](terminology.md#composition-and-authority) each reserved
the `override` disposition — full replacement of another owner's target — as
a grant this issue would decide. The decision is a denial: no policy, client,
or component may replace content another owner created. `merge` remains
classified and equally ungranted.

This is enforced at the type level, not only by policy:

- [`GRANTED_DISPOSITIONS`](../src/forge_template/file_conflicts.py) is
  `("create", "extend")` — `FILE_DISPOSITIONS` still *names* all four so the
  contract can state precisely what `merge` and `override` would mean, but
  only two are grantable.
- `OutputContribution.disposition` is typed `Literal["create", "extend"]`.
  An override contribution is not merely rejected at validation time — it is
  unconstructible.

An organisation that needs different content authors or selects a different
component. It does not gain a channel to replace one.

## What is not an extension point

- **File overlays or replacement.** No mechanism accepts a file path and
  substitutes its content for engine output.
- **Post-render mutation.** `render_project()` returns an immutable
  `RenderedProject`. A client that edits its bytes after the call returns is
  acting entirely outside this contract: `validate_rendered_project` has
  already run against the engine's own output, and nothing re-validates a
  client's later edit. Engine output is authoritative up to the point a
  client takes it; what a client does with its own copy afterward is its own
  responsibility, not a Forge extension mechanism.
- **Executable hooks or plugins.** No manifest field, policy field, or engine
  entry point runs downstream code during planning or rendering.
- **The private catalogue-root test seams.** `_CATALOGUE_ROOT_OVERRIDE` and
  `_FOUNDATION_ROOT_OVERRIDE` in `forge_template.engine` exist only for this
  repository's own test suite. They are not public API, are never guaranteed
  to exist, and must never be exposed or documented as an integration path —
  the same rule [composition-fixtures.md](composition-fixtures.md) already
  states for them.
- **Foundation replacement.** Foundation is the implicit, mandatory baseline,
  not a component; nothing selects it, disables it, or supplies an
  alternative to it.
- **The direct-Copier `template/` tree.** That is a separate, monolithic
  compatibility surface (see [CLAUDE.md](../CLAUDE.md)) governed by
  `copier update`'s own three-way merge, not by this engine's composition or
  policy contracts.

## Explicit failures

Every unsupported attempt fails before any file operation, with a stable
shape a downstream client can depend on:

| Attempt | Fails as | Detail |
| --- | --- | --- |
| A policy or client names a target file/path directly | Rejected at the [organisation-policy.md](organisation-policy.md) or [ProjectSpec](project-spec.md) schema boundary — no such field exists | Schema validation error, before planning |
| A manifest declares a disposition other than `create`/`extend` | Rejected at manifest parse time | Pydantic `ValidationError` on `OutputContribution.disposition` |
| A contribution names an extension point that does not exist, or targets its own owner | Rejected at catalogue validation | `ValueError` from `component_manifest.validate_manifest_set` / manifest model validators, independent of any selection |
| Two selected owners both create the same target | Rejected at plan resolution | `ForgeEngineError(code=EngineErrorCode.GENERATION_PLAN_FAILED, operation="plan")`, naming both owners and the shared target |

The last row is the one collision a valid catalogue can still produce at
selection time (two independently valid components whose targets happen to
collide); the others are caught earlier, at authoring or catalogue-load time.
None of the four ever reaches `render_project()`'s file-writing step.

## The sanctioned route to different content

An organisation, capability author, or platform author that wants output
this catalogue does not produce has exactly one route: author or select a
component that owns the content it wants, or — if extending existing owner
content — declare a `[[contributions]]` entry into a point that owner already
publishes. A future engine release may publish a new extension point on
existing owner content; that is additive catalogue evolution, not a policy
grant. Neither policy nor a client ever gains authority to replace content
directly.

## Stability and versioning

The published inventory above is part of the compatibility surface, the same
way component IDs and manifest protocols are:

- **Adding** an extension point to existing owner content is additive and
  requires no version transition beyond the normal patch/minor release that
  ships it. [ADR 0049](adr/0049-foundation-capability-tooling-extension-points.md)
  is the worked precedent: the three capability-tooling points ship in the
  same `0.4.0` line that first makes a requirable capability visible, and the
  points alone would not have forced even that minor bump.
- **Removing or renaming** a published extension point ID is breaking: any
  contribution naming it would stop resolving. It requires a version
  transition and release-note treatment matching any other breaking
  compatibility change (see [template-engine-api.md](template-engine-api.md)).
- Extension point IDs are stable identifiers, matching the kebab-case
  convention `component-manifests.md` already applies to component and
  option identifiers.

A regression test in `tests/test_extension_points.py` pins the current
eleven-entry inventory so a removal or rename is caught rather than shipped
silently; `tests/test_capability_extension_points.py` pins the additive,
byte-neutral, composition-ordered behaviour of the three capability-tooling
points.

## Client boundary

Engine output is authoritative. `render_project()` performs
`validate_rendered_project` before returning, so every `RenderedProject` a
client receives has already passed the checks in
[generated-project-validation.md](generated-project-validation.md). Staging
that output to a filesystem, resolving `uv.lock`, and any other finalisation
step remain client responsibilities, as recorded by the Stage 08 review in
[composition-architecture-review.md](composition-architecture-review.md#lock-state-and-finalisation).
A client is free to inspect or copy rendered bytes, but editing them before
staging is client-owned behaviour with no engine guarantee attached — it is
not a documented extension mechanism, and doing so forfeits the validation
the engine already performed.

The [no-copy inheritance proof](no-copy-inheritance.md) validates the positive
side of this boundary: independent clients obtain identical plans and bytes
for equivalent effective ProjectSpecs, while additive differences remain
selected-component files or declared extension contributions.

## Ownership and deferred work

`forge-template` owns this extension-point inventory and its stability
guarantee. A downstream client owns which components it selects, how it
presents that choice, and all filesystem and finalisation work.

The generic reference fixture proving these rules against a real, neutral
example is
[FT-09.03 / #46](https://github.com/Sandsy09/forge-template/issues/46),
delivered as
[organisation-policy-fixtures.md](organisation-policy-fixtures.md)'s
test-only reference resolver -- executable, but not a shipped public parser
or resolver; that remains unscheduled, per
[ADR 0040](adr/0040-organisation-policy-reference-fixture.md). Forge/Blueprint
compatibility policy — including any versioned commitment about what future
Blueprint releases may assume — is
[compatibility-policy.md](compatibility-policy.md), delivered by
[FT-09.04 / #47](https://github.com/Sandsy09/forge-template/issues/47) and
adopted by [ADR 0041](adr/0041-forge-blueprint-compatibility-policy.md); it
governs the engine surfaces named here (component versions, the published
extension-point inventory) alongside the rest of the versioned axes it
defines. The downstream consumption hook belongs to
[create-forge#54](https://github.com/Sandsy09/create-forge/issues/54), which
already commits to using only the supported engine API and avoiding arbitrary
file overlays.

FT-09.05 closes the repository-local validation of this model through
[no-copy-inheritance.md](no-copy-inheritance.md) and
[ADR 0042](adr/0042-validate-no-copy-downstream-inheritance.md), without
turning the private test catalogue into a plugin mechanism.
