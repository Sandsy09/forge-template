# 2. Copier over Cookiecutter

## Status

Accepted

## Context

Cookiecutter is the more widely known scaffolding tool, but it only copies
files once. A project generated from a Cookiecutter template has no
supported way to pull in template changes made after it was scaffolded —
users either re-run the template into a new directory and hand-merge, or the
template drifts from every project it already produced.

## Decision

Use [Copier](https://copier.readthedocs.io/) instead. Its defining feature is
`copier update`, which three-way merges template changes into a project
generated months (or years) earlier, using the answers recorded at scaffold
time (`_answers_file: .copier-answers.yml`, rendered by
`template/.copier-answers.yml.jinja`) as the common ancestor.

Every structural decision in this repo is downstream of preserving that
capability.

## Consequences

- **File paths under `template/` become a stable API.** Copier tracks files
  by path, so moving or deleting one is a delete-plus-add for every existing
  project on its next update, not a clean rename. Renames require a
  `_migrations` block in `copier.yml`.
- **Generated output must be pre-commit clean.** `_tasks` commits the
  scaffold immediately; if a hook rewrites a freshly generated file, that
  commit fails and the scaffold breaks before the user sees it.
- **Every user-visible template change needs a tag.** Copier resolves the
  "latest version" from PEP 440 git tags; untagged commits on `main` are
  invisible to `copier update`.
- **A known limitation, accepted rather than fixed:** local edits at the very
  end of a templated file can be lost on update. Both sides append at EOF,
  there is no trailing context for the patch to anchor to, and the incoming
  side wins. Mid-file edits merge correctly. The mitigation is template
  design — keep a stable section (e.g. License) at the end of long templated
  files so user additions land above it, not after it.

In exchange, `forge-template` gets the one thing Cookiecutter cannot offer:
a project scaffolded on day one can still receive template improvements a
year later.
