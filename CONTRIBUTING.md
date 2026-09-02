# Contributing

This describes the human workflow — how to set up, validate, and release a
change. For the rules that keep changes from breaking `copier update` for
projects already scaffolded from this template, see
[docs/invariants.md](docs/invariants.md); this file won't restate them.

## Setup

```bash
uv sync --all-groups
uv run pre-commit install --install-hooks
```

The pre-commit gate lints root `*.md` and `docs/**` with `markdownlint-cli2`
(ruleset in [.markdownlint-cli2.jsonc](.markdownlint-cli2.jsonc)); `docs/adr/`
is exempt from its line-length rule only, since ADR records are immutable.
`template/`'s Markdown is all `.md.jinja` and stays out of scope entirely —
see [invariant 1](docs/invariants.md#1-generated-output-must-be-pre-commit-clean).

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
[organisation policy protocol](docs/organisation-policy.md) defines the
strict, order-independent defaults and constraints a downstream client applies
before constructing that effective request, without granting policy rendering
authority; the
[organisation-policy reference fixture](docs/organisation-policy-fixtures.md)
proves that protocol executably against a test-only resolver. The
[component manifest protocol](docs/component-manifests.md) defines the strict
TOML metadata, compatibility, owned resources, dependencies, and conflicts
that future engine discovery will consume. The
[composition order contract](docs/composition-order.md) defines the single
deterministic order a validated selection of those components applies in. The
[file conflict and override rules](docs/file-conflicts.md) define the output
target, disposition, and collision-safety rules that composed selection
resolves against. The
[safe override and extension points](docs/extension-points.md) contract
defines the complete sanctioned extension surface, denies any `override`
grant, and publishes the extension-point inventory as a versioned contract —
grown from eight to eleven points by FT-11.01 / ADR 0049, which added
`pyproject-development-dependencies`, `pyproject-task-definitions`, and
`pyproject-aggregate-check` so a selected capability, not only an archetype,
can attach tooling.
The
[template variable contract](docs/template-variables.md) defines the rendered
variable namespace and the component option vocabulary declared through
`options_schema`. The
[stable template-engine API](docs/template-engine-api.md) is the supported
top-level client boundary; low-level composition helpers are implementation
details. The
[generated-project validation contract](docs/generated-project-validation.md)
defines the in-memory checks every successful render passes before a client
may stage it. The [Library archetype contract](docs/library-archetype.md)
defines the package-specific boundary FT-08.02 introduced at `0.3.0` and the
Stage 08 review boundary-corrects at `0.3.2`:
manifest and option-schema protocol `2`, the implicit Foundation content
source, the discriminated `PlannedFile.owner`, and the production `library`
manifest itself. The current Copier tree remains unchanged while
`create-forge --engine-preview` consumes the public catalogue. The
[CLI Application archetype contract](docs/cli-application-archetype.md)
defines the package-specific boundary FT-08.04 implements: the optionless
`cli` executable shape, its one direct runtime dependency, console/module
entry points, and the four neutral Foundation extension points it shares
with Library. The source catalogue's `discover_components()` result is now
`("cli", "jupyter", "library", "scientific-python")`; the latest published
`0.3.2` wheel remains the two-archetype line.
The [composition architecture review](docs/composition-architecture-review.md)
records which duplicated resources remain archetype-owned, which accidental
Foundation assumptions were removed, and why lock resolution belongs to
client finalisation. The
[Forge-Blueprint compatibility policy](docs/compatibility-policy.md) defines
every versioned engine axis, compatible ranges, deprecation windows, and the
facts a conformant unsupported-version report must carry, without changing
the public facade or package version. The
[no-copy inheritance proof](docs/no-copy-inheritance.md) demonstrates that a
downstream client can keep policy and orchestration local while consuming
Foundation and component output only through that supported facade.
The [Data Science roadmap](docs/roadmap-v2/README.md) continues this completed
architecture through Stages 10–14. It plans a package-backed,
notebook-oriented third archetype and reusable capabilities without changing
the default Copier path during roadmap creation.
The canonical [Data Science archetype contract](docs/data-science-archetype.md)
fixed that shape's package, notebook, working-tree, and ownership boundary
before implementation; FT-12.01 / ADR 0053 now implements the manifest, its
owned package and smoke tests, and its packaging/metadata/classifier
contributions.
The [initial Data Science capability contracts](docs/data-science-capabilities.md)
define the optionless `jupyter` development-tooling and `scientific-python`
runtime-dependency owners. FT-11.02 / ADR 0050 ships `jupyter`, and FT-11.03 /
ADR 0051 ships `scientific-python`, in the unreleased source catalogue; the
published `0.3.2` catalogue remains unchanged.
The [notebook, data, and model safeguards](docs/notebook-data-and-model-safeguards.md)
fix the fail-closed notebook-validation order, deterministic failure
identifiers, output-free diagnostics, and the prose-only working-tree
guidance those future owners must satisfy. The
[Data Science compatibility and acceptance contract](docs/data-science-compatibility-and-acceptance.md)
classifies every versioned engine axis for the `0.4.0` line, fixes the
executable acceptance matrix and its per-check owners, and states the
cross-repository release gates, completing the Stage 10 contract set.
Stage 11's first changes ship in the engine: FT-11.01 / ADR 0049 adds the
three capability-tooling Foundation extension points the `jupyter` and
`scientific-python` capabilities need, additively and with `library` and
`cli` output semantically unchanged. FT-11.02 / ADR 0050 uses those points to
add Jupyter development dependencies, tasks, safe notebook validation, root
guidance, and checkpoint hygiene only when the capability is selected.
FT-11.03 / ADR 0051 contributes the bounded scientific runtime stack, its
component-owned import test, and usage guidance only when Scientific Python is
selected. The two capabilities remain independent. FT-11.04 / ADR 0052 then
proves the layer — the
[capability composition validation](docs/capability-composition-validation.md)
covers every archetype-and-capability composition, fails every documented
invalid selection closed before rendering, and extends `poe check:wheel` to
the component manifests and extension trees — closing Stage 11 with no
manifest, content, engine, or version change.
Stage 12 then adds the third archetype: FT-12.01 / ADR 0053 ships
`data-science` `1.0.0`, an independent package-backed archetype that requires
`jupyter>=1,<2` and is rejected before rendering without it. `library`/`cli`
stay `1.0.1`, both capabilities stay `1.0.0`, and the package stays `0.3.2`
and untagged — FT-12.04 releases `0.4.0`.

## Branching and pull requests

`main` is never committed to directly. Every change gets its own branch and a
pull request — even a single-line fix.

**Branch names** are `<type>/<short-slug>`, kebab-case, where `<type>` is one
of the Conventional Commits types this repo already uses: `feat`, `fix`,
`docs`, `chore`, `refactor`, `test`, `ci`, `build`. Pick the type that the
branch's eventual squash commit will carry — for example:

```text
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
the slow `combos`/`update`/`archetype` markers — checks `copier.yml` itself,
`docs/adr/`, and the render-check functions; see
[src/forge_template](src/forge_template)). This is separate from validating
the *scaffold* — see below.

A change that intentionally moves the composition, file-conflict, or
template-variable contracts' composed output should also regenerate the
golden fixtures those contracts are checked against
(`uv run pytest tests/test_composition_contract.py --update-goldens`) and
review the diff — see
[composition-fixtures.md](docs/composition-fixtures.md).

A change to `src/forge_template/foundation/` or
`src/forge_template/components/*/content` should also run
`uv run poe archetype`, which builds real wheels and sdists for both
production archetypes -- Library across all three packaging modes, CLI's one
fixed mode plus its installed console script and `python -m` invocation --
see [library-archetype.md](docs/library-archetype.md) and
[cli-application-archetype.md](docs/cli-application-archetype.md).

A change to a component manifest, its packaged resources, or
`[tool.hatch.build.targets.wheel]` should also run `uv run poe check:wheel`
(see [Releasing](#releasing)), which verifies the built wheel still ships
every manifest, content tree, and extension contribution and still excludes
this repo's own CI tooling.

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
scaffolded from `main` right now will never see them. Before a release, bump
`project.version` in `pyproject.toml` through a reviewed pull request. The
manual `.github/workflows/release.yml` derives `v<project-version>` from that
single source, rejects an existing or non-increasing tag, and has no separate
bump selector. Run it from the Actions tab (`workflow_dispatch`), using
`dry_run: true` first when you want to inspect the derived tag without pushing
it.

If your change renamed or deleted a file under `template/`, the workflow
warns if no `_migrations` block covers it — existing projects would otherwise
get that path deleted plus a new one added on their next `copier update`,
rather than a clean rename. See
[invariant 3](docs/invariants.md#3-moving-or-deleting-files-under-template-breaks-updates).

Since [ADR 0036](docs/adr/0036-publish-the-engine-to-pypi.md), the same
`release.yml` run also publishes the engine package to PyPI — a `publish`
job, gated by the `pypi` GitHub Environment and PyPI Trusted Publishing
(OIDC, no stored token), runs after the tag/release job and is skipped
entirely under `dry_run`. It re-runs `poe check:wheel` as a release-time
safety net before building and publishing, on top of the same check already
required by CI's `wheel` job. Before any release, you can run that check
locally too:

```bash
uv run poe check:wheel
```

This builds a wheel into a fresh temporary directory and fails loudly if it
ships this repository's own CI tooling (`adr.py`, `render.py`, `schema.py`,
`github_actions.py`) or fails to import cleanly against only its declared
runtime dependencies — see ADR 0036 for why those modules are excluded.
