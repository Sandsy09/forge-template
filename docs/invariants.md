# Invariants

Six hard rules govern changes under `template/` and `copier.yml`. Breaking
one silently degrades or destroys `copier update` for projects already
scaffolded from this template — the capability
[ADR 0002](adr/0002-copier-over-cookiecutter.md) exists to preserve.

They are numbered, and the numbers are stable: existing records and code
comments cite them as "invariant 3". A new rule appends as 7; none is ever
renumbered.

## 1. Generated output must be pre-commit clean

`_tasks` commits the scaffold. If any hook modifies a freshly generated file,
that commit fails and the whole scaffold breaks.

The usual culprit is `{%- endif %}` stripping the trailing newline, which
trips `end-of-file-fixer`. **This has already broken `.gitignore` and
`renovate.json` once.** End conditional files with `{% endif %}` followed by a
real newline.

Guarded by the root `.pre-commit-config.yaml`'s whitespace/EOF hooks, which
deliberately cover `template/` directly rather than relying on the generated
project's own CI (which never runs pre-commit against files it didn't just
edit). `test-combos.sh` never actually caught this class of bug; five
template files still shipped without trailing newlines in `v0.1.0` until the
root pre-commit config was added and run against `template/` for the first
time. Keep the pre-commit hooks scoped that way.

The `markdownlint-cli2` hook is the deliberate exception: it excludes
`template/` (and `.github/`) rather than covering it. Every Markdown file
under `template/` is `.md.jinja` and holds raw Jinja, not valid Markdown;
linting or `--fix`-rewriting one would itself violate this invariant.

## 2. `.copier-answers.yml` must be generated and committed

Copier does not create it — `template/.copier-answers.yml.jinja` must exist and
render `{{ _copier_answers|to_nice_yaml }}`. Without it, every scaffolded
project is permanently cut off from `copier update`, silently.

## 3. Moving or deleting files under `template/` breaks updates

Copier tracks by path. A rename is a delete plus an add for existing projects.
Declare a `_migrations` block in `copier.yml` when this is unavoidable:

```yaml
_migrations:
  - version: v0.3.0
    before:
      - ["git", "mv", "old/path.py", "new/path.py"]
```

`release.yml` warns at release time when template files moved without one.
**This will matter if a future cutover moves existing Copier paths.** The
selected `cli` reference archetype is package-bound and must not move them.

## 4. Jinja and GitHub Actions both use `${{ }}`

Wrap GHA expressions in generated workflows with `{% raw %}...{% endraw %}`, or
Jinja consumes them. Same applies to git-cliff's Tera templates in
`pyproject.toml.jinja`.

Conversely, a literal `${{` inside a `run:` block in **this repo's own**
workflows is interpreted by Actions even in quotes. Write such patterns as
`'\$\{\{'` so the literal sequence never appears.

## 5. `.gitattributes` is mandatory, in the template AND at repo root

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

## 6. Every template change that should reach users needs a tag

Untagged commits on `main` are invisible to `copier update`. Use `release.yml`.
