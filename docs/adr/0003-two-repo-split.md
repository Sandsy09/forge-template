# 3. Two-repo split

## Status

Accepted

## Context

`forge-template` (the templates) and `create-forge` (the CLI that scaffolds
from it) could plausibly live in one repo — the CLI is a thin wrapper around
`copier copy gh:Sandsy09/forge-template`. But [ADR
0002](0002-copier-over-cookiecutter.md) established that Copier resolves a
template's "latest version" from PEP 440 git tags on the template's own repo.

## Decision

Keep them as two separate repositories:

| Repo | Role |
| --- | --- |
| [`forge-template`](https://github.com/Sandsy09/forge-template) | The templates themselves. |
| [`create-forge`](https://github.com/Sandsy09/create-forge) | The CLI that scaffolds from it. |

If they were one repo, every tag would have to mean something for both the
CLI's release cadence and the template's — a CLI bugfix release would either
need its own unrelated template tag, or template changes would have to wait
for a CLI release to ship. Splitting removes that coupling: `forge-template`
tags exist purely to mark points `copier update` can resolve to, and
`create-forge` releases independently as its own package.

## Consequences

- A change spanning both (e.g. `create-forge` needing a new template
  question) requires two PRs, potentially reviewed and merged out of order.
- `create-forge` supplies context the template itself deliberately leaves
  blank — e.g. `copier.yml`'s `github_org` question has an empty `default`
  because the CLI's own org profile fills it in; a bare `copier copy` user is
  simply prompted.
- Each repo has its own CI, its own `pyproject.toml`, and its own release
  workflow, with no shared tooling repo to keep in sync.
