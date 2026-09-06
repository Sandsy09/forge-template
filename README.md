# forge-template

[![PyPI](https://img.shields.io/pypi/v/forge-template)](https://pypi.org/project/forge-template/)

Project templates and a Python composition engine for building libraries,
command-line applications, and Data Science projects.

The easiest way to generate a project is with the companion CLI:

```bash
uvx create-forge new
```

**[Read the Forge user guide](https://sandsy09.github.io/create-forge/)**
for installation, project recipes, and troubleshooting.

## How the repositories fit together

| Repository | What it provides |
| --- | --- |
| **forge-template** | The generated project content and composition engine. |
| [create-forge](https://github.com/Sandsy09/create-forge) | The CLI for selecting templates, answering questions, and writing projects. |

You do not need to clone either repo for normal use. Their versions are
independent: this guide covers `forge-template 0.4.1` with
`create-forge 0.3.0`. Generated projects do not depend on Forge at runtime.

## Default: an updatable Python library

```bash
uvx create-forge new "My Library"
cd my-library
uv run poe check
```

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), Git,
and Python 3.11+ (uv can install Python). Configure your Git name and email
first: generation creates a repository and local commits.

The default Copier template includes a `src/` package, uv, Ruff, pytest with
coverage, mypy and/or pyright, pre-commit hooks, and GitHub Actions CI.
Choose uv or Hatchling packaging, static or Git-tag versioning where
supported, a license, dependency-update tooling, and optional MkDocs docs.

For regular use, `uv tool install create-forge` installs the CLI command;
`uv tool upgrade create-forge` updates it within its installation
constraints. See [installation and versions](https://sandsy09.github.io/create-forge/installation/)
for exact pins and engine-extra installation.

### Use Copier directly

```bash
uvx copier copy gh:Sandsy09/forge-template your-project --trust --vcs-ref v0.4.1
cd your-project
uv run poe check
```

Copier asks the template's own questions. `--trust` allows its tasks to
initialise Git, make local commits, install dependencies, and install hooks.
Only run template code you trust. Omit `--vcs-ref` to use the latest
suitable release tag. Through the companion CLI, the equivalent template
selection is `new --template library --ref v0.4.1`.

### Pull template updates

From a clean, committed Copier-generated project:

```bash
uvx create-forge update --dry-run
uvx create-forge update --ref v0.4.1
uv run poe check
```

Keep `.copier-answers.yml` committed. Review the diff, resolve conflicts,
and rerun checks before committing. A dry run validates the request without
applying it or producing a file-by-file diff. Direct Copier users can run
`uvx copier update --trust --vcs-ref v0.4.1` instead.

## Preview: project types and capabilities

The engine catalogue supports these independent project types:

| Archetype | Generated starting point |
| --- | --- |
| Library | A distributable package with three packaging modes. |
| CLI Application | A Typer application, console command, and command tests. |
| Data Science | A package, starter notebook, and ignored data/model paths. |

All share uv lockfiles, Ruff, mypy, pytest, and Poe tasks. Add **Jupyter**
for notebook tooling or **Scientific Python** for NumPy, pandas, Matplotlib,
and scikit-learn. Data Science requires Jupyter; Scientific Python is
optional. Both capabilities can also accompany Library or CLI Application.

```bash
uvx --from "create-forge[engine]==0.3.0" create-forge new "My Analysis" --engine-preview --archetype data-science --capability jupyter --yes --data license=mit
cd my-analysis
uv run --locked poe check
uv run poe notebook
```

The CLI's engine extra selects a compatible package (`>=0.4.1,<0.5`). These
preview flags are hidden from normal help. **Preview projects do not support
`create-forge update`** and do not receive the default Copier template's CI
or Git hook setup. See [project types](https://sandsy09.github.io/create-forge/projects/)
and [capabilities](https://sandsy09.github.io/create-forge/capabilities/).

## Use the engine from Python

For your own generator or organisation-specific client:

```bash
uv add forge-template
```

The [public engine API](docs/template-engine-api.md) discovers components,
validates requests, and renders files in memory. Your client handles
filesystem writes and command execution. Start with the
[reference index](https://sandsy09.github.io/create-forge/reference/) and its
independent downstream-client example. The engine is a Python library,
not a standalone scaffolding command.

## What's next

The Foundation and Data Science roadmaps are complete. Making the engine
the CLI's default workflow is planned but unscheduled. Follow
[open work](https://github.com/Sandsy09/forge-template/issues) and
[releases](https://github.com/Sandsy09/forge-template/releases), or suggest
a useful project type or capability.

## Feedback and contributing

- [Report generated-content bugs or request capabilities](https://github.com/Sandsy09/forge-template/issues/new/choose).
- [Correct this repo's documentation](https://github.com/Sandsy09/forge-template/issues/new?template=documentation.yml).
- [Suggest a shared guide or example](https://github.com/Sandsy09/create-forge/issues/new?template=documentation.yml).
- [Report a CLI problem](https://github.com/Sandsy09/create-forge/issues/new/choose).

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and PR checks and
[docs/invariants.md](docs/invariants.md) before changing generated content.
Report vulnerabilities through [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
