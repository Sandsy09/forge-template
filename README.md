# forge-template

A [Copier](https://copier.readthedocs.io/) template that scaffolds modern
Python projects. It currently offers one archetype — **library** — and is
built specifically around `copier update`, which lets a project pull in
template changes months after it was first scaffolded via a three-way merge.

## Quick start

The easiest way to use this template is via its companion CLI,
[`create-forge`](https://github.com/Sandsy09/create-forge):

```bash
uvx create-forge
```

You can also scaffold directly with Copier, without the CLI:

```bash
uvx copier copy gh:Sandsy09/forge-template your-project --trust
```

`--trust` is required — the scaffold runs a `_tasks` step (git init, first
commit) after copying files.

## Two repos

| Repo | Role |
| --- | --- |
| [`forge-template`](https://github.com/Sandsy09/forge-template) | This repo. The templates themselves. |
| [`create-forge`](https://github.com/Sandsy09/create-forge) | The CLI that scaffolds from it. |

They're kept separate because Copier resolves template versions from PEP 440
git tags on this repo — merging the two would tangle the CLI's own releases
with the template's.

## What you get

Answer a handful of questions (project name, build backend, license, Python
versions to support, ...) and the scaffold gives you a `src/`-layout package
with `pyproject.toml` (uv or Hatchling), ruff, mypy and/or pyright, pytest
with coverage, a `poe`-driven task runner, pre-commit hooks, GitHub Actions
CI, and optional docs (MkDocs) and changelog generation (git-cliff). The
question schema in [copier.yml](copier.yml) is the source of truth for
exactly what's asked and what each answer controls.

## Layout

```
forge-template/
├── copier.yml               Question schema for the scaffold
├── pyproject.toml           This repo's OWN tooling (not part of the scaffold)
├── src/, tests/              ^ same
├── docs/adr/                 Why this repo is shaped the way it is
├── scripts/                 verify-ci.sh: push scaffolded combos, watch CI
├── .github/workflows/       This repo's own CI + release automation
└── template/                Everything here becomes the generated project
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the human workflow and
[CLAUDE.md](CLAUDE.md) for the invariants that keep `copier update` working
across projects generated at different points in this template's history; read
the latter before changing anything under `template/`. The
[canonical Forge vocabulary](docs/terminology.md) defines architectural terms,
the [Foundation guarantees](docs/foundation-guarantees.md) define the mandatory
outcomes every generated project receives, the
[Foundation scope](docs/foundation-scope.md) defines which concerns belong in
that baseline, the [Python support policy](docs/python-support.md) defines the
supported CPython window and lifecycle, the
[editor integration strategy](docs/editor-integration.md) keeps the baseline
and default profile editor-neutral, the
[configuration ownership conventions](docs/configuration-ownership.md) keep
runtime settings owner-local and explicitly injected, the
[environment-variable conventions](docs/environment-variables.md) define
owner-prefixed runtime inputs and explicit local dotenv behaviour, the
[structured logging capability](docs/structured-logging.md) defines
owner-local events and one entrypoint-owned logging configuration, the
[path and resource ownership conventions](docs/paths-and-resources.md) keep
runtime path and resource access owner-local and free of implicit process
context, the
[exception ownership conventions](docs/exception-ownership.md) keep
exceptions owner-local and require failures to be handled once rather than
silently dropped or logged repeatedly, the
[secret-handling safeguards](docs/secret-handling.md) keep secret-bearing
files out of version control without generating a mandatory scanner, the
[supply-chain provenance contract](docs/supply-chain-provenance.md) defines
desired SBOM and release-provenance behaviour without generating either yet,
the [GitHub Action pinning policy](docs/github-action-pinning.md) keeps remote
workflow dependencies immutable and maintainable, and
[docs/adr/](docs/adr/) records why significant decisions were made.

## License

MIT — see [LICENSE](LICENSE).
