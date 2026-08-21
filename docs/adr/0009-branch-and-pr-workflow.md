# 9. Branch and pull request workflow

## Status

Accepted

## Context

Every commit in this repo's history had gone straight to `main` — no PR was
ever opened against it, despite `.github/workflows/test-template.yml` already
triggering on `pull_request` and its final job existing specifically to be a
required status check for branch protection. There was also no PR template and
no issue templates for this repo, despite `template/.github/` shipping both to
every scaffolded project.

Working this way costs review: several recent commits
(`fix: trailing newlines in generated files`, three times in a row) are what
unreviewed direct pushes to `main` look like — the same problem re-fixed
because nothing forced a second pair of eyes before it landed.

`release.yml` builds its release notes from
`git log "${latest}..HEAD" --pretty='- %s' --no-merges`, which is sensitive to
how history on `main` is shaped: a merge strategy that leaves multiple commits
per unit of work produces multiple, possibly messy, release-note lines for
what a user experiences as one change.

## Decision

Adopt a branch-per-change, PR-into-`main`, squash-merge workflow, documented
in [CONTRIBUTING.md](../../CONTRIBUTING.md):

- Branch names are `<type>/<short-slug>`, where `<type>` is one of this repo's
  existing Conventional Commits types, matching the type of the eventual
  squash commit.
- Every change is squash merged. This makes each `release.yml` note line
  correspond to exactly one PR, and makes the squash commit subject —  edited
  by hand at merge time, not left as GitHub's default title — the single
  authoritative one-line description of the change.
- Branch protection settings (PR required, `All checks passed` required,
  squash-only, auto-delete branches) are documented in CONTRIBUTING.md but not
  applied by this decision; applying them on GitHub is a separate, deliberate
  step.
- The same shape is mirrored into `template/CONTRIBUTING.md.jinja` for
  scaffolded projects, without this repo's own `release.yml` specifics, which
  vary by `changelog_tool`.

## Consequences

- `.github/pull_request_template.md` and `.github/ISSUE_TEMPLATE/` now exist
  at the repo root, retargeted at this repo (template tag and Copier version
  instead of a package version; an issue-template contact link pointing
  CLI-only reports at `create-forge`, per [ADR-0003](0003-two-repo-split.md)).
- Existing projects scaffolded from `v0.1.0`/`v0.1.1` receive this addition to
  `CONTRIBUTING.md.jinja` as a three-way merge on their next `copier update`.
- Applying the recommended branch protection settings, and any cleanup of
  history that predates this decision, is left to the maintainer.
