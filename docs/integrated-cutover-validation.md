# Integrated engine-default cutover validation

This is FT-18.01's evidence record: execution of the two acceptance-matrix
rows it owns from
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md)
(FT-15.04 / [ADR 0061](adr/0061-provider-compatibility-failure-and-release-gates.md)),
pairing the immutable released `forge-template` `0.5.0` against the candidate
`create-forge` `0.4.0` client. Accepted by
[ADR 0067](adr/0067-validate-the-integrated-engine-default-cutover.md). It is
the direct analogue of
[provider-acceptance-validation.md](provider-acceptance-validation.md)
(FT-17.05) and
[cross-repository-validation.md](cross-repository-validation.md) (FT-14.02):
real commands, real output, one row per acceptance-matrix line.

## Why this exists

FT-17.06 released an immutable provider — `forge-template` `0.5.0` on PyPI.
Seven `create-forge` issues (CF-18.01 through CF-18.07) then built a
candidate client with the engine as the default `new` path, but that
candidate is prepared and deliberately unpublished: `create-forge`'s own
CF-18.07 (publish and verify the engine-default client release) names this
issue as a direct blocker. Every prior proof was one-sided — the provider
proved against its own working tree (FT-17.05), the client proved against an
index-resolved version string (CF-18.06) — and `poe crossrepo` itself had
fallen behind the very client changes (`--engine-preview` removed, a
post-rename `git init` lifecycle added) this issue must validate against.
This record closes both gaps: it proves the released artefact and the
candidate client together, and it repairs the standing local-pair suite.

## Validated pair

| Side | Identity | Provenance |
| --- | --- | --- |
| `forge-template` (provider) | `0.5.0` | Published on PyPI; digest-verified against [cutover-provider-release.md](cutover-provider-release.md), installed from the verified file, never an index specifier |
| `create-forge` (candidate client) | `0.4.0`, commit `553af92f312e4e0cf18720ca74d2029af0885cc4` on `main`, untagged | Built from the unmodified sibling working tree (`uv build --wheel`); the no-sibling-edit constraint (ADR 0066 decision 3) is asserted executable — `git status --porcelain` identical before and after the build |

Local validation platform: Windows 11, Python 3.13.1. Row 338 additionally
validated on `ubuntu-latest` in CI (the `released-client` job) — see
[.github/workflows/test-template.yml](../.github/workflows/test-template.yml).

## The released artefacts, verified

`tests/released_provider.py` fetches PyPI's own JSON metadata for
`forge-template==0.5.0`, asserts its reported size and digest equal the
identities [cutover-provider-release.md](cutover-provider-release.md)
recorded — before downloading a byte — then downloads and re-hashes:

| Artefact | Size | SHA-256 | Agreement |
| --- | --- | --- | --- |
| `forge_template-0.5.0-py3-none-any.whl` | 108,247 bytes | `dffaad1eae884856a3828edc2a31f889fcb44f233b6e19c85dc7d2cc9fc6a023` | Pinned record == PyPI JSON metadata == downloaded bytes |
| `forge_template-0.5.0.tar.gz` | 738,075 bytes | `4bcd49a43749d73b2c7bb38122211b1824078470276706d4aa3608d15fd612ba` | (row 339 downloads the wheel only; the sdist identity is recorded from the same pinned source for completeness) |

The installed provider's own `direct_url.json` names the verified download
path with a `file://` scheme — never an index — and the candidate client's
names the built wheel the same way.

## Row 338 — the `0.4.1`-pinned client is unaffected

`tests/test_released_client_compatibility.py`, hermetic (PyPI artefacts
only, no sibling checkout). The last `create-forge` release still on the
`forge-template>=0.4.1,<0.5` line is `0.3.2`, whose engine dependency is
declared behind the `engine` extra — so the resolution proof installs
`create-forge[engine]==0.3.2`, not a bare `create-forge==0.3.2`.

| Test | Result |
| --- | --- |
| `test_the_released_engine_line_is_published_before_asserting_pin_back` | Pass — `0.5.0` is the current PyPI release |
| `test_the_released_client_resolves_the_0_4_1_line_after_0_5_0_publishes` | Pass — resolves `forge-template` inside `>=0.4.1,<0.5`, never `0.5.0` |
| `test_the_released_client_still_generates_against_the_0_4_1_line` | Pass — a real `create-forge new --engine-preview` generation, the pre-cutover project shape (no `.git`, no `.forge`), clean `uv lock --check`, no Forge distribution in the output |
| `test_a_plain_install_of_the_released_client_is_unaffected` | Pass — a bare `create-forge==0.3.2` resolves no engine at all, `--version` and `doctor --json` both work |

