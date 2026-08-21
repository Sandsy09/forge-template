# 4. Build backend + versioning

## Status

Accepted

## Context

Scaffolded projects need a build backend, and the two realistic choices —
`uv_build` and Hatchling — have different capabilities. `uv_build` is
simpler but only supports a static version literal in `pyproject.toml`.
Hatchling supports `hatch-vcs`, deriving the version from git tags, but that
mechanism breaks installs from a plain archive tarball (no `.git` directory
to inspect) and is unnecessary weight for a project that doesn't want it.

These two questions — which backend, and how versioning works — are not
independent: `uv_build` can only ever mean static versioning. If they were
modeled as two separate, independently answerable questions, a project could
end up in `build_backend: uv_build` + `versioning: vcs`, a combination that
doesn't build.

The risk is sharper than an ordinary invalid-input bug, because of [ADR
0002](0002-copier-over-cookiecutter.md): `copier update` replays stored
answers from `.copier-answers.yml`. An invalid combination has to be made
*unrepresentable*, not merely unselected in the UI, or a future template
change could silently reintroduce it for every project that already
recorded it.

## Decision

Model `build_backend` and `versioning` as a linked pair in `copier.yml`:

- `build_backend` — `uv_build` (default, simple, static version only) or
  `hatchling` (needed for git-tag versioning).
- `versioning` — only asked `when: build_backend == 'hatchling'`. Choices:
  `static` or `vcs` (git tags via `hatch-vcs`, with the tarball-install
  caveat stated in its help text).
- `versioning_resolved` — a hidden, `when: false` computed value:
  `static` if `build_backend == 'uv_build'`, otherwise whatever `versioning`
  says. **Every file under `template/` reads `versioning_resolved`, never
  bare `versioning`.** This is enforced by
  `check_versioning_indirection` in
  [src/forge_template/schema.py](../../src/forge_template/schema.py), which
  fails the build if any template file references bare `versioning`.

## Consequences

- The invalid pairing (`uv_build` + `vcs`) cannot exist in a stored answers
  file, because `versioning` is never even asked when `build_backend` is
  `uv_build` — and `versioning_resolved` collapses it regardless.
- Any new template file that reads `versioning` instead of
  `versioning_resolved` is a CI failure, not a runtime surprise discovered
  by a user.
- The pattern — a `when: false` computed question with the derived value in
  `default`, consumed instead of the raw inputs — is the general mechanism
  `copier.yml` uses for every other computed value (e.g. `python_matrix`,
  `repo_url`), established here first.
