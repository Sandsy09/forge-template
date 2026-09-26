# Contributing

Thanks for contributing to `forge-template`. This is the single source for the
human workflow: set up the repository, make and validate a change, open a pull
request, and release it. Architecture and implementation constraints live in
[CLAUDE.md](CLAUDE.md); canonical behavioural contracts are indexed in
[docs/README.md](docs/README.md).

## Getting set up

Install [uv](https://docs.astral.sh/uv/) and Git, then run:

```bash
uv sync --all-groups
uv run pre-commit install --install-hooks
```

The hook formats and lints Python and validates repository Markdown, YAML,
TOML, shell, and commit messages. Root Markdown and `docs/**` are checked by
markdownlint; immutable ADRs are exempt only from the line-length rule.

## Making a change

Use this flow for fixes, features, and documentation work:

1. Open or select an issue that describes the problem and intended outcome.
2. Read [CLAUDE.md](CLAUDE.md), then locate the relevant living contracts in
   [docs/README.md](docs/README.md). For direct-Copier changes, also read all
   six [template invariants](docs/invariants.md).
3. Decide whether the work changes an architectural boundary, public API,
   protocol, compatibility range, dependency policy, or release/security
   guarantee. If so, add an ADR before or with the implementation.
4. Update every affected living contract in the same pull request as the
   behaviour it describes. Keep user-facing examples aligned with the sibling
   `create-forge` guide when generated behaviour changes.
5. Implement the smallest coherent change, following the surrounding code and
   component ownership boundaries.
6. Run `uv run poe check`, then select the additional checks below according
   to what changed.
7. Open a pull request, wait for `All checks passed`, and squash-merge it.

ADRs use Nygard format: `## Status`, `## Context`, `## Decision`, and
`## Consequences`. Copy the latest record, increment its number, and add it to
`docs/adr/README.md`. ADRs are immutable; supersede an old decision with a new
record rather than rewriting history.

## Running the checks

Start with the fast suite for every change:

```bash
uv run poe check
```

This runs Ruff format checking, Ruff linting, strict mypy, and pytest without
the slow `combos`, `update`, `archetype`, `crossrepo`, and `sweep` markers.

Run additional checks according to the affected surface:

| Change | Additional validation |
| --- | --- |
| `template/**` or `copier.yml` | `uv run poe combos` |
| A path present in released Copier projects | `uv run poe update` |
| Generated GitHub Actions | `./scripts/verify-ci.sh <org>` after `poe combos` |
| Foundation or component generated content | `uv run poe archetype` |
| Catalogue, selection, composition, or public render facade | `uv run poe sweep` |
| Component manifests/resources or wheel configuration | `uv run poe check:wheel` |
| A provider/client boundary visible to `create-forge` | `uv run poe crossrepo` with a sibling checkout |
| `pyproject.toml` dependencies or `uv.lock` | `uv run poe audit` (needs network) |
| Catalogue growth or CI job cost | the growth guard in `poe check`; `uv run poe ci:timings` to re-baseline |

`poe combos` renders four direct-Copier configurations and runs each generated
project's checks. It uses the working tree by default; add `--from-git` when a
real commit-backed source is required.

`poe update` exercises local-edit preservation and last-release-to-HEAD Copier
updates. Run it whenever a released generated path changes. A rename or
deletion under `template/` also needs an appropriate Copier migration.

`poe archetype` builds and installs production engine compositions.
`poe sweep` plans and renders every valid catalogue composition in memory.
`poe crossrepo` pairs both local working trees and skips when no sibling
`../create-forge` checkout exists; see
[the cross-repository validation contract](docs/cross-repository-validation.md).

When a composition contract intentionally changes expected bytes, regenerate
and review its fixtures:

```bash
uv run pytest tests/test_composition_contract.py --update-goldens
```

Update archetype regression digests only when the corresponding output change
is intentional and explained by the pull request.

## Opening a pull request

Never commit directly to `main`. Branch from an up-to-date `main` using
`<type>/<short-slug>`, where the type matches the eventual Conventional Commit:

```text
feat/add-component
fix/update-migration
docs/contributor-guidance
ci/validate-generated-workflow
```

Use Conventional Commit subjects such as `feat:`, `fix:`, `docs:`, `test:`,
`refactor:`, or `chore:`. Complete the pull request template, explain what and
why, list the validation performed, and call out compatibility or generated
output changes.

Wait for the protected `All checks passed` job. Squash-merge so the final
subject produces one useful release-note entry, then delete the branch.
Merging does not release a template change: users receive it only after this
repository is tagged.

## What CI runs

`.github/workflows/test-template.yml` runs the Linux checks from the reusable
`linux-checks.yml`, pinned to `ubuntu-24.04`, plus a Windows smoke render. The
Linux checks validate:

- Pre-commit plus the fast repository suite.
- All four direct-Copier combinations.
- Installed archetype builds and full composition sweeps.
- Copier update compatibility.
- Wheel contents and clean public-package imports.
- A dependency-vulnerability audit of the locked graphs (`audit` job, part of
  `All checks passed`; also weekly and before a release).

`All checks passed` aggregates the pinned Linux call, the Windows job and the
dependency audit, and is the branch-protection target. `runner-canary.yml`
runs the identical Linux checks on the next Ubuntu image; it is non-blocking
and never part of that gate. Workflows name explicit runner images rather
than `ubuntu-latest`; see
[the runner baseline contract](docs/ci-runner-baseline.md) for the canary's
ownership and promotion criteria.

Job cost is budgeted: [the validation budget](docs/validation-budget.md)
records the measured baseline, the approved limits and the tiers. Adding a
capability or platform that pushes a sweep past its limit fails `poe check`
until the tiering is decided.

The two composition sweeps run on a pull request only when it changes a
composition-sensitive path, decided fail-closed by the `classify` job; they
always run on `main`, weekly, on manual dispatch and before a release. Each
sweep proves every valid composition executed, and the `Validation budget`
job's summary shows the timings, the thresholds and the evidence. It fails on
a regression at the approved limits, and it labels a failed job an
infrastructure failure (rerun it) or a test failure (fix the change). Force a
full run with `gh workflow run test-template.yml --ref <branch>`. A release
requires its own commit's run to have both sweeps green.

A local green run does not prove GitHub Actions itself is green; inspect the
actual run after pushing. Cross-repository validation and generated-project
live CI verification remain deliberate local checks because they require a
sibling checkout or temporary repositories.

## Working across both repositories

The shared Forge user guide lives in `create-forge/docs/user-guide/`. When a
change affects generated behaviour or CLI integration, coordinate both working
trees, update affected recipes and examples, and follow the client repository's
canonical cross-repository workflow for merge and release order.

With `../create-forge` present, validate the local pair through
`uv run poe crossrepo`. From the sibling repository, validate its documentation
with:

```bash
uv sync --locked
uv run poe docs:build
```

Keep released behaviour distinct from proposals recorded in roadmap documents.

## Dependencies and workflow security

Repository Python dependencies follow
[the dependency update policy](docs/dependency-updates.md). Strict upper bounds
are compatibility claims, so major-line moves require deliberate review and
their policy-prescribed validation. Generated-project dependencies are owned by
their components or the direct-Copier schema, not by root Dependabot settings.

Locked dependencies are audited for known vulnerabilities with `uv audit` under
[the dependency audit contract](docs/dependency-audit.md): run
`uv run poe audit`, fix a finding with `uv lock --upgrade-package <name>`, and
accept one only through a reviewed, expiring entry in
`.github/audit-exceptions.toml`. A lock-only upgrade is not automatically a
change to a published support floor.

External GitHub Actions follow
[the action-pinning policy](docs/github-action-pinning.md): use a full
40-character commit SHA with the exact release tag in a same-line comment.
Review upstream changes and independently verify the tag-to-SHA mapping before
merging an update. Do not replace pins with branches, tags, or short SHAs.

## Labels

[`.github/labels.toml`](.github/labels.toml) is shared with `create-forge` and
is the source of truth for issue and pull-request labels. Preview or apply it
with:

```bash
uv run poe labels:sync -- --dry-run
uv run poe labels:sync -- --prune
```

Apply the same manifest to the sibling repository when its vocabulary changes.

## Releasing

`pyproject.toml` is the single source of truth for the package version and the
`v<version>` Git tag. Untagged template changes are invisible to existing
direct-Copier projects.

1. Open and merge a reviewed version-bump pull request after all required
   validation passes.
2. Run `uv run poe check:wheel` against the release candidate. The release
   workflow also runs the dependency audit first and stops on findings or an
   unreachable advisory service; there is no bypass, so rerun it.
3. In GitHub Actions, run the manual **Release template** workflow from `main`
   with `dry_run: true` and inspect the derived tag and release notes.
4. Run it again with `dry_run: false`. The workflow creates the tag and GitHub
   release, then publishes the same version to PyPI through Trusted Publishing.
5. Verify the published wheel, source distribution, GitHub release, and PyPI
   version before coordinating a dependent `create-forge` release.

If a released template path was renamed or removed, confirm its Copier
migration is present before releasing. Never repair a bad release by moving an
existing tag; publish an immutable follow-up release instead.