**4/4 passed in 63 seconds.** Also run as the `released-client` CI job.

## Row 339 — the integrated matrix

`tests/test_released_provider_cutover.py`, sibling-gated (skips without a
`create-forge` checkout, like `poe crossrepo`), `cutover`-marked. Six
compositions — `library-minimal`, `library-github-max` (every compatible
capability, the one full build-and-check cell), `library-renovate`,
`cli-full`, `data-science-min`, `data-science-rich` — chosen to reach
catalogue edges the historical ten-composition `crossrepo` set does not.

| Test | Matrix row(s) discharged | Result |
| --- | --- | --- |
| `test_the_published_artefacts_match_their_recorded_identities` | Publication row; the "immutable released provider" premise | Pass |
| `test_the_pair_installs_the_verified_wheel_and_the_candidate_client` | Independence AC-04 (no unpublished registry dependency), for the released pair | Pass — both `direct_url.json` entries are `file://` |
| `test_the_installed_release_publishes_the_negotiation_facts` | Engine: negotiation facts | Pass |
| `test_the_installed_release_discovers_the_fourteen_component_catalogue` | Engine: catalogue discovery | Pass |
| `test_the_installed_release_descriptors_carry_no_filesystem_path` | Engine: path-free descriptors | Pass |
| `test_the_installed_release_ships_the_two_generation_metadata_codes` | Engine: the two reserved `EngineErrorCode` values | Pass |
| `test_the_released_wheel_imports_and_renders_in_isolation` | Engine: isolated import/render; strengthened to assert the isolated `__all__` equals the reviewed working tree's | Pass |
| `test_every_boundary_composition_generates_through_the_released_pair` × 6 | Generated projects: shape, `uv lock --check`, no Forge dependency, Data Science notebook | Pass |
| `test_every_generated_target_has_an_explicit_owner` × 6 | Generated projects: every selected component owns ≥1 file | Pass |
| `test_recorded_metadata_reproduces_the_generated_project_byte_for_byte` × 6 | Generated projects: the reproducibility guarantee, proven for the first time against a `.forge/generation.json` a *client* wrote | Pass |
| `test_the_client_classifies_update_targets_against_the_released_engine` | Generated projects: client-boundary update classification (`create-forge update --dry-run`) | Pass |
| `test_the_maximal_composition_builds_installs_and_passes_its_own_check` | Generated projects: full build, install, locked `poe check`, `pre-commit run --all-files`, Forge-freedom probe | Pass |
| `test_repeated_generation_is_byte_identical` × 2 | Regression: determinism | Pass |
| `test_documented_rejections_leave_no_partial_destination` × 7 | Independence: deterministic failure cleanup, including three new edges (`dependabot`/`github`, `dependabot`/`renovate` conflict, `documentation`/`library`) | Pass |
| `test_the_client_reads_no_component_resource_to_negotiate_or_select` | Independence: no-resource-read at the client boundary | Pass |

**37/37 passed in 4 minutes 11 seconds** (after three fixes to this issue's
own test code — see "What this validation itself found" in
[ADR 0067](adr/0067-validate-the-integrated-engine-default-cutover.md)).

## Cited, not re-executed

Per ADR 0067 decision 1, the following are cited to their existing
provider-side proof rather than re-executed through the client:

- The exhaustive 2240-composition sweep — [ADR 0066](adr/0066-validate-provider-parity-reproducibility-and-distributions.md)
  decision 2. The client boundary adds no new selection-validation code path
  for the sweep to re-prove.
