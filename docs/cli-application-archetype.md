# CLI Application Archetype Contract

This document defines the additions the Forge `cli` archetype makes to the
mandatory [Foundation](foundation-scope.md). It is the canonical living
contract accepted by
[ADR 0034](adr/0034-select-cli-application-reference-archetype.md) and
implemented by FT-08.04
([ADR 0035](adr/0035-implement-cli-application-archetype.md)).

FT-08.04 introduced this contract in the installed engine catalogue at
package version `0.3.0`, beside the [Library archetype](library-archetype.md)
it neither inherits from nor reads resources from. It changes no Copier
template, question, or generated output: the released Copier path still
renders only the Library tree, unchanged, while `create-forge --engine-preview`
selects either public-engine archetype. The Stage 08
[composition review](composition-architecture-review.md) corrects their
shared Foundation boundary at package `0.3.2` and component `1.0.1`.

## Selection rationale

CLI Application is the second reference archetype because it adds an
executable application boundary without tying Forge to a business domain,
network protocol, deployment platform, or data ecosystem. It is useful on
its own and exercises composition behavior the
[Library archetype](library-archetype.md) does not:

- one archetype-owned runtime dependency;
- console-script and module entry points;
- application-specific distribution metadata;
- installed command behavior rather than a consumer import API; and
- a complete archetype with no component options.

The rejected alternatives are deferred, not forbidden:

| Candidate | Why it is not reference archetype two |
| --- | --- |
| HTTP service | It would exercise runtime configuration and logging deeply, but would also select a server lifecycle, ASGI framework, deployment assumptions, and a wider security/maintenance surface. |
| Data pipeline | Scheduler, data-source, retry, state, and execution-model ownership are not yet neutral enough to define one representative contract. |
| Data Science | Notebook conventions, native/scientific dependencies, datasets, and a materially larger compatibility matrix would commit Forge prematurely to one domain. |

## Archetype boundary

CLI Application is an installable, executable Python distribution composed
over Foundation. It owns:

- the `src/<package_name>/` application package;
- fixed PEP 517 build behavior and static PEP 621 version metadata;
- the generated console script and `python -m` entry point;
- the Typer application and starter command behavior;
- the one direct runtime dependency required by that behavior; and
- command-, installation-, and artifact-specific validation.

Foundation continues to own neutral identity, licence, root guidance,
repository hygiene, the declared quality environment, and aggregate check
commands. Mixed files do not transfer ownership: Foundation owns
`pyproject.toml` and `README.md`, while CLI Application contributes reviewed
sections through declared extension points.

CLI Application does not inherit from, select, require, or read resources
from Library. The two are independent archetypes layered over the same
implicit Foundation source; a ProjectSpec selects exactly one.

## Production component contract

The production manifest at `src/forge_template/components/cli/component.toml`
has this identity:

| Field | Required value |
| --- | --- |
| `manifest_version` | `2` |
| `id` | `cli` |
| `name` | `CLI Application` |
| `kind` | `archetype` |
| `version` | `1.0.1` |
| `compatibility.projectspec_protocols` | `[1]` |
| `compatibility.requires_python` | `>=3.11` |
| `requires` / `conflicts` | empty |
| `options_schema` | omitted |

The component has no option schema. A valid CLI ProjectSpec therefore uses
`components.archetype = "cli"` and does not add a `cli` entry to
`component_options`.

The console command is derived from `ProjectSpec.project.repository_name`.
Forge must not ask for or serialize a duplicate `command_name` option. The
Python import package remains `ProjectSpec.project.package_name`.

## Packaging and dependency contract

CLI Application uses one fixed packaging mode:

- static initial distribution version `0.1.0`;
- `uv_build>=0.12,<0.13` and `uv_build` as the PEP 517 backend;
- `src/<package_name>/` as the build module and source root;
- wheel and source-distribution output; and
- inline typing through `src/<package_name>/py.typed`.

It declares exactly one direct runtime dependency initially:

```toml
dependencies = [
    "typer>=0.27,<1",
]
```

The supported package is `typer`, not `typer-slim`. Upstream retains
`typer-slim` only as a migration shim and directs new projects to install
Typer itself. Typer and its transitive dependencies belong to CLI Application,
never Foundation.

The generated project metadata includes the `Environment :: Console`
classifier and this console script:

```toml
[project.scripts]
<repository_name> = "<package_name>.cli:app"
```

The angle-bracket values above are rendered from ProjectSpec; they are not
new component options.

## Package and command contract

The owned initial tree is:

```text
src/<package_name>/
├── __init__.py
├── __main__.py
├── cli.py
└── py.typed
tests/
├── __init__.py
└── test_cli.py
```

