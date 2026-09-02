# forge-template

A [Copier](https://copier.readthedocs.io/) template and public composition
engine for modern Python projects. The engine catalogue offers independent
**library** and **CLI Application** archetypes; the compatibility-preserving
direct-Copier path remains Library-only and supports `copier update` through
three-way merges.

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

The public engine used by `create-forge --engine-preview` is also installable
directly — `pip install forge-template` or `uv add forge-template` — for
clients that consume
[`docs/template-engine-api.md`](docs/template-engine-api.md)'s typed
discovery/validation/rendering API without going through Copier or
`create-forge` at all. The published wheel ships the engine facade and its
Foundation/component content only; this repository's own tooling
(`docs/adr/` checks, `copier.yml`/`template/` inspection) is not part of the
installable package — see
[ADR 0036](docs/adr/0036-publish-the-engine-to-pypi.md).

The [accepted Data Science shape](docs/data-science-archetype.md) is an
independent, package-backed, notebook-oriented archetype composed with the
accepted [`jupyter` and `scientific-python` capability
contracts](docs/data-science-capabilities.md). Its
[Stage 10–14 roadmap](docs/roadmap-v2/README.md) tracks the six epics and 24
filed child issues across both repositories. The default direct-Copier Library
path remains unchanged.

## Two repos

| Repo | Role |
| --- | --- |
| [`forge-template`](https://github.com/Sandsy09/forge-template) | This repo. The templates and side-effect-free composition engine. |
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

```text
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

See [CONTRIBUTING.md](CONTRIBUTING.md) for the human workflow,
[docs/invariants.md](docs/invariants.md) for the rules that keep
`copier update` working across projects generated at different points in
this template's history, and [CLAUDE.md](CLAUDE.md) for agent guidance; read
the invariants before changing anything under `template/`. The
[canonical Forge vocabulary](docs/terminology.md) defines architectural terms,
the [Foundation guarantees](docs/foundation-guarantees.md) define the mandatory
outcomes every generated project receives, the
[Foundation scope](docs/foundation-scope.md) defines which concerns belong in
that baseline, the [Library archetype contract](docs/library-archetype.md)
defines the distributable-package additions composed over it, and the
[CLI Application archetype contract](docs/cli-application-archetype.md)
defines the implemented executable reference shape. The
[Data Science archetype contract](docs/data-science-archetype.md) defines the
future third shape's package, notebook, working-tree, and capability ownership
without yet implementing it. The [initial Data Science capability
contracts](docs/data-science-capabilities.md) define reusable notebook tooling
and an independently optional scientific runtime stack, and the
[notebook, data, and model safeguards](docs/notebook-data-and-model-safeguards.md)
fix the fail-closed notebook-validation order, deterministic failures, and
safe diagnostics for that future archetype. The
[composition architecture review](docs/composition-architecture-review.md)
records the Stage 08 boundary corrections proven by both archetypes, and
the [Python support policy](docs/python-support.md) defines the
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
workflow dependencies immutable and maintainable, the
[ProjectSpec protocol](docs/project-spec.md) defines the strict, serialisable
generation request for the composition engine, the
[organisation policy protocol](docs/organisation-policy.md) defines the
strict downstream selection constraints applied before that effective request
is constructed, proved executably by the
[organisation-policy reference fixture](docs/organisation-policy-fixtures.md),
the
[component manifest protocol](docs/component-manifests.md) defines strict
bundled metadata and compatibility for its component catalogue, the
[composition order contract](docs/composition-order.md) defines the
deterministic order that catalogue applies in, the
[file conflict and override rules](docs/file-conflicts.md) define its output
target, disposition, and collision-safety rules, the
[safe override and extension points](docs/extension-points.md) contract
denies any `override` grant and publishes the extension-point inventory as a
versioned contract, the
[template variable contract](docs/template-variables.md) defines the rendered
variable namespace and component option vocabulary, the
[stable template-engine API](docs/template-engine-api.md) exposes typed,
side-effect-free discovery, validation, planning, and in-memory rendering, the
[generated-project validation contract](docs/generated-project-validation.md)
checks every rendered result before a client receives it, the
[Forge-Blueprint compatibility policy](docs/compatibility-policy.md) defines
every versioned engine axis, compatible ranges, and deprecation windows a
downstream client may rely on, the
[no-copy inheritance proof](docs/no-copy-inheritance.md) validates that an
independent downstream client can reuse package-bound Forge content through
the public facade without copying it, and
[docs/adr/](docs/adr/) records why significant decisions were made.

## License

MIT — see [LICENSE](LICENSE).