- The `cli` and `data-science` full build-and-check cells — FT-17.05's own
  three provider-side cells in
  [provider-acceptance-validation.md](provider-acceptance-validation.md#full-composition-build-cells).
- The unavailable/out-of-range-provider fail-closed path — already proven
  client-side by `create-forge`'s CF-18.06 installed-cutover suite.
- The wheel/sdist content and size audit — FT-17.06's own published-artefact
  audit in
  [cutover-provider-release.md](cutover-provider-release.md#published-artefacts).

## What `poe crossrepo` now shows

`tests/test_cross_repository_validation.py` — the local-pair, both-working-
trees suite — was broken by the very client changes this issue validates
against: `--engine-preview` removed, and CF-18.03's post-rename lifecycle
now creates `.git` and a committed `.forge/generation.json` where the suite
previously asserted neither existed.
[cutover-provider-release.md](cutover-provider-release.md#recorded-during-preparation-the-crossrepo-lag-deepened-as-expected)
recorded the resulting near-total failure (1 passed, 19 failed) as an
expected, owned lag. Repaired here: every `--engine-preview` invocation
removed, the project-shape assertion updated to expect `.git` and
`.forge/generation.json`, and the determinism comparison extended to exclude
`.git/**` alongside `uv.lock`.

**20/20 passed in 9 minutes 15 seconds** — including
`test_create_forge_cross_repository_contract_passes_against_the_local_engine`,
which shells out to `create-forge`'s own canonical
`tests/test_engine_cross_repository.py`: the `EngineInfo(metadata_version=…)`
construction lag FT-17.05 recorded is confirmed fixed by CF-18.01.

## Compositions exercised

| Slug | Archetype | Platform | Capabilities |
| --- | --- | --- | --- |
| `library-minimal` | `library` | — | none |
| `library-github-max` | `library` | `github` | `changelog`, `coverage`, `dependabot`, `documentation`, `dotenv-example`, `jupyter`, `pre-commit`, `pyright`, `scientific-python` |
| `library-renovate` | `library` | — | `changelog`, `dotenv-example`, `renovate` |
| `cli-full` | `cli` | `github` | `changelog`, `coverage`, `dotenv-example`, `jupyter`, `pre-commit`, `pyright`, `scientific-python` |
| `data-science-min` | `data-science` | — | `jupyter` |
| `data-science-rich` | `data-science` | `github` | `jupyter`, `scientific-python`, `coverage`, `pyright`, `pre-commit` |

`renovate` is exercised on its own (`library-renovate`) — never before built
through a client — since it conflicts with `dependabot`, which is exercised
instead in the maximal `library-github-max` cell.

## Failure cleanup

Seven documented rejection cases, each asserting a non-zero exit, no
partial destination, and no `.create-forge-*` staging sibling: a Data
Science project explicitly deselecting capabilities, one omitting the
capability flag entirely, an unknown archetype, an unknown
`--component-option` owner, `dependabot` without `github` (its `requires`
edge), `dependabot` with `renovate` (their mutual `conflicts`), and
`documentation` without `library` (its `requires` edge, exercised through
the `cli` archetype). All seven passed.

## What this validation itself found

Three bugs, all in this issue's own new test code, none in either released
product — see
[ADR 0067](adr/0067-validate-the-integrated-engine-default-cutover.md#what-this-validation-itself-found)
for the full account: a missing `github.organisation` component option on
every `github`-platformed composition; an incorrect assumption that
`create-forge`'s client-owned requirement hint text applies to a
capability's `requires`/`conflicts` edge (it only covers the selected
archetype's own direct requirement); and an incomplete `.venv` exclusion in
the project-shape and determinism assertions (CF-18.03's lifecycle creates
it exactly when `pre-commit` is selected). All three were caught by a real
failing run and fixed before any row was recorded as passing.

## Recorded validation

| Command | Result |
| --- | --- |
| `uv run poe crossrepo` | 20 passed in 555s |
| `uv run pytest -m cutover tests/test_released_client_compatibility.py -v` | 4 passed in 63s |
| `uv run pytest -m cutover tests/test_released_provider_cutover.py -v` | 37 passed in 251s |
| `uv run poe check` | 722 passed, 2 skipped (pre-existing, unrelated symlink-platform skips), 418s |
| `uv run pytest tests/test_cutover_gates.py tests/test_living_docs.py tests/test_adr.py` | All pass — the matrix, doc and ADR tripwires stay satisfied |

## What this does not prove

- **A `create-forge` release.** Publishing `0.4.0` — the tag, GitHub
  Release, and PyPI artefacts — is `create-forge`'s own CF-18.07, which this
  record unblocks but does not perform.
- **A default-path switch in this repository.** No `copier.yml`, `template/**`,
  component, or engine content changed.
- **`1.0.0`.** Not promised by this issue or by ADR 0061; it remains a later
  decision.
- **The exhaustive 2240-composition sweep through the client**, or the `cli`
  / `data-science` full build cells beyond the one `library-github-max` cell
  proven here — see "Cited, not re-executed" above.

## Scope held

No `EngineErrorCode`, component version, `foundation_version`, `copier.yml`,
or `template/**` change. `main` stays `0.5.0` and already tagged — this issue
releases nothing on either side. The candidate `create-forge` working tree
was built from but never modified (`git status --porcelain` asserted
identical before and after every wheel build).
