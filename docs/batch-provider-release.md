# Reviewed forge-template 0.7.0 release

This is FT-28.03's evidence record: the reviewed batch provider line is
tagged, released and published, and its artefacts are audited against PyPI. It
is the canonical answer to
[FT-28.03 / #203](https://github.com/Sandsy09/forge-template/issues/203), the
final child of
[FT-EPIC-28 / #190](https://github.com/Sandsy09/forge-template/issues/190), and
executes a decision already accepted by
[ADR 0081](adr/0081-batch-composition-compatibility-and-acceptance.md) /
[batch-compatibility-and-acceptance.md](batch-compatibility-and-acceptance.md)
(FT-27.02): the `0.7.0` line, the two axes it moves, the provider gate and the
rollback rule. FT-28.03 adds no new decision and files no ADR; it runs the one
already made, and completes the Copier floor
[ADR 0073](adr/0073-scaffold-tasks-run-only-on-copy.md) had already decided. This
document is the direct analogue, one roadmap later, of
[streamlit-provider-release.md](streamlit-provider-release.md) (FT-20.04's
`0.6.0` record), which stays the immutable `0.6.0` record, untouched by this
release.

FT-28.01 and FT-28.02 (both merged on `main`) implemented and validated the
`batch` archetype
([ADR 0082](adr/0082-batch-archetype-implementation.md),
[0083](adr/0083-validate-batch-generated-projects.md)). None of it was
reachable by a client until this release: merging is not releasing
([CONTRIBUTING.md](../CONTRIBUTING.md#releasing)), and every commit since
`f358240` (the `0.6.0` prepare commit) was invisible to `copier update` and to
a version-pinned engine client until this issue ran the protected release.

## The release chain

| Step | Evidence |
| --- | --- |
| Prepare | [PR #226](https://github.com/Sandsy09/forge-template/pull/226) `chore: prepare forge-template 0.7.0`, squash commit `8d12452cfdc9bcae942d885a6ba93587130d8d26`; protected checks 27 of 27 on the PR head `3792752cf27dc1fd74e52a4928571c53f12918a0` ([run 37464166243](https://github.com/Sandsy09/forge-template/actions/runs/37464166243)) |
| Protected `main` gate | [run 37466333385](https://github.com/Sandsy09/forge-template/actions/runs/37466333385) on the merge commit: success, 16 of 16 jobs, `All checks passed` green, both composition sweeps and the copier-update, kitchen-sink and Windows jobs included |
| Release candidate | `uv run poe check:wheel` on the merged commit: ok, wheel 128,920 bytes (ceiling 131,072), sdist 1,191,163 bytes |
| Release dry run | [run 37468612887](https://github.com/Sandsy09/forge-template/actions/runs/37468612887): dispatched from `main` at `8d12452`, derived `v0.6.0` to `v0.7.0`, `Dependency audit`, `Exhaustive tier evidence` and `release` succeeded, `Create tag` and `GitHub release` skipped and the whole `Publish to PyPI` job skipped, so it created nothing; `Warn on breaking template changes` was silent |
| Release run | [run 37470916166](https://github.com/Sandsy09/forge-template/actions/runs/37470916166): `Dependency audit`, `Exhaustive tier evidence`, `release` and `Publish to PyPI` all succeeded |
| Tag and GitHub Release | [`v0.7.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.7.0), an annotated tag (object `8d2610c72ac65e231c9adeb4d0bff624fde1dfd0`) by `github-actions[bot]` at commit `8d12452cfdc9bcae942d885a6ba93587130d8d26`; the Release is neither a draft nor a prerelease |
| PyPI | [`forge-template 0.7.0`](https://pypi.org/project/forge-template/0.7.0/), `Requires-Python >=3.11`, not yanked |

`git rev-list -n1 v0.7.0` confirms the tag names exactly PR #226's squash
commit, and `origin/main` was still that commit when the release ran: the tag,
the GitHub Release and the PyPI artefacts all name one commit SHA. The release
workflow now also refuses to run unless the dependency audit is clean
([ADR 0075](adr/0075-audit-locked-dependencies-with-uv-audit.md)) and the
release commit's own push run has both composition sweeps green
([ADR 0077](adr/0077-implement-validation-tiers-and-thresholds.md)); both
gates ran, for the dry run and for the real release, and passed.

The release notes generated from `git log v0.6.0..HEAD --no-merges`:

```text
- chore: prepare forge-template 0.7.0 (#226)
- test: validate batch generated projects and distributions (#225)
- feat: implement the independent batch archetype (#223)
- docs: define batch composition, compatibility and acceptance (#222)
- docs: define the scheduling-neutral batch project contract (#221)
- test: verify the decomposed engine as installed artefacts and clients (#220)
- refactor: extract discovery, rendering and provenance engine internals (#219)
- test: freeze the engine compatibility baseline and internal seams (#218)
- docs: synchronise the roadmap mirror and issue tracking conventions (#215)
- ci: implement validation tiers, sweep escalation and regression thresholds (#213)
- docs: approve composition validation budgets and tiers (#212)
- ci: audit locked dependencies for known vulnerabilities (#211)
- ci: keep test temp data off the ubuntu-26.04 tmpfs (#210)
- ci: pin the Ubuntu runner baseline and add a 26.04 canary (#208)
- fix: run scaffold tasks only on copy, not update (#204) (#205)
- chore: bump ruff from 0.16.6 to 0.16.8 in the dev-tooling group across 1 directory (#176)
- ci: bump astral-sh/setup-uv from 10.0.1 to 10.1.0 (#175)
- docs: complete Stage 20 release (#185)
```

## Published artefacts

| Artefact | Size | SHA-256 | Uploaded (UTC) |
| --- | --- | --- | --- |
| `forge_template-0.7.0-py3-none-any.whl` | 128,920 bytes | `edaf0604fbfdc746c5ba6c5bd4b42b080919b8fa421b04d6f08345b6d89e37a3` | 2026-10-06 13:28:16 |
| `forge_template-0.7.0.tar.gz` | 1,191,052 bytes | `7d0e236422ab30837564ff030993b9edb8e7410a6f370a28aa4f0203c6b85580` | 2026-10-06 13:28:18 |

Both were downloaded directly from `files.pythonhosted.org` (never from this
checkout) and verified against PyPI's own JSON API metadata for both size and
hash. Wheel `METADATA` and sdist `PKG-INFO` both report `0.7.0`.

These are not the digests `poe check:wheel` printed on the release candidate
(`b82590b0...` for the wheel, and a sdist of 1,191,163 bytes with digest
`ed09a08f...`). That task builds from a Windows working tree; the release builds
from a Linux checkout in CI, and an archive embeds build metadata, so the two
builds do not share a digest. The published files are the record, and the audit
below is of them. The wheel is 128,920 bytes in both builds, so the 131,072-byte
ceiling still has about 2.1 KiB of headroom, and nothing was raised.

## What `0.7.0` changes

This release moves the two axes ADR 0081 classified, and carries three further
groups of changes that merged after `0.6.0` and none of which changes a
client-observable contract.

- **One new component**, `batch` `1.0.0`, an archetype on manifest protocol `2`
  with no `requires`, `conflicts` or options. `discover_components()` grows
  from fifteen to sixteen, and `batch` sorts first, before `changelog`. It owns
  the seven paths of the [archetype contract](batch-archetype.md#reserved-generated-shape)
  and contributes through published Foundation extension points only.
- **The package version**, `0.6.0` to `0.7.0`, a new minor line. Below `1.0` a
  supported range is minor-scoped, so `create-forge` `0.5.0`'s `>=0.6,<0.7`
  does not drift into it.
- **The engine decomposition** (FT-25, [ADR 0079](adr/0079-decompose-the-engine-behind-a-frozen-facade.md)).
  `engine.py` became a facade over six private modules (`_discovery`,
  `_errors`, `_legacy_answers`, `_models`, `_provenance`, `_rendering`), which
  are the six files the wheel delta shows added beside the batch tree. It was
  held byte-for-byte compatible by the frozen facade baseline and the
  per-composition fingerprints, and was verified as installed artefacts by
  `poe pairing`. No export, signature, error code or protocol integer moved.
- **Copy-only scaffold tasks** ([ADR 0073](adr/0073-scaffold-tasks-run-only-on-copy.md)).
  `copier.yml` guards the git bootstrap and hook installation with
  `_copier_operation == 'copy'`, so an idle `copier update` no longer fails on
  an empty commit. See "Direct-Copier regression" below, including the one
  correction this release review made to it.
- **Tooling only**, with no packaged effect: validation tiers, the dependency
  audit, the Ubuntu runner baseline and the roadmap mirror.
- **Unchanged:** the public facade (every name, signature and result field),
  `EngineErrorCode`, the ProjectSpec protocol (`1`), the component-manifest
  protocols (`1`, `2`, `3`), the option-schema protocols, `metadata_version`
  (`1`), the sixteen Foundation extension points, `foundation_version` (`1`),
  the fifteen existing components and their versions, and `template/`.

The one real defect FT-28.02 found, `job.py`'s `os.replace`, was in the
archetype's own content and was fixed before this release, so `batch` ships at
`1.0.0` with the corrected file.

Every addition is additive: nothing exported from `forge_template` was renamed,
removed or narrowed, and no deprecation was opened.

## Release review: the Copier floor

Reviewing the delta against `v0.6.0` found one gap in the work already merged,
and it is corrected in the prepare commit rather than shipped. ADR 0073
decision 4 requires Copier `>=9.6`: below that, `_copier_operation` is never
injected into the task context, and the guard `{{ _copier_operation == 'copy' }}`
renders as the literal string `False`, so every guarded task, `git init`
included, would silently never run, on `copy` as well as `update`. The change
that landed ADR 0073 raised only the test dependency (`copier>=9.6,<10`), while
`copier.yml`'s own `_min_copier_version`, the floor Copier enforces on a user,
stayed `9.4.0`. Shipped as it was, a user on Copier 9.4 or 9.5 would have been
admitted and then given a project with no git repository and no hooks.

PR #226 sets `_min_copier_version: "9.6.0"`. This completes a decision already
accepted, so it needed no new ADR. No test pinned the old value. The released
`create-forge` clients are unaffected: their `legacy` extra declares
`copier>=9.16,<10`, well above it.

## Published-artefact audit

Downloaded the `0.7.0` wheel and sdist and the `0.6.0` wheel directly from PyPI,
verified each against its own JSON API metadata, and checked:

| Check | Result |
| --- | --- |
| Wheel and sdist size and SHA-256 match the PyPI JSON API; neither yanked; the `0.6.0` wheel likewise | Pass |
| Wheel `METADATA` / sdist `PKG-INFO` report `0.7.0`; `Requires-Python >=3.11`; runtime dependencies `jinja2`, `packaging`, `pydantic` only | Pass |
| Isolated venv installs the downloaded wheel and imports from `site-packages`, not this checkout | Pass |
| Installed package reports the negotiation payload: `package_version=0.7.0`, `projectspec_protocols=(1,)`, `component_manifest_protocols=(1,2,3)`, `metadata_version=1` | Pass |
| Discovery returns sixteen components; `batch` is first, an archetype at `1.0.0`, ProjectSpec protocol `1`, `>=3.11`, with no `requires`, `conflicts` or options | Pass |
| Wheel ships sixteen manifests, `py.typed`, `foundation/foundation.toml`, the six private engine modules and the whole `batch` tree (16 files) | Pass |
| Wheel excludes `adr.py`, `render.py`, `schema.py`, `github_actions.py` | Pass |
| The sdist carries the same `batch` tree name for name (16 and 16) | Pass |
| **Delta against the published `0.6.0` wheel** (payload, `dist-info` excluded) | 22 files added (the 16 under `components/batch/` and the six private engine modules), none removed, 4 changed (`component_manifest.py`, `engine.py`, `file_conflicts.py`, `generation_metadata.py`); no other component and no Foundation file differs |
| **Every accepted batch composition renders from the installed wheel**: all 2,048 subsets of the ten capabilities and the platform were tried | 640 derived from the discovered `requires` and `conflicts` edges, 640 accepted by the engine and 640 rendered; the engine's decision agreed with the derivation for every subset, in both directions |
| `data/output.json` is never a rendered target, for any of the 640 | Pass |
| Invalid selections are rejected, not rendered (`documentation`, which requires `library`; `dependabot` without `github`; `dependabot` with `renovate`) | Pass: `invalid-component-selection` |
| The four accepted selections (none, `jupyter`, `scientific-python`, both) render from the wheel with the job module, `__main__.py`, the tracked sample input, `tests/test_job.py`, `py.typed`, the `run` task, the console script, the output ignore rule and the corrected `Path.replace` | Pass |
| `uv lock` resolves each of the four; no generated lock names `forge-template` or `create-forge` | Pass |
| Maximal selection (`jupyter` and `scientific-python`): `uv sync --all-groups --locked`, `uv run --locked poe check`, then the console script runs the job and writes the expected output | Pass |
| A wheel built from the downloaded sdist has a 162-file payload byte-identical to the published wheel's | Pass |

37 of 37 checks passed. This audit script was disposable tooling, not committed
to this repository, the same precedent FT-12.04, FT-14.03, FT-17.06 and FT-20.04
set. It compares component ids rather than relation objects, the defect that
made the `0.6.0` script derive 512 compositions instead of 640, and it checked
the engine's decision for every one of the 2,048 subsets rather than only the
ones the derivation admits.

## Direct-Copier regression

`template/` is **byte-identical** to `v0.6.0`: `git diff v0.6.0..v0.7.0` over
that path is empty. `copier.yml` is not, for the two reasons above (the
copy-only task guards and the Copier floor), so unlike `0.6.0` this release does
change a Copier-facing file, and the Copier ladder is evidence rather than a
formality.

The protected `main` gate above carried it: its `scaffold` jobs (all four
combinations, including the kitchen sink), the `windows` job and the
`update-compat` job all passed against the tagged commit. `uv run poe update`
was also run locally on the committed tree before the prepare PR merged: three
passed, including `test_update_with_nothing_to_apply_succeeds`, ADR 0073's own
test. No `_migrations` block was required: no template path was renamed or
removed, which is also why the dry run's breaking-change warning stayed silent.
`copier update` therefore keeps working for every project already scaffolded
from a tag.

## Provider hand-off and supported bounds

This release is an immutable, reviewed target. Released `create-forge` `0.5.0`
declares `forge-template>=0.6,<0.7`
([template-engine-api.md](template-engine-api.md#compatibility-and-current-cutover-boundary))
and is **unaffected** by this publication: it continues to resolve, install and
generate against the `0.6.x` line exactly as before. Widening that bound to
`>=0.7,<0.8`, refreshing the lock and adding client tests is a deliberate,
reviewed client change,
[CF-29.01](https://github.com/Sandsy09/create-forge/issues/204)'s to make, not
this release's.

The `0.6.x` line stays installable and supported for the compatibility policy's
[deprecation window](compatibility-policy.md#deprecation-windows), so a client
that hits a `0.7.0` defect can pin back and keep generating while a fix ships as
`0.7.1`. `0.6.0` is **not** yanked, and `0.7.0` itself is never mutated: a
defect is corrected forward, exactly as
[ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md)
decision 5 and the contract's rollback rule state.

The immutable target a client adopts:

| Fact | Value |
| --- | --- |
| Tag | `v0.7.0` (annotated) |
| Commit | `8d12452cfdc9bcae942d885a6ba93587130d8d26` |
| Package bounds a client should declare | `forge-template>=0.7,<0.8` |
| Component identity | `batch`, `archetype`, `1.0.0`, manifest protocol `2`, `>=3.11` |
| Discovered components | sixteen, `batch` first |
| Published wheel | `forge_template-0.7.0-py3-none-any.whl`, 128,920 bytes, sha256 `edaf0604fbfdc746c5ba6c5bd4b42b080919b8fa421b04d6f08345b6d89e37a3` |

This section is the hand-off for
[CF-29.01](https://github.com/Sandsy09/create-forge/issues/204): it records the
tag, commit, package bounds and component identity, and claims neither client
batch support nor an engine-default switch. Nothing in the `create-forge`
repository was changed by this issue.

## What this does not prove

- **A `create-forge` adoption or release.** Widening the engine bound,
  refreshing the lock, and the client's installed batch validation are
  [CF-29.01](https://github.com/Sandsy09/create-forge/issues/204),
  [CF-29.02](https://github.com/Sandsy09/create-forge/issues/205) and
  [CF-29.03](https://github.com/Sandsy09/create-forge/issues/206), out of scope
  for this issue by its own stated exclusions.
- **Client batch support.** No released client selects `batch` yet; batch is
  reachable only through the engine.
- **An engine-default switch.** This release makes none. The cutover shipped
  separately, in `forge-template` `0.5.0` and `create-forge` `0.4.0`; the
  direct-Copier Library path is unchanged and un-deprecated.
- **`1.0.0`.** Not promised by this release or by ADR 0081; it remains a later
  decision.

## Recorded after the release

### The pairing tier

`poe pairing` ([engine-internals.md](engine-internals.md#installed-and-paired-verification))
had been red since FT-28.01: it compared the candidate with the published
`0.6.0`, which cannot render `batch`, and it paired the candidate with released
`create-forge` `0.5.0`, which is outside the `0.7` line. It is retargeted here,
as the release it compared against now exists, and passes (6 passed):

- the candidate wheel, the wheel built from the candidate sdist and the
  published `0.7.0` wheel are observed by a minimal independent client to be
  identical, and equal the checked-in fingerprints, for every archetype,
  `batch` included;
- a positive control: released `create-forge` `0.5.0` resolves a `0.6` engine
  and still generates a project with it; and
- with the candidate installed in its place, `create-forge new` **fails closed**
  before generating anything, for `library` and for `batch` alike: exit `3`, the
  message `Detected forge-template 0.7.0, but this create-forge release supports
  forge-template>=0.6,<0.7`, and no destination directory.

The byte-identical released-client comparison the tier made for `0.6.0` cannot
be made across the two lines, because the client refuses the newer one; it moves
to CF-29.01. One behaviour is recorded rather than asserted away, since it
belongs to the client: `create-forge doctor --json` negotiates the protocols but
not the package range, so it reports the out-of-range `0.7.0` engine healthy
(`ok: true`) while `new` refuses it. Tightening that is client work.

### The crossrepo lag

`poe crossrepo` against the sibling `../create-forge` checkout (unmodified, at
`e0f22c2`) was run once after the release. It was green through FT-25.03; it now
reports one failure and nineteen errors in about fifteen seconds, and all twenty
items trace to one unsatisfiable resolution before any generation:

```text
create-forge==0.5.0 depends on forge-template>=0.6,<0.7, ... we can
conclude that create-forge==0.5.0 cannot be used.
```

This is not a defect. It is the compatibility policy's fail-closed contract
working as designed, exactly as it did when `0.5.0` and `0.6.0` published (see
[streamlit-provider-release.md](streamlit-provider-release.md#recorded-during-the-release-the-crossrepo-lag)).
`poe crossrepo` is deliberately absent from CI
([ADR 0057](adr/0057-validate-the-cross-repository-data-science-line.md)), so no
protected job depends on it. It stays red until
[CF-29.01](https://github.com/Sandsy09/create-forge/issues/204) widens the
client's bound to `>=0.7,<0.8`, and it is that issue's to clear. Nothing in
`../create-forge` was changed here.

The client-observable proof that the `0.7.0` artefacts render and install is the
isolated audit above, which uses no `create-forge` at all.

## Downstream adoption

This release gives `create-forge` an immutable reviewed target to widen its
engine bound against, at
[CF-29.01](https://github.com/Sandsy09/create-forge/issues/204), which was
blocked on it. Released `create-forge` `0.5.0` is unaffected in the meantime: it
keeps resolving, installing and generating against `forge-template>=0.6,<0.7`,
which stays installable through the compatibility policy's support window.
