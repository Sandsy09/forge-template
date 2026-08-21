# 5. git-cliff over hand-written changelogs

## Status

Accepted

## Context

Scaffolded projects enforce Conventional Commits regardless of changelog
choice — a `commit-msg` pre-commit hook (`conventional-pre-commit`) rejects
non-conforming messages either way. That means the commit history is already
structured data by the time anyone would sit down to write a changelog entry
by hand.

## Decision

Offer [git-cliff](https://git-cliff.org/) as the default `changelog_tool`,
generating `CHANGELOG.md` from commit history via a `changelog` Poe task
(`git-cliff --output CHANGELOG.md`). `manual` (Keep a Changelog, hand-written)
remains a choice for projects that want editorial control over wording.

### Alternatives considered

**python-semantic-release** was considered and rejected. It is heavier than
this template needs, and it wants to *own* both the changelog and the
version bump — which conflicts with git-cliff owning the changelog and with
[ADR 0004](0004-build-backend-and-versioning.md)'s `versioning_resolved`
already owning how the version is determined. It is also stricter about
commit-type semantics than intended here: a stray `feat!:` (or a `!` typo)
would trigger an unintended major version bump with no manual gate in
between. Not pursued.

## Consequences

- `git-cliff`'s configuration in `template/pyproject.toml.jinja`
  (`[tool.git-cliff.changelog]` etc.) uses Tera templates, whose `{{ }}`
  delimiter collides with Jinja's own — the same problem GitHub Actions
  `${{ }}` expressions have in generated workflow files. The whole block is
  wrapped in `{% raw %}...{% endraw %}` so Jinja passes it through
  unrendered (see `CLAUDE.md` invariant 4).
- A project that switches `changelog_tool` after scaffolding does so by
  editing `pyproject.toml` directly; there is no migration path back and
  forth, since the two tools' config sections don't coexist meaningfully.
