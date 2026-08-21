# CLAUDE.md — forge-template

Guidance for Claude Code working in this repository.

## What this is

A [Copier](https://copier.readthedocs.io/) template that scaffolds modern Python
projects. Currently one archetype: **library**.

Copier was chosen over Cookiecutter specifically for `copier update`, which
three-way merges template changes into projects generated months earlier. Every
decision here is downstream of preserving that capability.

## Repository relationship

| Repo | Role |
| --- | --- |
| `https://github.com/Sandsy09/forge-template` | This repo. The templates. |
| `https://github.com/Sandsy09/create-forge` | The CLI that scaffolds from it. |

Separate because Copier resolves template versions from PEP440 git tags here.
**Do not merge them.**

## Layout

```
forge-template/
├── copier.yml              Question schema. MUST be at root.
├── scripts/
│   ├── test-combos.sh      Scaffold every combo, assert, run their checks
│   ├── verify-ci.sh        Push combos to throwaway repos, watch CI
│   └── test-update.sh      Validate copier update three-way merge
├── .github/workflows/
│   ├── test-template.yml   This repo's CI
│   └── release.yml         Manual tag + release
└── template/               EVERYTHING here becomes the scaffold
```

Nothing inside `template/` describes the template itself. `copier.yml`,
scripts, and this repo's own CI stay at root and are excluded via
`_subdirectory: template`.

## The question schema

`copier.yml` is the contract. Once projects exist in the wild, changing it is
expensive.

Key mechanics:

- **`build_backend` and `versioning` are a linked pair.** `versioning` is only
  asked when Hatchling is chosen; `versioning_resolved` is a hidden computed
  value that collapses to `static` for `uv_build`. **All templates read
  `versioning_resolved`, never `versioning`.** This makes the invalid
  combination unrepresentable rather than merely unselected, which matters
  because `copier update` replays stored answers.
- **`python_matrix` is computed**, sliced from `python_all` between
  `python_min_version` and `python_version`. Adding a new Python version is a
  one-line edit to `python_all`.
- **Computed values use `when: false`** with the value in `default`.
- **`github_org` has an empty default** deliberately. The CLI supplies it.

## Invariants — do not break these

### 1. Generated output must be pre-commit clean

`_tasks` commits the scaffold. If any hook modifies a freshly generated file,
that commit fails and the whole scaffold breaks.

The usual culprit is `{%- endif %}` stripping the trailing newline, which
trips `end-of-file-fixer`. **This has already broken `.gitignore` and
`renovate.json` once.** End conditional files with `{% endif %}` followed by a
real newline.

Guarded by an assertion in `test-combos.sh`. Keep it.

### 2. `.copier-answers.yml` must be generated and committed

Copier does not create it — `template/.copier-answers.yml.jinja` must exist and
render `{{ _copier_answers|to_nice_yaml }}`. Without it, every scaffolded
project is permanently cut off from `copier update`, silently.

### 3. Moving or deleting files under `template/` breaks updates

Copier tracks by path. A rename is a delete plus an add for existing projects.
Declare a `_migrations` block in `copier.yml` when this is unavoidable:

```yaml
_migrations:
  - version: v0.3.0
    before:
      - ["git", "mv", "old/path.py", "new/path.py"]
```

`release.yml` warns at release time when template files moved without one.
**This will matter when archetype two is added** and shared files get extracted.

### 4. Jinja and GitHub Actions both use `${{ }}`

Wrap GHA expressions in generated workflows with `{% raw %}...{% endraw %}`, or
Jinja consumes them. Same applies to git-cliff's Tera templates in
`pyproject.toml.jinja`.

Conversely, a literal `${{` inside a `run:` block in **this repo's own**
workflows is interpreted by Actions even in quotes. Write such patterns as
`'\$\{\{'` so the literal sequence never appears.

### 5. `.gitattributes` is mandatory, in the template AND at repo root

`* text=auto eol=lf`. In `template/`, without it, Windows checkouts get CRLF,
Copier's regenerated baseline never matches the working tree, and
`copier update` degrades to full-file overwrite — silently destroying local
edits. The author develops on Windows; this has already bitten once.

The **root** `.gitattributes` (added alongside `template/`'s) matters for a
different reason: `template/*.jinja` files are read as raw bytes when Copier
scaffolds — Copier does not run them through git's smudge filters — so the
line endings a project gets are whatever this repo's own checkout produced.
Without a root `.gitattributes`, a fresh clone on a machine with
`core.autocrlf=true` (the author's own Windows setup) checked out `copier.yml`,
every `scripts/*.sh`, `.gitignore`, and both workflow files as CRLF — verified
by cloning HEAD before the fix landed. Shell scripts with CRLF shebangs can
break on Linux runners. `template/`'s own `.gitattributes` already protected
everything under `template/`; the root one covers everything else.

### 6. Every template change that should reach users needs a tag

Untagged commits on `main` are invisible to `copier update`. Use `release.yml`.

## Conditional filenames

Optional files use conditional names — when the name renders empty, the file is
skipped:

```
template/{% if use_docs %}mkdocs.yml{% endif %}.jinja
template/{% if dependency_updates == 'renovate' %}renovate.json{% endif %}.jinja
```

Works for directories too. Files needing no rendering (`py.typed`,
`.editorconfig`) carry no `.jinja` suffix — `py.typed` in particular **must
stay byte-empty**.

## Validation

Run in this order. All three currently pass.

```bash
./scripts/test-combos.sh     # local: 4 combos, render assertions, poe check
./scripts/verify-ci.sh <org> # pushes to throwaway repos, watches CI
./scripts/test-update.sh     # three-way merge: local edits survive
```

`test-combos.sh` scaffolds from a **non-git snapshot** so uncommitted edits are
picked up. `test-update.sh` clones properly, because updates need real tags.
`_commit` is legitimately absent from answers files produced by the snapshot
path — that is not a bug.

Combo 4 (kitchen sink) flips every remaining conditional at once. It has caught
real bugs the other three missed — including all 11 byte-empty template files
below, once an eighth assertion (no zero-byte file in rendered output, outside
a `py.typed`/`tests/__init__.py` allowlist) was added. Keep both.

## Current state

Working: library archetype, all four combos green locally and in CI, update
merge validated, root and template `.gitattributes` both in place, no
byte-empty template files remain, `task_runner`/`make` removed (it was the
one untested, 100%-broken conditional — see Deferred). **`v0.1.0` is tagged
(annotated, via `release.yml`) and pushed to `origin`** — the CLI can
scaffold from this repo.

Not yet done:
- No root `pyproject.toml` for the template repo's own tooling (uv, ruff, poe)
- No pre-commit config at root
- Root `LICENSE`, `README.md`, `CONTRIBUTING.md` exist but are 0-byte
  placeholders; `SECURITY.md` doesn't exist at root at all
- No `docs/`

## Backlog, in order

**1. Root repo hygiene** ([#2](https://github.com/Sandsy09/forge-template/issues/2)).
`pyproject.toml` for the template repo's own tooling, pre-commit config,
content for the placeholder `LICENSE` (MIT, matching the CLI), `README.md`,
`CONTRIBUTING.md` (how to change a template safely — the invariants above,
and it should point at this file rather than restate it), and a new
`SECURITY.md`.

**2. `docs/`** ([#3](https://github.com/Sandsy09/forge-template/issues/3)).
ADRs for decisions already made: Copier over Cookiecutter, two-repo split,
uv_build vs Hatchling as a user choice, git-cliff over hand-written
changelogs, mypy as default with pyright optional, MkDocs pinned below 2.0.

**3. Archetype two** ([#4](https://github.com/Sandsy09/forge-template/issues/4)).
Extract shared files into a common location, add the new archetype's own
directory. **This is the `_migrations` moment** — plan it before writing any
code, and keep the library archetype's paths stable if possible. Candidates
in rough order of usefulness: `cli`, `service` (FastAPI + Docker), `pipeline`.

## Known limitation, documented not fixed

Local edits at the **very end** of a templated file can be lost on update: both
sides append at EOF, there is no trailing context for the patch to anchor to,
and the incoming side wins. Mid-file edits merge correctly.

Mitigation is template design — keep a stable section (License, etc.) at the
end of long templated files so user additions land above it. Noted in the
generated `CONTRIBUTING.md`.

## Deferred, with reasons

- **python-semantic-release** — heavy, fights git-cliff over changelog
  ownership, and a stray `feat!:` can trigger an unintended major.
- **Zensical instead of MkDocs** — MkDocs 2.0 removes the plugin system and
  breaks mkdocstrings; Material is in maintenance mode. Zensical is the
  successor but sits at 0.0.x with preliminary mkdocstrings support. Both
  Renovate and Dependabot configs pin below the breaking versions. Revisit when
  Zensical reaches 1.0 with mkdocstrings parity.
- **`make` as a `task_runner` choice** — removed entirely (see Current state).
  It was the widest-blast-radius conditional, `make` is absent on Windows by
  default (the author's own dev platform, so it could never be dogfooded), and
  nothing in the validation suite ever actually invoked `make` — combo 4 set
  `task_runner=make` and then ran `uv run poe typecheck` directly. The result
  shipped as a byte-empty `Makefile` with an unrunnable `make check` in
  `_message_after_copy`. Reintroduce only as a fully CI-tested option (a real
  Makefile mirroring every Poe task, plus a workflow job that runs `make check`
  on Linux) — tracked as [#1](https://github.com/Sandsy09/forge-template/issues/1),
  not scheduled yet.