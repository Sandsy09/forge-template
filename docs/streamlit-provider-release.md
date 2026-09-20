# Reviewed forge-template 0.6.0 release

This is FT-20.04's evidence record: the reviewed Streamlit provider line is
tagged, released and published, and its artefacts are audited against PyPI. It
is the canonical answer to
[FT-20.04 / #162](https://github.com/Sandsy09/forge-template/issues/162), the
final child of
[FT-EPIC-20 / #145](https://github.com/Sandsy09/forge-template/issues/145), and
executes a decision already accepted by
[ADR 0069](adr/0069-streamlit-composition-compatibility-and-acceptance.md) /
[streamlit-compatibility-and-acceptance.md](streamlit-compatibility-and-acceptance.md)
(FT-19.02): the `0.6.0` line, the two axes it moves, the provider gate and the
rollback rule. FT-20.04 adds no new decision and files no ADR; it runs the one
already made. This document is the direct analogue, one roadmap later, of
[cutover-provider-release.md](cutover-provider-release.md) (FT-17.06's `0.5.0`
record), which stays the immutable `0.5.0` record, untouched by this release.

FT-20.01 to FT-20.03 (all merged on `main`) implemented and validated the
`streamlit` archetype
([ADR 0070](adr/0070-streamlit-archetype-implementation.md),
[0071](adr/0071-streamlit-tasks-safeguards-and-composition.md),
[0072](adr/0072-validate-streamlit-generated-projects.md)). None of it was
reachable by a client until this release: merging is not releasing
([CONTRIBUTING.md](../CONTRIBUTING.md#releasing)), and every commit since
`4ac39d9` (the `0.5.0` prepare commit) was invisible to `copier update` and to
a version-pinned engine client until this issue ran the protected release.

## The release chain

| Step | Evidence |
| --- | --- |
| Prepare | [PR #184](https://github.com/Sandsy09/forge-template/pull/184) `chore: prepare forge-template 0.6.0`, squash commit `f358240f6c9fad24cde81d649cc1fdea96895eeb`; protected checks 13/13 on the PR head `0dfd37830fb6a5e9d9b76c10188c0272d1b32f4b` |
| Protected `main` gate | [run 35516420106](https://github.com/Sandsy09/forge-template/actions/runs/35516420106) on the merge commit: success, 13 of 13 jobs, `All checks passed` green |
| Release candidate | `uv run poe check:wheel` on the merged commit: ok, wheel 115,232 bytes, sdist 810,398 bytes |
| Release dry run | [run 35517122107](https://github.com/Sandsy09/forge-template/actions/runs/35517122107): dispatched from `main` at `f358240`, derived `v0.5.0` to `v0.6.0`, created nothing (`Create tag` and `GitHub release` skipped, the whole `Publish to PyPI` job skipped); `Warn on breaking template changes` was silent |
| Release run | [run 35539758128](https://github.com/Sandsy09/forge-template/actions/runs/35539758128): `release` and `Publish to PyPI` both succeeded |
| Tag and GitHub Release | [`v0.6.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.6.0), an annotated tag by `github-actions[bot]`, at commit `f358240f6c9fad24cde81d649cc1fdea96895eeb`; the Release is neither a draft nor a prerelease |
| PyPI | [`forge-template 0.6.0`](https://pypi.org/project/forge-template/0.6.0/), `Requires-Python >=3.11`, not yanked |

`git rev-list -n1 v0.6.0` confirms the tag names exactly PR #184's squash
commit, and `origin/main` was still that commit when the release ran: the tag,
the GitHub Release and the PyPI artefacts all name one commit SHA.

The release notes generated from `git log v0.5.0..HEAD --no-merges`:

```text
- chore: prepare forge-template 0.6.0 (#184)
- test: validate Streamlit generated projects and distributions (#183)
- feat: add the Streamlit run task, safeguards and capability composition (#182)
- feat: implement the independent Streamlit archetype (#181)
- docs: define Streamlit composition, compatibility and acceptance (#180)
- docs: define the Streamlit project shape and ownership (#179)
- test: validate the integrated engine-default cutover (FT-18.01) (#178)
- docs: consolidate repository guidance
- docs: complete Stage 17 release (#174)
```

## Published artefacts

| Artefact | Size | SHA-256 | Uploaded (UTC) |
| --- | --- | --- | --- |
| `forge_template-0.6.0-py3-none-any.whl` | 115,232 bytes | `cf21152242a81b6a19d5298521a77f504063091759b5cca721b3f527c64ac742` | 2026-09-20 21:48:22 |
| `forge_template-0.6.0.tar.gz` | 810,268 bytes | `07e036a582d038f704c5678a75d93c75cec186e8fb138b75ae08d933dd0b9db8` | 2026-09-20 21:48:24 |

Both were downloaded directly from `files.pythonhosted.org` (never from this
checkout) and verified against PyPI's own JSON API metadata for both size and
hash. Wheel `METADATA` and sdist `PKG-INFO` both report `0.6.0`.

These are not the digests `poe check:wheel` printed on the release candidate
(`6d5fbc...` and `8f4b9d...`). That task builds from a Windows working tree; the
release builds from a Linux checkout in CI, and a wheel archive embeds build
metadata, so the two builds do not share a digest. The published files are the
record, and the audit below is of them.

## What `0.6.0` changes

Deliberately the narrow inverse of `0.5.0`'s "everything Stage 17 built": this
release moves exactly the two axes ADR 0069 classified, and nothing else.

- **One new component**, `streamlit` `1.0.0`, an archetype on manifest
  protocol `2` with no `requires`, `conflicts` or options.
  `discover_components()` grows from fourteen to fifteen, and `streamlit`
  sorts last, after `scientific-python`. It owns seven paths
  (`app.py`, `src/<package>/{__init__,app}.py`, `py.typed`,
  `tests/{__init__,test_app}.py`, `.streamlit/config.toml`) and nine Foundation
  contributions, all through published extension points.
- **The package version**, `0.5.0` to `0.6.0`, a new minor line. Below `1.0` a
  supported range is minor-scoped, so `create-forge` `0.4.0`'s
  `>=0.5,<0.6` does not drift into it.
- **Unchanged:** the public facade (every name, signature and result field),
  `EngineErrorCode`, the ProjectSpec protocol (`1`), the component-manifest
  protocols (`1`, `2`, `3`), the option-schema protocols, `metadata_version`
  (`1`), the sixteen Foundation extension points, `foundation_version` (`1`),
  the fourteen existing components and their versions, `template/` and
  `copier.yml`.

Every addition is additive: nothing exported from `forge_template` was renamed,
removed or narrowed, and no deprecation was opened.

## Published-artefact audit

Downloaded both the `0.6.0` and `0.5.0` wheels and the `0.6.0` sdist directly
from PyPI, verified each against its own JSON API metadata, and checked:

| Check | Result |
| --- | --- |
| Wheel and sdist size and SHA-256 match PyPI JSON API; neither yanked | Pass |
| Wheel `METADATA` / sdist `PKG-INFO` report `0.6.0`; `Requires-Python >=3.11`; runtime dependencies `jinja2`, `packaging`, `pydantic` only | Pass |
| Isolated venv installs the downloaded wheel with only those and their transitive dependencies, and imports from `site-packages`, not this checkout | Pass |
| Installed package reports the negotiation payload: `package_version=0.6.0`, `projectspec_protocols=(1,)`, `component_manifest_protocols=(1,2,3)`, `metadata_version=1` | Pass |
| Discovery returns fifteen components; `streamlit` is last, an archetype at `1.0.0` with no `requires`, `conflicts` or options | Pass |
| Wheel ships fifteen manifests, `py.typed`, `foundation/foundation.toml`, `engine.py`, `project_spec.py`, and the whole `streamlit` tree (17 files, the hidden `.streamlit/config.toml` included) | Pass |
| Wheel excludes `adr.py`, `render.py`, `schema.py`, `github_actions.py` | Pass |
| The sdist carries the same `streamlit` tree name for name (17 and 17) | Pass |
| **Delta against the published `0.5.0` wheel** (payload, `dist-info` excluded) | 17 files added, all under `components/streamlit/`; none removed; every shared file byte-identical |
| **Every accepted Streamlit composition renders from the installed wheel**: all 2,048 subsets of the ten capabilities and the platform were tried | 640 derived from the discovered `requires` and `conflicts` edges and 640 rendered; the engine's own accept or reject decision agreed with the derivation for every subset, in both directions |
| Invalid selections are rejected, not rendered (`documentation`, which requires `library`; `dependabot` without `github`) | Pass: `invalid-selection` |
| The four accepted selections (none, `jupyter`, `scientific-python`, both) render from the wheel with `app.py`, `src/<package>/app.py`, `tests/test_app.py`, `.streamlit/config.toml`, the `run` task, the `streamlit>=1.63,<2` bound, the secrets ignore rule and `gatherUsageStats = false` | Pass |
| `uv lock` resolves each of the four; no generated lock names `forge-template` or `create-forge` | Pass |
| Maximal selection (`jupyter` and `scientific-python`): `uv sync --all-groups --locked`, then `uv run --locked poe check` | Pass |
| A wheel built from the downloaded sdist installs and reports the same negotiation facts, and its 140-file payload is byte-identical to the published wheel's | Pass |

This audit script was disposable tooling, not committed to this repository, the
same precedent FT-12.04, FT-14.03 and FT-17.06 set. Its first pass reported one
failure that was a defect in the script, not in the release: it compared each
component's `requires` entries (relation objects) with ids, so every selection
that carried a `requires` edge (`dependabot` with `github`) was skipped and it
derived 512 compositions rather than 640. All 512 rendered. A corrected pass
compares ids, as the engine's own `tests/composition_matrix.py` does, and
additionally checks the engine's decision for every subset rather than only the
ones the derivation admits; its result is the row above.

## Direct-Copier regression

The protected `main` gate above carried this row: its `scaffold` job (all four
combinations, including the kitchen sink), `windows` job and
`update-compat` job all passed against the tagged commit. `template/` and
`copier.yml` are **byte-identical** to `v0.5.0`: `git diff v0.5.0..v0.6.0` over
those two paths is empty. So `copier update` keeps working unchanged for
every project already scaffolded from a tag, and no `_migrations` block was
required. `uv run poe combos` and `uv run poe update`, the two Copier-ladder
rows the acceptance matrix assigns to this issue, are therefore carried by that
run rather than repeated locally.

## Provider hand-off and supported bounds

This release is an immutable, reviewed target. Released `create-forge`
`0.4.0` declares `forge-template>=0.5,<0.6`
([template-engine-api.md](template-engine-api.md#compatibility-and-current-cutover-boundary))
and is **unaffected** by this publication: it continues to resolve, install and
generate against the `0.5.x` line exactly as before. Widening that bound to
`>=0.6,<0.7`, refreshing the lock and adding client tests is a deliberate,
reviewed client change,
[CF-21.01](https://github.com/Sandsy09/create-forge/issues/165)'s to make, not
this release's.

The `0.5.x` line stays installable and supported for the compatibility policy's
[deprecation window](compatibility-policy.md#deprecation-windows), so a client
that hits a `0.6.0` defect can pin back and keep generating while a fix ships as
`0.6.1`. `0.5.0` is **not** yanked, and `0.6.0` itself is never mutated: a
defect is corrected forward, exactly as
[ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md)
decision 5 and the contract's rollback rule state.

The immutable target a client adopts:

| Fact | Value |
| --- | --- |
| Tag | `v0.6.0` (annotated) |
| Commit | `f358240f6c9fad24cde81d649cc1fdea96895eeb` |
| Package bounds a client should declare | `forge-template>=0.6,<0.7` |
| Component identity | `streamlit`, `archetype`, `1.0.0`, manifest protocol `2`, `>=3.11` |
| Discovered components | fifteen, `streamlit` last |

This section is the hand-off for
[CF-21.01](https://github.com/Sandsy09/create-forge/issues/165): it records the
tag, commit, package bounds and component identity, and claims neither client
Streamlit support nor an engine-default switch. Nothing in the `create-forge`
repository was changed by this issue.

## What this does not prove

- **A `create-forge` adoption or release.** Widening the engine bound,
  refreshing the lock, and the client's installed Streamlit validation are
  [CF-21.01](https://github.com/Sandsy09/create-forge/issues/165),
  [CF-21.02](https://github.com/Sandsy09/create-forge/issues/166) and
  [CF-21.03](https://github.com/Sandsy09/create-forge/issues/167), out of scope
  for this issue by its own stated exclusions.
- **Client Streamlit support.** No released client selects `streamlit` yet;
  Streamlit is reachable only through the engine.
- **An engine-default switch.** This release makes none
  (FT-ROADMAP-02-EX-03). The cutover shipped separately, in `forge-template`
  `0.5.0` and `create-forge` `0.4.0`; the direct-Copier Library path is
  unchanged and un-deprecated.
- **`1.0.0`.** Not promised by this release or by ADR 0069; it remains a later
  decision.

## Recorded during the release: the crossrepo lag

`poe crossrepo` against the sibling `../create-forge` checkout (unmodified, at
`6435884`) was run once after the release. FT-20.03 recorded it green (20
passed) while the engine was still `0.5.0`; the outcome is now a total,
single-cause failure at dependency resolution, before any generation:

```text
create-forge==0.4.0 depends on forge-template>=0.5,<0.6, ... we can
conclude that create-forge==0.4.0 cannot be used.
```

The run reported one failure and nineteen errors in about ten seconds, and all
twenty items trace to that one unsatisfiable resolution. Nineteen are fixture
errors, because the paired environment installs both local working trees and
`create-forge` `0.4.0` declares `forge-template>=0.5,<0.6`, which the local
`0.6.0` engine is outside. The twentieth,
`test_create_forge_cross_repository_contract_passes_against_the_local_engine`,
runs `create-forge`'s own contract tests through the same two-package
resolution and fails the same way. None of the twenty reached generation, so
this run says nothing about the archetype either way.

This is not a defect. It is the compatibility policy's fail-closed contract
working as designed: a minor-scoped range below `1.0` does not drift into the
next minor, and `0.5.0` published the same way against `create-forge` `0.3.2`
(see [cutover-provider-release.md](cutover-provider-release.md#recorded-during-preparation-the-crossrepo-lag-deepened-as-expected)).
`poe crossrepo` is deliberately absent from CI
([ADR 0057](adr/0057-validate-the-cross-repository-data-science-line.md)), so no
protected job depends on it. It stays red until
[CF-21.01](https://github.com/Sandsy09/create-forge/issues/165) widens the
client's bound to `>=0.6,<0.7`, and it is that issue's to clear. Nothing in
`../create-forge` was changed here.

The client-observable proof that the `0.6.0` artefacts render and install is
the isolated audit above, which uses no `create-forge` at all.

## Downstream adoption

This release gives `create-forge` an immutable reviewed target to widen its
engine bound against, at
[CF-21.01](https://github.com/Sandsy09/create-forge/issues/165), which was
blocked on it. Released `create-forge` `0.4.0` is unaffected in the meantime: it
keeps resolving, installing and generating against `forge-template>=0.5,<0.6`,
which stays installable through the compatibility policy's support window.