The package root exposes only `__version__` through `__all__` initially.
`__version__` reads the installed distribution metadata and retains the
Library contract's deterministic `0.0.0` fallback when metadata is
unavailable.

`<package_name>.cli` exposes the documented module-level Typer application
`app`. The console entry point invokes that object, while `__main__.py` calls
the same object so `python -m <package_name>` has equivalent behavior. The
package root does not re-export `app`.

The initial command surface is:

- no arguments: print help to stdout and exit `0`;
- `--help`: print help to stdout and exit `0`;
- `--version`: print `<repository_name> <installed-version>` to stdout and
  exit `0` without invoking a command;
- `hello [NAME]`: default `NAME` to `World`, print `Hello, <NAME>!` to stdout,
  and exit `0`; and
- invalid commands or arguments: use Typer's normal non-zero usage-error path.

The README contribution documents installation for development, console and
module invocation, the starter command, and where to add commands. It does
not promise byte-stable Typer help styling; tests assert the command contract
and meaningful content rather than snapshotting framework decoration.

## Foundation extension requirements

CLI Application reuses these existing Foundation extension points:

- `pyproject-build-system`;
- `pyproject-build-configuration`; and
- `readme-project-shape`.

FT-08.04 added these provider- and archetype-neutral points to the
Foundation-owned `pyproject.toml` source:

- `pyproject-archetype-metadata` for static version metadata -- renamed from
  the Library-specific `pyproject-library-metadata` FT-08.02 originally
  published, since both archetypes need the identical job;
- `pyproject-runtime-dependencies` inside the project dependency array;
- `pyproject-classifiers` inside the classifier array; and
- `pyproject-entry-points` after the core project metadata.

CLI Application contributes only its owned version, Typer dependency,
console classifier, and script table through those points. Empty points must
render away without changing Library output. Unsupported or competing
contributions continue to fail under the existing ordering, extension, and
collision contracts; no implicit replacement is introduced.

## Runtime and platform boundaries

The initial archetype adds no environment-backed configuration, dotenv
loader, logging setup, secret, network client, persistence, daemon behavior,
publication, signing, attestation, deployment, or provider integration.

Future runtime behavior follows the owner-local
[configuration](configuration-ownership.md),
[environment-variable](environment-variables.md),
[structured-logging](structured-logging.md),
[path/resource](paths-and-resources.md), and
[exception](exception-ownership.md) contracts. Documentation sites,
changelogs, coverage policy, dependency updates, pre-commit feedback, editor
integration, and GitHub files retain their capability or platform owners.

## FT-08.04 implementation and acceptance boundary

FT-08.04 implements `cli` only in the package-bound engine catalogue. It
adds no archetype question, conditional tree, migration, or answer to
`copier.yml` or `template/`. The direct-Copier path remains Library-only, so
existing Library updates remain safe by construction. Future `create-forge`
selection consumes engine discovery rather than duplicating this metadata.

Implementation introduced the archetype in `forge-template` `0.3.0` and the
reviewed boundary correction moves its component version to `1.0.1` in
package `0.3.2`. ProjectSpec protocol `1`, manifest protocol `2`, Foundation
version `1`, and the public engine facade remain unchanged.

Acceptance, proven by `tests/test_cli_archetype.py` (fast, render-level) and
`tests/test_cli_build.py` (the `archetype` pytest marker, `uv run poe
archetype`, real `uv build`):

- deterministic discovery, planning, and rendering with both `library` and
  `cli` packaged;
- no source-path leakage or public catalogue override;
- the exact metadata, dependency, entry-point, and command behavior above;
- isolated wheel and sdist builds, installation, artifact inspection, console
  invocation, and module invocation;
- successful generated-project validation and aggregate quality checks --
  including the generated `cli.py`/`__main__.py`/`test_cli.py` themselves
  passing `uv run --locked poe check` (lock drift, Ruff format/lint,
  `mypy --strict`, pytest)
  inside the rendered project, not merely importing; and
- explicitly reviewed structural evidence (not byte-for-byte, since an empty
  extension marker line is consumed along with its own newline) that the four
  new Foundation extension points leave Library output unchanged.

## Current evidence and deferred work

The production catalogue now contains both `cli` and `library`, proven
end-to-end: `discover_components()` returns both descriptors,
`plan_generation`/`render_project` compose either one with Foundation into a
real project, and `uv run poe archetype` builds a real wheel and sdist,
installs them, and exercises the documented console-script and `python -m`
command contract for real.

`create-forge#10` completed generic interactive and non-interactive selection
for this component without recreating its questions, defaults, metadata, or
rendering rules.
