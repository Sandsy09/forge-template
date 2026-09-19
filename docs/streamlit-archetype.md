# Streamlit Archetype Contract

This document defines the `streamlit` archetype's project shape and ownership
boundaries. It is the canonical living contract accepted by
[ADR 0068](adr/0068-streamlit-project-shape.md) for
[FT-19.01](https://github.com/Sandsy09/forge-template/issues/157). Its review
obligations are **FT-ROADMAP-02-AC-01** (project shape, entry point,
dependency and task ownership and the deployment boundary, shared with
[FT-19.02](https://github.com/Sandsy09/forge-template/issues/158)),
**FT-ROADMAP-02-EX-01** (no cloud deployment, container orchestration,
authentication, database or FastAPI service surface) and
**FT-ROADMAP-02-EX-04** (no arbitrary Streamlit plugin ecosystem), the last two
shared with [FT-20.02](https://github.com/Sandsy09/forge-template/issues/160).

The archetype is implemented in two steps, both inside component `1.0.0`.
[FT-20.01](https://github.com/Sandsy09/forge-template/issues/159) ([ADR
0070](adr/0070-streamlit-archetype-implementation.md)) added the `streamlit`
component to the catalogue, so `discover_components()` returns fifteen
components, four of them archetypes, on the still-unreleased line that follows
the published [`forge-template` `0.5.0`](cutover-provider-release.md): the
package, launcher, in-process smoke test and six of the Foundation
contributions below.
[FT-20.02](https://github.com/Sandsy09/forge-template/issues/160) ([ADR
0071](adr/0071-streamlit-tasks-safeguards-and-composition.md)) completed it
with the `run` task, `.streamlit/config.toml`, the secrets ignore rule and the
README section, so the archetype now owns all seven paths and contributes all
nine points below.
[FT-20.03](https://github.com/Sandsy09/forge-template/issues/161) ([ADR
0072](adr/0072-validate-streamlit-generated-projects.md)) then proved it as a
generated project and as a distribution, recorded in
[streamlit-validation.md](streamlit-validation.md).
`tests/test_streamlit_contract.py` pins the live manifest against the table
below so the two cannot drift. Nothing here changes a Copier
template, question or generated Library output, and the direct-Copier path
stays Library-only.

## Archetype identity and fixed choices

Streamlit is an independent, package-backed archetype for an interactive data
application, composed over the same implicit Foundation as Library, CLI
Application and Data Science. Its identity and fixed project choices are:

| Concern | Contract |
| --- | --- |
| Component ID | `streamlit` |
| Display name | Streamlit |
| Component options | none |
| Packaging | `uv-build-static` |
| Build requirement | `uv_build>=0.12,<0.13` |
| Initial version | `0.1.0` |
| Runtime entry point | root `app.py`, run by `streamlit run app.py` |
| Console script | none |
| Intrinsic runtime dependencies | exactly one: `streamlit>=1.63,<2` |
| Development-only constraint | `numpy<2.5`, in the generated `dev` group only |

The component ID names the domain, as `library`, `cli` and `data-science` do.
It is the same string as the `streamlit` distribution it depends on; the two
are distinct namespaces, and the component is selected through the engine's
`components.archetype` field, never by a package name.

The fixed choices keep the first version focused on composition rather than
creating a packaging matrix. Because the component declares no option schema, a
valid Streamlit ProjectSpec uses `components.archetype = "streamlit"` and adds
no `streamlit` entry to `component_options`. The component version, the
engine-package line that first ships it, the supported Python window and the
capability matrix were FT-19.02's decisions and are fixed in the
[compatibility and acceptance contract](streamlit-compatibility-and-acceptance.md)
(component `1.0.0`, package line `0.6.0`, floor `>=3.11`); the generated
project's own `0.1.0` starting version is a separate axis from all of them.

The archetype uses PEP 517 and PEP 621 metadata and must build a wheel and a
source distribution. It contributes these classifiers; no Streamlit-specific
trove classifier exists:

- `Typing :: Typed`;
- `Environment :: Web Environment`; and
- `Topic :: Internet :: WWW/HTTP :: Dynamic Content`.

## Reserved generated shape

The production component owns this minimal tracked shape:

```text
app.py
src/<package_name>/__init__.py
src/<package_name>/app.py
src/<package_name>/py.typed
tests/__init__.py
tests/test_app.py
.streamlit/config.toml
```

The package is independent rather than inherited from any existing archetype.
Its root public API exports only `__version__`, resolved from installed
distribution metadata with the same deterministic `0.0.0` fallback the other
archetypes use. The `__init__.py`, `py.typed` and `tests/__init__.py` files are
byte-identical to `library`'s copies — copied into the archetype's own content
tree, never read across archetypes.

Root `app.py` and `.streamlit/config.toml` are sole-owner `create` content of
this archetype. Foundation publishes no file at either path, so nothing
collides, and its project-wide Ruff and mypy invocations already cover the
project root; no Foundation change is required.

## Application entry point

The real application lives in the typed package. `main()` in
`src/<package_name>/app.py` builds the page; root `app.py` is a thin launcher
that imports `main` from the package and calls it under an
`if __name__ == "__main__":` guard. Streamlit executes the launcher as a script
with that name, so `streamlit run app.py` is the one documented command. The
launcher exists because Streamlit runs its target as a script rather than an
importable module, and keeping application code in the package keeps it under
the same typing, linting and test regime as every other archetype.

The package root does not re-export `main`. There is no console script and no
`python -m` entry point; the `pyproject-entry-points` extension point stays
unfilled.

The starter application is a single page: a title, a short introduction and one
interactive widget — a text input that greets the name entered, `Hello, World!`
by default, as the CLI archetype's `hello` command does — using only Streamlit,
the generated package and the standard library. The title is the project name
held in a module-level `TITLE` constant, escaped for a Python string literal.
Free text reaches no other literal: the generated docstrings carry no project
name. A name containing a double quote is valid Python but may be re-quoted by
`ruff format`, which a project owner corrects with `poe format`. Streamlit's
`pages/` multipage convention is available to the project owner and is
documented in the generated README, but the archetype tracks no `pages/` tree or
placeholder — the same no-placeholder stance the Data Science working trees
take.

## Packaging and dependency contract

Streamlit uses one fixed packaging mode:

- static initial distribution version `0.1.0`;
- `uv_build>=0.12,<0.13` and `uv_build` as the PEP 517 backend;
- `src/<package_name>/` as the build module and source root;
- wheel and source-distribution output; and
- inline typing through `src/<package_name>/py.typed`.

Both artefacts contain only the module tree `src/<package_name>/`. The root
`app.py` launcher and `.streamlit/config.toml` are source-tree files, not
distribution content: the application runs from a checkout with
`streamlit run app.py`, and the wheel carries the typed package. This is
deliberate and consistent with the no-deployment boundary; the
[compatibility and acceptance contract](streamlit-compatibility-and-acceptance.md#package-build-and-install-requirements)
records the evidence and the acceptance requirements.

It declares exactly one direct runtime dependency:

```toml
dependencies = [
    "streamlit>=1.63,<2",
]
```

Streamlit and its transitive dependencies belong to this archetype, never to
Foundation. The bound was reviewed against official PyPI metadata on 19
September 2026. `1.64.0` was the newest release at that date, released four
days earlier; the floor is the previous settled minor line:

| Dependency line | Reviewed lower release | `Requires-Python` |
| --- | --- | --- |
| `streamlit>=1.63,<2` | [1.63.0](https://pypi.org/pypi/streamlit/1.63.0/json) | `>=3.10` |

The lower release accepts Forge's Python 3.11 floor. `streamlit.testing.v1` and
a `py.typed` marker ship inside the same distribution, so neither the test
surface nor strict type checking adds a *runtime* dependency. That the whole
supported Python window resolves was verified by FT-19.02 (see the
[dependency evidence](streamlit-compatibility-and-acceptance.md#python-and-dependency-evidence));
the executable endpoint check is FT-20.03's
([streamlit-validation.md](streamlit-validation.md)).

Type checking does need one development-only constraint, which FT-19.02's
resolution evidence did not exercise and FT-20.01's first end-to-end run found.
Streamlit requires only `numpy<3`, so on Python 3.12 and later the lock selects
NumPy 2.5, whose type stubs use PEP 695 `type` statements. Foundation's `mypy`
targets the project's Python floor (3.11) and cannot parse that syntax, so a
default project failed its own `poe check`. The archetype therefore contributes
`"numpy<2.5"` through `pyproject-development-dependencies`, which lands in the
`dev` dependency group and never in the wheel metadata, mirroring the
`numpy>=2.4,<2.5` ceiling `scientific-python` already carries. The cap is
reviewed when Forge's Python floor moves past 3.11 or the type-check target
otherwise changes ([ADR 0070](adr/0070-streamlit-archetype-implementation.md)).

The declared bound is a normative compatibility line. Lock movement within it
is routine reviewed maintenance; changing either bound needs an upstream
compatibility review and resolution across the accepted Python range, and
crossing the upper bound requires a superseding ADR. Automated dependency
updates may not cross it or raise the Python floor silently.

## Configuration and secret safeguards

The archetype tracks one minimal, deterministic `.streamlit/config.toml`:

```toml
[browser]
gatherUsageStats = false
```

Streamlit collects usage statistics by default; a generated project must not
begin reporting them without an explicit choice by its owner. No other setting
is preselected.

`.streamlit/secrets.toml` is Streamlit's own secret file. It is ignored through
the archetype's `gitignore-project-shape` contribution as the root-anchored
`/.streamlit/secrets.toml`. Foundation's ignore rules contain no `.streamlit`,
`*.toml` or `app` pattern, so this rule shadows no tracked file, satisfying the
[ignore-shadowing audit](secret-handling.md#secret-bearing-files-stay-out-of-version-control).

**No `.streamlit/secrets.toml.example` is generated.** The `.env` file remains
the single documented secret channel. Foundation ignores the `.env` family and
negates `!.env.example`; the tracked, placeholder-only `.env.example` file itself
is owned by the optional `dotenv-example` capability, so a project that does not
select it has no example file at all. Either way the
[placeholder-only rule](secret-handling.md#the-tracked-example-carries-placeholders-only)
has one enforced target and no second example to keep in step. The archetype
adds no dotenv loader; runtime configuration follows the owner-local
[configuration](configuration-ownership.md) and
[environment-variable](environment-variables.md) conventions. Generation-time
inputs are never secret sources.

## Run and check tasks

The archetype contributes one task through Foundation's
`pyproject-task-definitions` point, which an archetype may use exactly as a
capability does:

```toml
run = "streamlit run app.py"
```

The archetype contributes **nothing** to `pyproject-aggregate-check`. `check`
must stay a terminating quality gate; a server task inside it would hang every
generated project's checks and CI. The unchanged aggregate keeps Foundation's
lock, format, lint, type-check and test steps, so the app's own tests run under
`poe check` while `poe run` is deliberately outside it.

## Tests

The archetype owns `tests/test_app.py`. It drives the launcher in process
through `streamlit.testing.v1.AppTest`, which executes the script and exposes
the rendered elements without binding a port, launching a browser or starting a
subprocess. It asserts that the script raises no exception and that the starter
page renders its title and responds to its widget.

A relative path given to `AppTest.from_file` resolves against the *calling
file*, so from `tests/` the string `"app.py"` would look for `tests/app.py`.
The test must therefore build the launcher path from its own location, as
`Path(__file__).parents[1] / "app.py"`. As with the CLI archetype, tests assert
the app contract and meaningful content rather than snapshotting framework
output: the title equals the package's `TITLE`, the default page greets the
world, and entering a name greets that name. The smoke constructs its `AppTest`
with a 10-second `default_timeout`.

The wall-clock bounds on this smoke — 10 seconds per run and 600 seconds for the
whole project check — and the acceptance matrix that runs it across selections
and Python versions are fixed in the
[compatibility and acceptance contract](streamlit-compatibility-and-acceptance.md#time-bounded-non-serving-smoke).

## Foundation extension requirements

Streamlit uses only points Foundation already publishes; no new extension
point is required and the published inventory in
[extension-points.md](extension-points.md) is unchanged:

| Extension point | Used | Carries |
| --- | --- | --- |
| `pyproject-build-system` | yes | the `uv_build` backend |
| `pyproject-archetype-metadata` | yes | static `version = "0.1.0"` |
| `pyproject-build-configuration` | yes | `[tool.uv.build-backend]` module settings |
| `pyproject-runtime-dependencies` | yes | `"streamlit>=1.63,<2",` |
| `pyproject-classifiers` | yes | the three classifiers above |
| `pyproject-task-definitions` | yes | the `run` task |
| `readme-project-shape` | yes | project structure and how to run |
| `gitignore-project-shape` | yes | `/.streamlit/secrets.toml` |
| `pyproject-entry-points` | no | there is no console script |
| `pyproject-aggregate-check` | no | `check` must terminate |
| `pyproject-development-dependencies` | yes | the development-only `numpy<2.5` cap; `AppTest` itself ships in `streamlit` |

Empty points render away without changing other archetypes' output, and
unsupported or competing contributions continue to fail under the existing
[ordering, extension and collision contracts](file-conflicts.md).

## Ownership map

Each generated concern has one owner, including when several contribute to a
mixed root file.

| Concern | Owner |
| --- | --- |
| Neutral project identity, licence, prerequisites, lock and quality guarantees, root guidance, repository hygiene and the `.env` ignore rules with the `!.env.example` negation | Foundation |
| Root `pyproject.toml`, `README.md` and `.gitignore` source files | Foundation, accepting only reviewed component contributions |
| Package, test and root launcher paths, packaging and version metadata, classifiers, the Streamlit runtime dependency and the starter page | Streamlit archetype |
| `.streamlit/config.toml` and the `/.streamlit/secrets.toml` ignore entry | Streamlit archetype, the latter through `gitignore-project-shape` |
| The `run` task | Streamlit archetype, through `pyproject-task-definitions` |
| Project-shape and run guidance within the root README | Streamlit archetype, through `readme-project-shape` |
| The tracked, placeholder-only `.env.example` file | optional `dotenv-example` capability |
| Notebook authoring and tooling | optional [`jupyter`](data-science-capabilities.md#jupyter-capability) capability |
| Optional scientific runtime dependencies | optional [`scientific-python`](data-science-capabilities.md#scientific-python-capability) capability |
| CI, repository-provider, delivery and deployment integrations | Selected platform components |
| Default or constrained selections | Profiles and organisation policies, which own no rendered files |
| Discovery-driven input, ProjectSpec construction, staging, lock finalisation and atomic destination placement | `create-forge` |

Streamlit may reuse Foundation extension points and public template variables.
It may not read or contribute through Library, CLI Application or Data Science
resources, select any of them, or introduce inheritance between archetypes. The
two capabilities are optional here, unlike the `requires` edge Data Science
declares on Jupyter; the four selections and their compatibility are fixed in the
[compatibility and acceptance contract](streamlit-compatibility-and-acceptance.md#valid-and-invalid-selections),
and the archetype's manifest declares no `requires` or `conflicts` for them.

Foundation remains provider-, framework-, organisation- and domain-neutral.
Streamlit, its testing harness and its configuration never become universal
Foundation dependencies.

## Explicit exclusions

The archetype excludes, for this contract and for its implementation:

- cloud deployment, including Streamlit Community Cloud configuration;
- container images, Compose files and orchestration;
- authentication, login flows and identity providers;
- databases, ORMs and persistence layers;
- FastAPI and any other service or API framework;
- any arbitrary Streamlit plugin or component ecosystem: no custom-component
  build step, no `components.declare_component` scaffolding and no third-party
  component registry; and
- environment-backed configuration loaders, logging setup, network clients,
  daemon behaviour, publication, signing, attestation and provider
  integration.

Platforms own deployment and delivery. No remote registry or plugin execution is
introduced, and generated code depends on no Forge runtime package.

These exclusions govern the generated project's own surface and code. They do
not forbid Streamlit's dependency tree, which already includes a web-server
stack (`starlette` and `uvicorn`) as transitive dependencies of the pinned
`streamlit` line; the archetype neither imports nor exposes them.

## Client boundary

`create-forge` discovers component descriptors and constructs an effective
ProjectSpec through the supported public engine facade. It must not copy this
shape, hard-code the `streamlit` identifier, recreate component requirements or
render archetype content itself. The engine remains the authority for
selection, options, compatibility, planning, rendering and generated-project
validation; the client remains responsible for filesystem effects and lock
finalisation.

## Deferred decisions

[FT-19.02](https://github.com/Sandsy09/forge-template/issues/158) accepted ([ADR
0069](adr/0069-streamlit-composition-compatibility-and-acceptance.md)) the
capability matrix (no capability, Jupyter only, Scientific Python only and
both), the supported Python and dependency window, package build and install
requirements, committed-lock restoration, the time-bounded non-serving smoke,
the component version and the target provider compatibility line, in the
[compatibility and acceptance
contract](streamlit-compatibility-and-acceptance.md).
[FT-20.01](https://github.com/Sandsy09/forge-template/issues/159) implemented
the package, launcher, smoke test and six contributions, and
[FT-20.02](https://github.com/Sandsy09/forge-template/issues/160) the tasks,
safeguards and capability composition, and
[FT-20.03](https://github.com/Sandsy09/forge-template/issues/161) validated the
result.
[FT-20.04](https://github.com/Sandsy09/forge-template/issues/162) publishes it.
None of the Stage 19 decisions or FT-20.01 to FT-20.03 bumps a version or
releases.
