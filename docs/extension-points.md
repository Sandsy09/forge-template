# Safe override and extension points

This document answers one question the earlier composition contracts each
deferred: what may a downstream client — organisation policy, a future
Blueprint-style consumer, or a component author — safely change about
generated output, and what happens when it tries something unsafe. It is
delivered by [FT-09.02](https://github.com/Sandsy09/forge-template/issues/45)
and adopted by [ADR 0039](adr/0039-deny-policy-file-overrides.md).

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
| `content/pyproject.toml.jinja` | `pyproject-build-system`, `pyproject-archetype-metadata`, `pyproject-build-configuration`, `pyproject-runtime-dependencies`, `pyproject-classifiers`, `pyproject-entry-points` |
| `content/README.md.jinja` | `readme-project-shape` |
| `content/.gitignore.jinja` | `gitignore-project-shape` |

All eight are published by the implicit Foundation content source. **Neither
production archetype publishes an extension point of its own** — `library`
and `cli` only contribute into Foundation's points, through manifest protocol
`2`'s `target.kind = "foundation"`
([component-manifests.md](component-manifests.md#accepted-manifest-protocol-v2-target-owner)).
This is unchanged by [ADR 0037](adr/0037-two-archetype-composition-review.md):
the Stage 08 review found no new point was required.

Foundation owns six further files with **no** extension point at all:
`.editorconfig`, `.gitattributes`, `.python-version.jinja`,
`CONTRIBUTING.md.jinja`, `LICENSE.jinja`, and `SECURITY.md.jinja`. These are
sole-owner `create` content, deliberately not extensible — stated here rather
than left to be inferred from the absence of a declaration.

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
  ships it.
- **Removing or renaming** a published extension point ID is breaking: any
  contribution naming it would stop resolving. It requires a version
  transition and release-note treatment matching any other breaking
  compatibility change (see [template-engine-api.md](template-engine-api.md)).
- Extension point IDs are stable identifiers, matching the kebab-case
  convention `component-manifests.md` already applies to component and
  option identifiers.

A regression test in `tests/test_extension_points.py` pins the current
inventory so a removal or rename is caught rather than shipped silently.

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

## Ownership and deferred work

`forge-template` owns this extension-point inventory and its stability
guarantee. A downstream client owns which components it selects, how it
presents that choice, and all filesystem and finalisation work.

The generic reference fixture proving these rules against a real, neutral
example is [FT-09.03 / #46](https://github.com/Sandsy09/forge-template/issues/46).
Forge/Blueprint compatibility policy — including any versioned commitment
about what future Blueprint releases may assume — is
[FT-09.04 / #47](https://github.com/Sandsy09/forge-template/issues/47). The
downstream consumption hook belongs to
[create-forge#54](https://github.com/Sandsy09/create-forge/issues/54), which
already commits to using only the supported engine API and avoiding arbitrary
file overlays. Executable organisation-policy parsing and resolution remain
[FT-09.01](organisation-policy.md#ownership-and-deferred-implementation)'s
standing deferral; this document does not implement it.
