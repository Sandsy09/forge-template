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

Runs ruff, mypy, and this repo's own test suite (`tests/`, which checks
`copier.yml` itself — see [src/forge_template](src/forge_template)). This is
separate from validating the *scaffold* — see below.

## Proposing a template change

Anything under `template/` or `copier.yml` needs to actually render and pass
its own checks before it's worth reviewing. In order of cost:

1. **`./scripts/test-combos.sh`** — scaffolds all four answer combinations
   (every `build_backend`/`versioning` pair, plus a "kitchen sink" combo that
   flips every remaining conditional at once) and runs each generated
   project's own `uv run poe check`. Entirely local, no network beyond
   package downloads. Run this after any template edit.
2. **`./scripts/test-update.sh`** — scaffolds from the last released tag,
   makes local edits a real user would make, changes the template, and runs
   `copier update` to confirm local edits survive the three-way merge. Run
   this if your change touches a file that already exists in released
   projects.
3. **`./scripts/verify-ci.sh <org>`** — pushes each combo from
   `test-combos.sh`'s output to a throwaway private repo and watches the
   generated project's own CI run for real. Costs GitHub Actions minutes.
   Worth one run before anything that touches the CI matrices in
   `template/.github/workflows/`.

**Local-green does not mean CI-green for this repo's own CI, either.** This
repo's `.github/workflows/test-template.yml` has, in the past, been broken on
`main` in ways that `test-combos.sh` couldn't catch — it runs entirely
locally, on a machine that already has a git identity configured, and doesn't
reproduce the CI runner's environment. After pushing, check the actual run
(`gh run watch`, or the Actions tab) rather than assuming a green local
script means the pipeline passed.

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
