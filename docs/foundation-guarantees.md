# Forge Foundation Guarantees

This document defines the mandatory outcomes every successfully generated
Forge project receives from Foundation. It complements the
[canonical architectural terminology](terminology.md): that reference defines
what Foundation is, while this one defines what Foundation guarantees.

The guarantees are outcome-based. A tool, provider, or project layout may
change as Forge evolves, but the replacement must preserve the same outcome.
The current Library scaffold's implementation is mapped below for clarity; the
mapping does not make those implementation choices permanent.

## Contract and applicability

A **Foundation guarantee** is a property Forge must provide in every
successfully generated project. Archetypes, capabilities, platforms, profiles,
and organisation policies may strengthen a guarantee, but they may not weaken
or remove one.

The contract applies to the project state produced by Forge and, when the
future composition model exists, to the result of composition. It does not
prevent a project owner from changing their independent repository after
handoff. Foundation provides a sound starting contract rather than a runtime
enforcement framework inside generated projects.

The engine's canonical
[generated-project validation](generated-project-validation.md) enforces the
universal in-memory plan/output and metadata invariants that can be proved
before handoff. It does not replace the generated project's own quality
commands or the client's filesystem finalisation checks.

## Mandatory guarantees

### Reproducible development and validation environment

A clean supported environment can restore the project's development and
validation environment from version-controlled project metadata and committed
lock state. Required prerequisites are documented, and routine validation does
not depend on undeclared tools or configuration from the operator's
workstation.

This is declared-input repeatability: the same committed project state, lock
state, and supported environment restore the same dependency selections and
validation behaviour. It is not a promise of byte-identical generated trees or
build artifacts across every machine and point in time.

### Dependency locking

Dependencies used to develop, test, analyse, format, lint, and build the
project have committed, machine-readable lock state. Automation detects when
declared dependency metadata and that lock state have drifted.

The lock controls the project-owned development and validation environment. A
distributable Library archetype still declares compatible dependency ranges
for its consumers; it does not impose the project's development lock on their
environments.

### Static typing

At least one static type checker is configured for project-owned Python source
and exposed through a non-interactive command that fails when the configured
typing policy is violated. An archetype may widen coverage or strengthen the
policy, but it may not remove the type-checking gate.

### Automated testing

Every generated project includes an automated test suite, an initial
executable test that proves the generated project can be imported or exercised,
and a non-interactive failing test command. Archetypes and capabilities add
tests appropriate to the behaviour they contribute.

### Linting

Every generated project includes a configured linter and a non-interactive
check that fails on violations in the project-owned source it covers. Added
components participate in that linting contract or provide an equivalently
integrated check for their owned content.

### Deterministic formatting

Every generated project includes deterministic formatting configuration, a
command that applies it, and a non-mutating check that fails when tracked
content is not formatted. Formatting policy is repository-owned and does not
depend on an editor's local defaults. The
[editor integration strategy](editor-integration.md) preserves that neutral
contract while defining a path for future opt-in editor capabilities.

### CI readiness

Every generated project exposes a stable, non-interactive aggregate quality
contract that can be invoked from a clean environment. It covers formatting,
linting, type checking, and testing, and returns a failing status when any
constituent check fails.

Foundation does not require a particular automation provider. When a platform
integration supplies CI configuration, it runs the same underlying quality
contract used locally rather than defining a divergent standard. The current
monolithic Library scaffold includes GitHub Actions as its platform-shaped
integration. Its remote workflow dependencies follow the
[GitHub Action pinning policy](github-action-pinning.md), without turning that
provider-specific security mechanism into a Foundation guarantee.

### Environment and Forge independence

Normal development, testing, building, and runtime operation require only the
prerequisites documented by the generated project. They do not require the
`create-forge` package, an installed `forge-template` package, a checkout of
either Forge repository, or a Forge runtime dependency.

