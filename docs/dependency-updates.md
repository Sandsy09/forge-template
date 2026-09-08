# Dependency update automation

This is the canonical living policy for automated Python dependency updates to
the `forge-template` **repository itself** — its root `pyproject.toml` and the
committed `uv.lock`. It is the sibling of the
[GitHub Action pinning policy](github-action-pinning.md), which governs the
`github-actions` half of the same [.github/dependabot.yml](../.github/dependabot.yml).

It does not govern the dependencies rendered into generated projects, and it
does not make Dependabot a Foundation requirement.

## Scope

[.github/dependabot.yml](../.github/dependabot.yml)'s `uv` entry checks the
repository root weekly on Monday and opens `chore`-prefixed pull requests
labelled `type:chore` and `area:packaging`, limited to five open at once. It
covers `[project.dependencies]` and every `[dependency-groups]` list, resolved
through `uv.lock`.

Routine development-tooling minor and patch updates (`ruff`, `mypy`,
`pytest` and its plugins, `pre-commit`, `poethepoet`, `pyyaml`) are collected
into a single `dev-tooling` group — one pull request per week. Runtime
dependencies and every major update arrive as individual, separately
reviewable pull requests.

Automation never merges its own pull requests. Every update is reviewed and
must pass the validation ladder below before merge.

## What this does not cover

- **Generated-project dependencies.** The dependencies declared in
  `template/pyproject.toml.jinja`, the Foundation content tree
  (`src/forge_template/foundation/content/`), and component fragments'
  `dependencies` are *generated-project* concerns. Each scaffolded project
  chooses its own updater through `copier.yml`'s `dependency_updates`
  question and owns that configuration after handoff. Nothing in this
  repository's `.github/dependabot.yml` reaches them.
- **Pinned pre-commit hook revisions.** `.pre-commit-config.yaml`'s `rev:`
  fields are not part of any ecosystem Dependabot's `uv` entry understands.
  They are updated manually. This surface has drifted before — the hook
  `ruff-pre-commit` currently pins `v0.14.0` while the resolved environment
  is well ahead of it — so it needs deliberate periodic review, not a
  background service.

## Gated compatibility lines

Every dependency below carries a deliberate strict upper bound in
`pyproject.toml`. `.github/dependabot.yml`'s `uv` entry has a matching
`version-update:semver-major` ignore rule for each, so a new major line
arrives only as a human pull request that moves every coupled artefact
together — never as an automated bump.

| Dependency | Bound | Why bounded | Crossing it requires |
| --- | --- | --- | --- |
| `jinja2` | `<4` | Engine runtime; the wheel's resolvable range for every engine consumer | bound + `uv.lock` + [compatibility-policy.md](compatibility-policy.md) + `poe combos` + `poe archetype` + `poe check:wheel` |
| `packaging` | `<27` | Engine runtime; version and specifier parsing across the catalogue | bound + `uv.lock` + [compatibility-policy.md](compatibility-policy.md) + `poe check:wheel` |
| `pydantic` | `<3` | Engine runtime; every ProjectSpec and manifest model | bound + `uv.lock` + [compatibility-policy.md](compatibility-policy.md) + `poe check:wheel` |
| `copier` | `<10` | The direct-Copier path this repo still supports ([invariant 4](invariants.md)) | bound + `uv.lock` + `poe combos` + `poe update` |
| `ipykernel` | `<8` | Live-kernel notebook validation the generated `jupyter` capability is written against | bound + `uv.lock` + `poe archetype` |
| `nbclient` | `<1` | Notebook execution in the same validator | bound + `uv.lock` + `poe archetype` |
| `nbformat` | `<6` | Notebook structural checks in the same validator | bound + `uv.lock` + `poe archetype` |

`tests/test_dependency_updates.py` derives this list from `pyproject.toml` at
run time: a bound added later without an ignore rule fails the fast suite, and
an ignore rule with no matching bound fails it too.

The unbounded development tools have no reviewed line to protect — routine
updates through them are the entire point of the automation.

## Reviewing a proposed update

Every Dependabot pull request, grouped or individual:

1. `uv run poe check` — always. Ruff, mypy, and the fast suite.
2. `uv run poe check:wheel` if a `[project.dependencies]` entry moved — the
   built wheel must still import against only its declared runtime range.
3. The slow suites the changed dependency maps to:

   | Changed dependency | Also run |
   | --- | --- |
   | `jinja2` | `poe combos`, `poe archetype`, `poe check:wheel` |
   | `packaging`, `pydantic` | `poe check:wheel` |
   | `copier` | `poe combos`, `poe update` |
   | `ipykernel`, `nbclient`, `nbformat` | `poe archetype` |
   | development tooling only | `poe check` alone |

4. A green local suite is not proof CI passed — confirm the actual GitHub
   Actions run, per [CONTRIBUTING.md](../CONTRIBUTING.md).

A major-version pull request for a gated dependency should not exist; if one
appears, the ignore rule is missing or misspelled and the fix is the config,
not a merge.

## Relationship to Action pinning

The `github-actions` entry in the same file stays governed by
[github-action-pinning.md](github-action-pinning.md): full-SHA pins, exact
release comments, human tag-to-SHA verification, and no auto-merge. This
policy changes nothing about it, and
`tests/test_dependency_updates.py` asserts that entry is left intact.
