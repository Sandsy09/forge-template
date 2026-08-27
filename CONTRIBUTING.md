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

No editor-specific setup is required. Project commands and configuration stay
authoritative; the [editor integration strategy](docs/editor-integration.md)
defines the boundary for any future optional editor capability. Generated
runtime settings follow the
[configuration ownership conventions](docs/configuration-ownership.md); the
template repository itself gains no shared runtime configuration layer. When
an owner uses environment-backed input, the
[environment-variable conventions](docs/environment-variables.md) keep its
namespace owner-local and local dotenv loading explicit. Runtime owners that
emit logs follow the
[structured logging capability](docs/structured-logging.md); reusable modules
emit through standard module loggers while the runtime entrypoint owns
process-wide configuration. Runtime owners that read or write files follow
the [path and resource ownership conventions](docs/paths-and-resources.md),
which keep resource access free of process-working-directory assumptions. The
[exception ownership conventions](docs/exception-ownership.md) keep an
owner's own exceptions catchable without a Forge import and require a failure
to be handled, re-raised, or translated exactly once. The
[secret-handling safeguards](docs/secret-handling.md) keep secret-bearing
files out of version control and enforce a placeholder-only `.env.example`
without generating a mandatory scanner. The
[supply-chain provenance contract](docs/supply-chain-provenance.md) defines
the SBOM and release-provenance behaviour a future capability must satisfy,
without generating either until a real release/publish path exists.
The [ProjectSpec protocol](docs/project-spec.md) defines the strict,
engine-owned generation request that future clients construct without taking
ownership of template or composition validation. The
[component manifest protocol](docs/component-manifests.md) defines the strict
TOML metadata, compatibility, owned resources, dependencies, and conflicts
that future engine discovery will consume. The
[composition order contract](docs/composition-order.md) defines the single
deterministic order a validated selection of those components applies in.

## Branching and pull requests

`main` is never committed to directly. Every change gets its own branch and a
pull request — even a single-line fix.

**Branch names** are `<type>/<short-slug>`, kebab-case, where `<type>` is one
of the Conventional Commits types this repo already uses: `feat`, `fix`,
`docs`, `chore`, `refactor`, `test`, `ci`, `build`. Pick the type that the
branch's eventual squash commit will carry — for example:

```
feat/archetype-cli
fix/gitignore-trailing-newline
ci/shellcheck-in-pre-commit
docs/adr-branch-workflow
```

**Flow:**

```bash
git switch -c <type>/<short-slug>       # branch from an up-to-date main
# ... commit(s), following Commit messages below ...
git push -u origin <type>/<short-slug>
gh pr create
```

Wait for `All checks passed` to go green, then **squash merge**. Two reasons
this repo squashes rather than merges or rebases:

- `release.yml`'s notes step is `git log "${latest}..HEAD" --pretty='- %s'
  --no-merges` — one squash commit per PR becomes exactly one release-note
  line. A merge commit or a rebased multi-commit branch produces one line per
  branch commit instead, including any WIP messages.
- **The squash commit's subject is what release notes and `git log` show.**
  Edit it into a well-formed Conventional Commits subject before merging —
  don't leave GitHub's default `Title (#12)`.

Delete the branch after merging (GitHub can do this automatically; see Branch
protection below).

Merging is not releasing — `main` stays untagged, and therefore invisible to
`copier update`, until [Releasing](#releasing) below is actually run.

Which of the validation ladder in [Proposing a template change](#proposing-a-template-change)
to run before pushing depends on what the branch touches; that section is the
one definition of the ladder, not repeated here.

### Branch protection

Recommended settings for `main` (GitHub → Settings → Branches), documented
here so they can be audited or reapplied rather than applied automatically by
this change:

- Require a pull request before merging.
- Require the `All checks passed` status check
  ([test-template.yml](.github/workflows/test-template.yml)'s aggregate job)
  to pass before merging. It's the only check worth requiring directly — it's
  `if: always()` and already fails if any job it depends on failed or was
  cancelled.
- Allow squash merging only, with "Default to pull request title" off (the
  merger edits the subject by hand — see above).
- Automatically delete head branches after merge.

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

Changes that also modify `create-forge` follow its canonical
[cross-repository contributor workflow](https://github.com/Sandsy09/create-forge/blob/main/docs/cross-repository-workflow.md)
for sibling-checkout validation, trust boundaries, and merge/release order.

## Updating GitHub Actions

Remote actions and reusable workflows follow the canonical
[GitHub Action pinning policy](docs/github-action-pinning.md): use a full
40-character commit SHA with the exact release tag in a same-line comment.
Root Dependabot proposes updates weekly, but every update requires human review
of the upstream release and source, independent tag-to-SHA verification, and a
green protected status before merge. Never replace a pin with a branch, tag,
or shortened SHA.

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

## Labels

[.github/labels.toml](.github/labels.toml) is the source of truth for this
repo's issue and PR labels, kept identical to `create-forge`'s copy of the
same file so the two never drift into different vocabularies. Six namespaced
groups each use one colour family: `area:`, `type:`, `priority:`, `size:`,
`status:`, and `roadmap:`. Most `type:` labels mirror the Conventional Commits
prefixes above; `type:epic` and `type:decision` classify roadmap planning
rather than a single eventual commit. `good first issue`, `help wanted`,
`cross-repo`, and `breaking-change` stay unprefixed because their
repository-wide meaning is clearer without another namespace.

Apply the manifest to a repo with:

```bash
uv run poe labels:sync -- --dry-run              # preview, changes nothing
uv run poe labels:sync -- --prune                # apply, deleting extras
uv run python scripts/labels.py --repo Sandsy09/create-forge --prune
```

`gh label create --force` makes this idempotent — re-run it any time the
manifest changes.

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