Template maintenance is a separate operation. Pulling template updates or
regenerating content may invoke Copier and access the template source, but a
project does not need to perform that maintenance to remain usable.

Runtime configuration is not a Foundation module or dependency. When an
archetype or capability needs settings, it follows the canonical
[configuration ownership conventions](configuration-ownership.md) while
preserving this independent-operation guarantee. Environment-backed settings
also follow the [environment-variable conventions](environment-variables.md),
which keep deployed inputs provider-neutral and local dotenv loading explicit.
Runtime code that discovered a project root or read from a source checkout
would silently reintroduce a Forge-repository dependency; the
[path and resource ownership conventions](paths-and-resources.md) keep path
and resource access free of that assumption so a project stays independent
once installed. A shared Forge base exception would create the same kind of
dependency at the point a caller wants to catch a project's own failures; the
[exception ownership conventions](exception-ownership.md) keep exception
types owner-local so catching them never requires a Forge import.

## Recommended conventions

The following practices reinforce the guarantees but are not themselves
universal Foundation requirements:

- provide one memorable aggregate command, conventionally named `check`;
- call the same underlying commands locally, in hooks, and in CI;
- keep pre-commit feedback fast while retaining comprehensive CI gates;
- collect coverage even when the project is not ready to enforce a threshold;
- strengthen typing, coverage thresholds, and test matrices as the project
  matures; and
- test additional operating systems when the project claims to support them.

A project may adopt stronger conventions. It may also replace an implementation
tool, provided the mandatory outcome remains intact.

## Current Library scaffold mapping

The v0.1.x Library scaffold is monolithic rather than composed from Foundation
and components. Its current behaviour nevertheless satisfies the contract as
follows:

| Guarantee | Current implementation evidence |
| --- | --- |
| Reproducible environment and dependency locking | `pyproject.toml` and `.python-version` declare the environment; generation creates and commits `uv.lock`; CI runs `uv lock --check` before synchronising dependencies. |
| Static typing | `type_checking` always selects mypy, pyright, or both; the selected checker is configured for source and tests and runs through the `typecheck` task and CI. |
| Automated testing | pytest, coverage configuration, and an initial import/version smoke test are present; the `test` task and CI run the suite. |
| Linting and formatting | Ruff owns lint and format policy; Poe exposes check/apply tasks, pre-commit provides local feedback, and CI runs non-mutating checks. |
| CI readiness | `uv run poe check` is the documented aggregate local contract; the generated GitHub Actions workflow runs the same formatting, linting, typing, and testing concerns, verifies builds, and pins remote actions under the [GitHub platform policy](github-action-pinning.md). |
| Environment and Forge independence | The generated repository owns its source, configuration, tasks, tests, and workflow and documents Python and uv as prerequisites. Neither Forge repository nor package is a development or runtime dependency. |

These named tools describe the current reference implementation. They may be
replaced by later decisions that preserve the guarantees.

## Non-guarantees and deferred decisions

Foundation does not currently promise:

- byte-identical generated trees or distribution artifacts;
- dependency installation, testing, or building without network access;
- support for every operating system;
- a universal coverage threshold;
- one type checker or strictness level; or
- one CI provider.

The first item is load-bearing for a future capability, not incidental: the
[supply-chain provenance contract](supply-chain-provenance.md)'s planned
release-provenance attestation records who built a distribution artifact and
where, but does not and cannot claim that artifact is independently
rebuildable byte-for-byte. Raising reproducibility to a guarantee would
require its own ADR superseding this contract.

[Python support policy](python-support.md) defines which CPython environments
Forge supports and how that window advances. The canonical [Foundation
scope](foundation-scope.md) defines what belongs in Foundation rather than an
archetype, capability, or platform. The
[ProjectSpec protocol](project-spec.md) now defines the effective generation
request, while composition enforcement remains accepted future work under
[create-forge ADR 0010](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0010-public-engine-integration-contract.md)
and Stage 06. This guarantee contract itself introduces no rendering API or
component engine.
