# Reviewed forge-template 0.5.0 release

This is FT-17.06's evidence record: the reviewed engine-default cutover
provider line is tagged, released, and published, and its artefacts are
audited against PyPI. It is the canonical answer to
[FT-17.06 / #155](https://github.com/Sandsy09/forge-template/issues/155), the
final child of
[FT-EPIC-17 / #142](https://github.com/Sandsy09/forge-template/issues/142),
and executes a decision already accepted by
[ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md) /
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md)
(FT-15.04) — the `0.5.0` line, the reasons it is not `1.0.0`, and the
immutable-release / `0.4.x`-support-window rules. FT-17.06 adds no new
decision; it runs the one already made. This document is the direct analogue,
one roadmap later, of [reviewed-engine-release.md](reviewed-engine-release.md)
(FT-14.03's `0.4.1` record) — that document stays the immutable `0.4.1`
record, untouched by this release.

FT-17.01 through FT-17.05 (all merged on `main`) implemented every provider
change the cutover moves: manifest protocol `3`, published `metadata_version`,
the `github` platform and eight tooling capabilities, the `plan_update`
reproducible-render surface, and the full acceptance-matrix execution. None of
it was reachable by a client until this release: merging is not releasing
([CONTRIBUTING.md](../CONTRIBUTING.md#releasing)), and every commit since
`9f7ed81` (the `0.4.1` prepare commit) was invisible to `copier update` and to
a version-pinned engine client until this issue ran the protected release.

## The release chain

| Step | Evidence |
| --- | --- |
| Prepare | [PR #173](https://github.com/Sandsy09/forge-template/pull/173) `chore: prepare forge-template 0.5.0`, squash commit `4ac39d9b3518411becf9978966c342be462f8227` |
| Protected `main` gate | [run 34699798870](https://github.com/Sandsy09/forge-template/actions/runs/34699798870) — success, every job including both `sweep-composition` / `sweep-independence` jobs |
| Release dry run | [run 34700275258](https://github.com/Sandsy09/forge-template/actions/runs/34700275258) — derived `v0.4.1` → `v0.5.0` against commit `4ac39d9b3518411becf9978966c342be462f8227`, displayed the release notes below, created no tag, release, or PyPI file (`Create tag` / `GitHub release` steps and the whole `Publish to PyPI` job report `skipped`); the `Warn on breaking template changes` step was silent |
| Release run | [run 34701562379](https://github.com/Sandsy09/forge-template/actions/runs/34701562379) — `release` and `Publish to PyPI` jobs both succeeded |
| Tag + GitHub Release | [`v0.5.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.5.0) at commit `4ac39d9b3518411becf9978966c342be462f8227` |
| PyPI | [`forge-template 0.5.0`](https://pypi.org/project/forge-template/0.5.0/) |

`git rev-list -n1 v0.5.0` confirms the tag names exactly PR #173's squash
commit — the tag, the GitHub Release, and the PyPI artefacts all name one
commit SHA (P2's first requirement).

The release notes generated from `git log v0.4.1..HEAD --no-merges`:

```text
- chore: prepare forge-template 0.5.0 (#173)
- test: validate provider parity, reproducibility and distributions (#172)
- feat: implement reproducible rendering for engine updates (#153)
- feat: ship the approved generated-content capabilities (#152)
- feat: implement the github platform component (#151)
- feat: implement provider provenance and public metadata contracts (#150)
- docs: define provider compatibility, failure and release gates (#149)
- docs: define platform composition and generated-tooling parity (#148)
- docs: define generation provenance and reproducible-update inputs (#147)
- docs: inventory default-Copier parity and assign ownership (#146)
- docs: record filed cross-repository roadmaps
- docs: prepare engine-default and Streamlit roadmap packs
- chore: add bounded uv dependency updates for forge-template
- docs: reconcile living provider documentation with the 0.4.1 release
- docs: simplify template README and improve feedback routes (#135)
- docs: reconcile the cross-repository matrix after the create-forge 0.3.0 release (#134)
- docs: complete Stage 14 release
```

## Published artefacts

| Artefact | Size | SHA-256 |
| --- | --- | --- |
| `forge_template-0.5.0-py3-none-any.whl` | 108,247 bytes | `dffaad1eae884856a3828edc2a31f889fcb44f233b6e19c85dc7d2cc9fc6a023` |
| `forge_template-0.5.0.tar.gz` | 738,075 bytes | `4bcd49a43749d73b2c7bb38122211b1824078470276706d4aa3608d15fd612ba` |

Both were downloaded directly from `files.pythonhosted.org` (never from this
checkout) and verified against PyPI's own JSON API metadata for both size and
hash. Wheel `METADATA` and sdist `PKG-INFO` both report `0.5.0`.

## What `0.5.0` changes

Deliberately the honest inverse of `0.4.1`'s "nothing in the catalogue"
([reviewed-engine-release.md](reviewed-engine-release.md#what-041-changes)):
this is the cutover release, and it changes everything Stage 17 built,
additively.

- **Nine new components**, `discover_components()` growing from five to
  fourteen: the first `kind = "platform"` component, `github` `1.0.0`
  (FT-17.02), and the eight FT-17.03 tooling capabilities — `changelog`
  `1.0.0` (first shipped `manifest_version = 3`), `coverage` `1.0.0`,
  `dependabot` `1.0.0`, `documentation` `1.0.0`, `dotenv-example` `1.0.0`,
  `pre-commit` `1.0.1` (already carrying FT-17.05's `check-added-large-files`
  lockfile-exclusion fix), `pyright` `1.0.0`, `renovate` `1.0.0`.
- **Component-manifest protocol** `(1, 2, 3)` — protocol `3`'s `[[renames]]` /
  `[[regeneration]]` records, published by FT-17.01; protocol-`1` and
  protocol-`2` manifests still accepted unchanged.
- **Generation metadata** — `metadata_version = 1` published through
  `get_engine_info()`, the `GenerationMetadata` hand-off surface on
  `RenderedProject.metadata`, `parse_generation_metadata` /
  `verify_generation_metadata`, and the two `EngineErrorCode` values
  (FT-17.01).
- **The reproducible-render update surface** — `plan_update(recorded, *, old,
  new) -> UpdatePlan`, and `UpdatePlan`'s nested `UpdateTarget` /
  `AppliedRename` models (FT-17.04).
- **Foundation's extension-point inventory**, 11 → 16: three host-link points
  (`pyproject-project-urls`, `contributing-project-shape`,
  `security-project-shape`, FT-17.02) and two `[dependency-groups]` points
  (`pyproject-named-dependency-groups`, `pyproject-dependency-group-includes`,
  FT-17.03). `foundation_version` stays `1` — these are new points on the
  existing protocol-`1` shape, not a protocol move, exactly as FT-11.01
  established the pattern.
- **`library` / `cli` / `data-science` / `jupyter` / `scientific-python`**
  unchanged in content and version (`1.0.1` / `1.0.1` / `1.0.0` / `1.0.0` /
  `1.0.0`) — no archetype gained a `ci-jobs` fill this cutover.

Every addition is additive: nothing exported from `forge_template` was
renamed, removed, or narrowed, and no deprecation was opened.

## Published-artefact audit

Downloaded both the `0.5.0` and `0.4.1` wheels and the `0.5.0` sdist directly
from PyPI (never from this repository's own source), verified each against
its recorded SHA-256, and checked:

| Check | Result |
| --- | --- |
| Wheel/sdist SHA-256 match PyPI JSON API metadata | Pass |
| Wheel `METADATA` / sdist `PKG-INFO` report `0.5.0` | Pass |
| Isolated venv installs the downloaded wheel with only its declared runtime dependencies (`jinja2`, `packaging`, `pydantic`) | Pass |
| Installed package reports the full negotiation payload: `package_version=0.5.0`, `projectspec_protocols=(1,)`, `component_manifest_protocols=(1,2,3)`, `metadata_version=1`, all fourteen component ids and versions | Pass |
| The four additive `plan_update` facade names (`plan_update`, `UpdatePlan`, `UpdateTarget`, `AppliedRename`) import from the installed wheel | Pass |
| Wheel ships every manifest, owned content and `extensions/` tree, `py.typed`, `engine.py`, `project_spec.py`, `foundation.toml` | Pass |
| Wheel excludes `adr.py`, `render.py`, `schema.py`, `github_actions.py` | Pass |
| **Delta against the published `0.4.1` wheel**: `forge_template/foundation/` + `forge_template/components/` | Nine new component trees added (five → fourteen components); four Foundation files (`foundation.toml`, `pyproject.toml.jinja`, `CONTRIBUTING.md.jinja`, `SECURITY.md.jinja`) gained only the new extension-point declarations/markers FT-17.02 and FT-17.03 added — `foundation_version` unchanged at `1`; every other shared file byte-identical |
| Sdist correctly carries the full repository (`adr.py`, `tests/`, `docs/`, `template/` all present — by design, no `[tool.hatch.build.targets.sdist]` override) | Pass |
| A wheel built from the downloaded sdist, in isolation, installs and reports the same negotiation facts | Pass |
| Render a maximal `library` composition (`github` + all compatible capabilities) from the installed `0.5.0` package into a temp project; `uv lock`, `uv sync --all-groups --locked`, `uv run --locked poe check` (lint, mypy, tests, coverage, notebook check, pyright) | Pass |
| Generated `uv.lock` names neither `forge-template` nor `create-forge` | Pass |

This audit script was disposable tooling, not committed to this repository —
the same precedent FT-12.04's `0.4.0` audit and FT-14.03's `0.4.1` audit set.

## Direct-Copier regression (R2)

The protected `main` gate above ([run 34699798870](https://github.com/Sandsy09/forge-template/actions/runs/34699798870))
carried this row: its `scaffold` job (all four combos, including the kitchen
sink), `windows` job, and `update-compat` job all passed against the tagged
commit. `template/` and `copier.yml` are **byte-identical** to `v0.4.1` — `git
diff v0.4.1..v0.5.0 -- template/ copier.yml` is empty — so `copier update`
keeps working unchanged for every project already scaffolded from a tag, and
no `_migrations` block was required.

## Provider hand-off and supported bounds (P3)

This release is an immutable, reviewed target. Released `create-forge`
(`0.3.2`) still declares `forge-template>=0.4.1,<0.5`
([template-engine-api.md](template-engine-api.md#compatibility-and-current-cutover-boundary))
and is **unaffected** by this publication — it continues to resolve, install,
and generate against the `0.4.x` line exactly as before. Widening that bound
to `>=0.5,<0.6` is a deliberate, reviewed client change,
[CF-18.01](https://github.com/Sandsy09/create-forge/issues/158)'s to make, not
this release's. The `0.4.x` line stays installable and supported for the
compatibility policy's window — at least 90 days and at least one further
tagged release past this cutover — so a client that hits a `0.5.0` defect can
pin back and keep generating while a fix ships as `0.5.1` (or a new line);
`0.5.0` itself is never mutated.

A hand-off comment recording this — the immutable target, its commit SHA, and
an explicit statement that client cutover has **not** shipped — was posted on
create-forge's [#158](https://github.com/Sandsy09/create-forge/issues/158)
(CF-18.01) and [#153](https://github.com/Sandsy09/create-forge/issues/153).
No label or content in that repository was changed.

## What this does not prove

- **A `create-forge` adoption or release.** Widening the engine bound,
  refreshing the lock, and the client's own regression evidence against the
  new line is [CF-18.01](https://github.com/Sandsy09/create-forge/issues/158)
  — out of scope for this issue by its own stated exclusions.
- **The integrated cross-repository cutover.** Pairing the released provider
  with the candidate client and running the full acceptance matrix together is
  [FT-18.01 / #156](https://github.com/Sandsy09/forge-template/issues/156).
- **A default-path switch.** `create-forge new --engine-preview` remains a
  hidden preview; the direct-Copier Library path is unchanged and
  un-deprecated.
- **`1.0.0`.** Not promised by this release or by ADR 0061; it remains a later
  decision.

## Recorded during preparation: the crossrepo lag deepened, as expected

`poe crossrepo` against the sibling `../create-forge` checkout (not modified)
was run again after this release, for comparison against FT-17.05's recorded
partial lag. The outcome is now a near-total, single-cause fail-closed
rejection rather than four isolated helper failures: released `create-forge`'s
own CLI negotiation now refuses `forge-template 0.5.0` outright, because it is
outside its declared `>=0.4.1,<0.5` range —

```text
--engine-preview is a hidden preview path (ADR 0014).
Detected forge-template 0.5.0, but this create-forge release supports
forge-template>=0.4.1,<0.5. Run `pip install 'forge-template>=0.4.1,<0.5'`
(or the equivalent `uv add`/`uv sync` invocation) to install a compatible
version.
```

19 of 20 non-passing crossrepo test items trace to exactly that one message
(the direct assertion `test_installed_engine_metadata_matches_the_reviewed_candidate`,
four rejection-message-content mismatches where the CLI now fails earlier at
negotiation, and 13 fixture-setup errors that all depend on
`create-forge new --engine-preview` actually running). This is not a defect —
it is the compatibility policy's fail-closed negotiation contract
([compatibility-policy.md](compatibility-policy.md#reporting-an-unsupported-forge-version))
working exactly as designed against a real, published, out-of-range engine.
The 20th, `test_create_forge_cross_repository_contract_passes_against_the_local_engine`,
is the pre-existing `metadata_version`-missing lag FT-17.05 already recorded
in [provider-acceptance-validation.md](provider-acceptance-validation.md) — a
raw `EngineInfo(...)` construction in create-forge's own test file, unrelated
to the version bound. Both lags are owned by CF-18.01 / FT-18.01. No
create-forge change was made.

## Downstream adoption

This release gives `create-forge` an immutable reviewed target to widen its
engine bound against, once CF-18.01 is scheduled. Released `create-forge
0.3.2` is unaffected in the meantime — it keeps resolving, installing, and
generating against `forge-template>=0.4.1,<0.5`, which stays installable
through the compatibility policy's support window.
