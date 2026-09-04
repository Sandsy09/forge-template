# Cross-repository Data Science validation

This is FT-14.02's evidence record: proof that current `forge-template` and
`create-forge` `main` branches pair and pass together through a local,
non-PyPI install. It is the canonical answer to
[FT-14.02 / #114](https://github.com/Sandsy09/forge-template/issues/114),
accepted by
[ADR 0057](adr/0057-validate-the-cross-repository-data-science-line.md), and
executed by `tests/test_cross_repository_validation.py` under the `crossrepo`
marker (`uv run poe crossrepo`).

FT-14.01's [composition review](composition-architecture-review.md) found no
production boundary defect and handed this issue a decision-complete `0.4.0`
candidate. FT-14.03 alone bumps and publishes the reviewed `0.4.1` line; this
record changes no version, tag, release, protocol, component, manifest,
rendered byte, public signature, or `create-forge` file.

## Validated revisions

| Repository | Branch | Commit |
| --- | --- | --- |
| `forge-template` | `main` | `6912390deeb4137f03643b07eb19effb89c80663` |
| `create-forge` | `main` | `eb85fbe6aea5fe9d503721b80036b64aac7f29f2` |

Both were clean and synchronised with `origin/main` when this validation ran,
matching the entry criteria
[composition-architecture-review.md](composition-architecture-review.md#compatibility-and-ft-1402-handoff)
states.

## How the local pair is built

Both repositories install as local path installs into one isolated virtual
environment — never an index, so no PyPI `forge-template` can enter the pair:

```bash
uv venv --python 3.13 .venv-crossrepo
uv pip install --python .venv-crossrepo <forge-template-root> <create-forge-root>
```

`tests/test_cross_repository_validation.py::test_the_paired_environment_installs_both_local_sources`
reads each package's `direct_url.json` and asserts both are `file://` URLs —
the executable form of acceptance criterion 4 ("no unpublished registry
dependency"). The suite is sibling-gated and skips entirely when no
`create-forge` checkout is found: a new `--create-forge-root` pytest option
(mirroring `create-forge`'s own `--forge-template-root`) defaults to
`../create-forge` next to this repository.

This is not added to `.github/workflows/test-template.yml`. It is deliberately
opt-in — see [ADR 0057](adr/0057-validate-the-cross-repository-data-science-line.md)
for why forge-template CI must not depend on a moving sibling `main`.

`uv run poe crossrepo` (`pytest -m crossrepo`) passed all 20 tests in 393
seconds (6m33s) against the paired local sources above.

## The Stage 14 compatibility matrix

Every row below is a check named by
[data-science-compatibility-and-acceptance.md](data-science-compatibility-and-acceptance.md#the-acceptance-matrix)
that this issue was responsible for making executable against the *paired*
local sources, rather than one repository in isolation.

| Check | Evidence | Outcome |
| --- | --- | --- |
| Installed engine metadata matches the reviewed candidate | `test_installed_engine_metadata_matches_the_reviewed_candidate` | Pass |
| Neither distribution resolves from an index | `test_the_paired_environment_installs_both_local_sources` | Pass |
| All ten valid compositions generate through the real console script | `test_every_valid_composition_generates_through_the_real_console_script` | Pass |
| Repeated generation is byte-deterministic | `test_repeated_generation_is_byte_identical` | Pass |
| Documented rejections leave no partial destination | `test_expected_failures_leave_no_partial_destination` | Pass |
| Both Data Science compositions pass their own generated `poe check` at Python 3.11, 3.13, and 3.14 | `test_data_science_composition_passes_its_own_checks` | Pass |
| `create-forge`'s own cross-repository engine contract passes against the local pair | `test_create_forge_cross_repository_contract_passes_against_the_local_engine` | Pass |
| Package content size matches the ADR 0056 review baseline | `tests/test_composition_architecture_review.py::test_package_content_size_matches_the_recorded_review_baseline` | Pass |
| Built wheel stays under the recorded size ceiling | `uv run poe check:wheel` | Pass |

## Compositions exercised

All ten valid compositions
([composition-architecture-review.md](composition-architecture-review.md#selection-and-ownership))
generate through `create-forge new --engine-preview` and are checked for
project shape, a clean `uv lock --check`, and no Forge distribution in
`pyproject.toml` or `uv.lock`:

- `library` × {none, `jupyter`, `scientific-python`, both}
- `cli` × {none, `jupyter`, `scientific-python`, both}
- `data-science` + `jupyter`
- `data-science` + `jupyter` + `scientific-python`

The two Data Science compositions additionally run their generated project's
own `uv run --locked poe check` — including live-kernel `notebook:check` —
proving Python compatibility through the client rather than only the engine:

| Composition | Python (`--data python_version=`) |
| --- | --- |
| `data-science` + `jupyter` | client default (`3.13`) |
| `data-science` + `jupyter` + `scientific-python` | `3.11`, `3.13`, `3.14` |

`uv run poe archetype` already sweeps the *engine* path at the 3.11/3.14
window edges for every capability combination
([data-science-validation.md](data-science-validation.md)); that evidence is
unchanged and is not repeated here.

## Failure cleanup

Four rejected requests are exercised through the real console script, each
asserting a non-zero exit and that the destination was never created:

| Rejected request | Expected exit | Diagnostic |
| --- | --- | --- |
| `data-science` with `--no-capabilities` | 1 | `requires selected component(s): jupyter` |
| `data-science` with no capability flag at all | 1 | `Add --capability jupyter.` |
| An unknown `--archetype` id | 1 | reports the unknown component |
| An unknown `--component-option` owner | 1 | `unknown option` |

No `.create-forge-*` staging sibling survives any of the four.

## Re-measured package size

Foundation plus every catalogue component's tree (excluding `__pycache__`)
reproduces ADR 0056's review figures exactly:

| Figure | ADR 0056 (2026-09-04) | Re-measured | Rule |
| --- | --- | --- | --- |
| Content files | 60 | 60 | Every file under `foundation/` and each of the five `components/<id>/` trees |
| Content bytes | 39,182 | 39,182 | Sum of those files' sizes |
| Duplicate overhead | 892 | 892 | `(owners − 1) × size` per group, summed over the seven duplicate groups |

Both figures are now pinned by
`tests/test_composition_architecture_review.py::test_package_content_size_matches_the_recorded_review_baseline`,
so a future content change that moves either number will fail loudly rather
than silently drift from the recorded review.

The built wheel itself is not pinned the same way — zip metadata (timestamps,
compression) is not byte-reproducible across machines. `uv run poe
check:wheel` during this validation built a 72,582-byte wheel, close to ADR
0056's own 72,566-byte review measurement and the published `0.4.0` wheel's
72,544 bytes. `scripts/check_wheel.py` now fails above a 131,072-byte (128
KiB) ceiling around these figures, and continues to verify every required
resource ships while repository-only tooling stays excluded.

## What this does not prove

- **Installed-console release validation.** This pairing installs both
  working trees from local source. The real end-to-end proof against a
  *published* `forge-template` release, through an installed `create-forge`
  console script, is `create-forge`'s own CF-14.02 — run against the eventual
  `0.4.1` release, not this local pair.
- **A `create-forge` dependency-range change.** `create-forge` continues to
  declare `forge-template>=0.4,<0.5`; nothing here moves it.
- **A published-artefact audit.** That is FT-14.03's responsibility once
  `0.4.1` is tagged and released, mirroring
  [data-science-validation.md](data-science-validation.md#published-040-release-verification)'s
  audit of `0.4.0`.
