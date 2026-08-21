# 7. MkDocs pinned below 2.0

## Status

Accepted

## Context

`use_docs` scaffolds a MkDocs + Material + mkdocstrings documentation site.
MkDocs 2.0 removes the plugin system that both Material and mkdocstrings
depend on, so upgrading past it would silently break every generated
project's `docs:build` task the moment an automated dependency update
applied it. Material itself is in maintenance mode; its intended successor,
[Zensical](https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/),
sits at 0.0.x with only preliminary mkdocstrings support.

## Decision

Pin `mkdocs>=1.6,<2` and `mkdocs-material>=9.5,<10` in
`template/pyproject.toml.jinja`, and add matching ignore rules to **both**
automated dependency-update configs so the pin actually holds regardless of
which tool a project picked:

- Renovate: a `matchPackageNames` rule in
  `template/{% if dependency_updates == 'renovate' %}renovate.json{% endif %}.jinja`
  holding `mkdocs` and `mkdocs-material` back, with an explanatory
  `description`.
- Dependabot: matching `ignore` entries with the same rationale as a comment,
  in `template/.github/{% if dependency_updates == 'dependabot' %}dependabot.yml{% endif %}.jinja`.

A version pin in `pyproject.toml` alone is not sufficient — the whole point
of `dependency_updates` is that Renovate or Dependabot will otherwise open a
PR bumping past it. Both configs need the exclusion, or whichever one the
project chose would walk it straight into the break.

## Consequences

- Generated projects cannot get MkDocs 2.0 automatically; upgrading requires
  a deliberate edit to `pyproject.toml` and both dependency-update configs
  once mkdocstrings supports it, or once Zensical does.
- Revisit this ADR (supersede, don't edit) when Zensical reaches 1.0 with
  mkdocstrings parity — at that point the better move may be switching the
  default rather than lifting the MkDocs 2.0 ceiling.
