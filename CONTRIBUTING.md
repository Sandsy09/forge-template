# Contributing

This describes the human workflow — how to set up, validate, and release a
change. For the rules that keep changes from breaking `copier update` for
projects already scaffolded from this template, see
[CLAUDE.md](CLAUDE.md); this file won't restate them.

## Setup

```bash
uv sync --all-groups
uv run pre-commit install --install-hooks
```

## Before opening a pull request

```bash
uv run poe check
```

Runs ruff, mypy, and this repo's own fast test suite (`tests/`, deselecting
the slow `combos`/`update` markers — checks `copier.yml` itself, `docs/adr/`,
and the render-check functions; see
[src/forge_template](src/forge_template)). This is separate from validating
the *scaffold* — see below.

## Proposing a template change

Anything under `template/` or `copier.yml` needs to actually render and pass
its own checks before it's worth reviewing. In order of cost:

1. **`uv run poe combos`** — scaffolds all four answer combinations (every
   `build_backend`/`versioning` pair, plus a "kitchen sink" combo that flips
   every remaining conditional at once) in parallel and runs each generated
   project's own `uv run poe check`. Entirely local, no network beyond
   package downloads. Run this after any template edit. Add `--from-git` (a
   pytest option) to scaffold from committed history instead of the default
   uncommitted snapshot.
2. **`uv run poe update`** — scaffolds from the last released tag, makes
   local edits a real user would make, changes the template, and runs
   `copier update` to confirm local edits survive the three-way merge, plus a
   second scenario updating straight from the last tag to `HEAD`. Run this if
   your change touches a file that already exists in released projects.
3. **`./scripts/verify-ci.sh <org>`** — pushes each combo from `poe combos`'s
   output to a throwaway private repo and watches the generated project's own
   CI run for real. Costs GitHub Actions minutes. Worth one run before
   anything that touches the CI matrices in `template/.github/workflows/`.

**Local-green does not mean CI-green for this repo's own CI, either.** This
repo's `.github/workflows/test-template.yml` has, in the past, been broken on
`main` in ways the local suite couldn't catch — it reproduces the CI runner's
environment closely (down to supplying a git identity when one isn't already
configured, via `tests/conftest.py`), but a green local run is still not proof
the actual GitHub Actions run passed. After pushing, check the actual run
(`gh run watch`, or the Actions tab) rather than assuming a green local suite
means the pipeline passed.

## Recording a decision

If a change makes a real architectural call — not just a bugfix — write an
[ADR](docs/adr/) for it: copy the most recent record, increment the number,
and follow the same Status/Context/Decision/Consequences shape. Records are
immutable; a decision that changes later gets a new ADR that supersedes the
old one, not an edit to it. `uv run poe check` verifies the set stays
consistent (filenames, numbering, that the index links every record).

## Commit messages

Conventional Commits (`feat:`, `fix:`, `chore:`, ...); a `commit-msg` hook
enforces this once `pre-commit install --install-hooks` has run.

## Releasing

Untagged commits on `main` are invisible to `copier update` — a project
scaffolded from `main` right now will never see them. Cutting a release is a
deliberate act: run `.github/workflows/release.yml` via the Actions tab
(`workflow_dispatch`), pick the version bump, and use `dry_run: true` first
if you want to see the computed tag before it's pushed.

If your change renamed or deleted a file under `template/`, the workflow
warns if no `_migrations` block covers it — existing projects would otherwise
get that path deleted plus a new one added on their next `copier update`,
rather than a clean rename. See CLAUDE.md's invariant 3.
