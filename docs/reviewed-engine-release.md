# Reviewed forge-template 0.4.1 release

This is FT-14.03's evidence record: the reviewed Stage 14 engine line is
tagged, released, and published, and its artefacts are audited against
PyPI. It is the canonical answer to
[FT-14.03 / #115](https://github.com/Sandsy09/forge-template/issues/115), the
final child of
[FT-EPIC-14 / #99](https://github.com/Sandsy09/forge-template/issues/99), and
was accepted as a decision by
[ADR 0048](adr/0048-data-science-compatibility-and-acceptance.md) before any
of Stage 14's children existed. This issue executes that decision; it adds no
new one.

FT-14.01's [composition review](composition-architecture-review.md) found no
production boundary defect. FT-14.02's
[cross-repository validation](cross-repository-validation.md) then proved
current forge-template and create-forge `main` pair and pass together through
a local, non-PyPI install. FT-14.03 republishes that same decision-complete
candidate as an immutable, PyPI-published target: **`0.4.1` changes nothing in
the catalogue** — see "What 0.4.1 changes" below.

## The release chain

| Step | Evidence |
| --- | --- |
| Prepare | [PR #132](https://github.com/Sandsy09/forge-template/pull/132) `chore: prepare forge-template 0.4.1`, squash commit `9f7ed8187d931c10016d76bb271de72ddb89a4c0` |
| Protected `main` gate | [run 33905406877](https://github.com/Sandsy09/forge-template/actions/runs/33905406877) — success |
| Release dry run | [run 33905776966](https://github.com/Sandsy09/forge-template/actions/runs/33905776966) — derived `v0.4.1`, displayed the release notes below, created no tag, release, or PyPI file |
| Release run | [run 33906621638](https://github.com/Sandsy09/forge-template/actions/runs/33906621638) — `release` and `Publish to PyPI` jobs both succeeded |
| Tag + GitHub Release | [`v0.4.1`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.1) at commit `9f7ed8187d931c10016d76bb271de72ddb89a4c0` |
| PyPI | [`forge-template 0.4.1`](https://pypi.org/project/forge-template/0.4.1/) |

The release notes generated from `git log v0.4.0..HEAD --no-merges`:

```text
- chore: prepare forge-template 0.4.1
- test: validate the cross-repository Data Science line
- test: validate three-archetype composition boundaries
- docs: complete Stage 12 release
```

## Published artefacts

| Artefact | SHA-256 |
| --- | --- |
| `forge_template-0.4.1-py3-none-any.whl` | `053a67b748dad0d1c437892981efd4614401bcf2c7488d3e2b67adc18db3d144` |
| `forge_template-0.4.1.tar.gz` | `ecab4ee966cda24e252ea1287923cfc89c411897e69c3b62e1d5101255f216e6` |

Both hashes were verified against PyPI's own JSON API metadata after
downloading. Wheel `METADATA` and sdist `PKG-INFO` both report `0.4.1`.

## What 0.4.1 changes

Nothing in the catalogue. `src/forge_template` is byte-identical between the
`v0.4.0` tag and the `v0.4.1` release commit — the three commits in between
(FT-14.01, FT-14.02, and this release's own prepare commit) touched only
tests, scripts, and documentation. The published-artefact audit below
confirms this at the wheel level directly, rather than relying on the source
diff alone: the `0.4.1` wheel's `forge_template/foundation/` and
`forge_template/components/` trees are **byte-identical** to the published
`0.4.0` wheel's, file for file. Every protocol integer, component version,
public signature, `EngineErrorCode` value, extension point, and rendered byte
is unchanged. Only the package version, the README long description, and this
documentation moved.

## Published-artefact audit

Downloaded both the `0.4.1` and `0.4.0` wheels and sdists directly from PyPI,
verified each against its recorded SHA-256, and checked:

| Check | Result |
| --- | --- |
| Wheel/sdist SHA-256 match PyPI metadata | Pass |
| Wheel `METADATA` / sdist `PKG-INFO` report `0.4.1` | Pass |
| `0.4.1` wheel's `foundation/` + `components/` trees vs. `0.4.0` wheel's | 0 differences |
| Wheel ships `engine.py`, `project_spec.py`, `foundation.toml`, `foundation/content/`, every component's manifest + owned content + `extensions/`, and `py.typed` | Pass |
| Wheel excludes `adr.py`, `render.py`, `schema.py`, `github_actions.py` | Pass |

An isolated virtual environment installed directly from the downloaded
`0.4.1` wheel (never from this repository's own source) reports:

```json
{
  "package_version": "0.4.1",
  "projectspec_protocols": [1],
  "component_manifest_protocols": [1, 2],
  "component_ids": ["cli", "data-science", "jupyter", "library", "scientific-python"],
  "component_versions": {
    "cli": "1.0.1",
    "data-science": "1.0.0",
    "jupyter": "1.0.0",
    "library": "1.0.1",
    "scientific-python": "1.0.0"
  },
  "data_science_requires": [["jupyter", "<2,>=1"]]
}
```

Both accepted Data Science compositions (`data-science` + `jupyter`, and
`data-science` + `jupyter` + `scientific-python`) were rendered from that
installed `0.4.1` package into temporary projects. Each resolved a lock,
restored with `uv sync --all-groups --locked`, passed
`uv run --locked poe check` (including `notebook:check` against a live
kernel), and built its own wheel and sdist with `uv build`. Their generated
`uv.lock` files name neither `forge-template` nor `create-forge`.

This audit script was disposable tooling, not committed to this repository —
the same precedent FT-12.04's `0.4.0` audit set.

## What this does not prove

- **`create-forge`'s installed-console end-to-end proof.** This audit renders
  through the engine's public facade directly, the same way
  [data-science-validation.md](data-science-validation.md#published-040-release-verification)'s
  `0.4.0` audit did. The real proof against an installed `create-forge`
  console script consuming this published release is CF-14.02.
- **A `create-forge` release.** `create-forge`'s own `0.3.0` release, adopting
  this `0.4.1` line, is CF-14.04 — out of scope for this issue by its own
  stated exclusions.
- **A default-path cutover.** `create-forge new --engine-preview` remains a
  preview; the direct-Copier Library path is unchanged.

## What remains

`create-forge` Stage 14 now has an immutable reviewed engine target. CF-14.01
adopts the `0.4.1` line (already within its declared
`forge-template>=0.4,<0.5` range), CF-14.02 and CF-14.03 complete client-side
end-to-end and regression validation, and CF-14.04 publishes `create-forge
0.3.0` and closes the roadmap.
