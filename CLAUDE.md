# CLAUDE.md — forge-template

Guidance for coding agents working in this repository. Contributor workflow,
test selection, pull requests, and releases live in
[CONTRIBUTING.md](CONTRIBUTING.md) and are intentionally not repeated here.

## What this is

`forge-template` provides two related generation surfaces:

- A direct [Copier](https://copier.readthedocs.io/) template for an updatable
  Python library.
- A public Python composition engine with independent Library, CLI Application,
  and Data Science archetypes plus optional platform and tooling components.

The companion [`create-forge`](https://github.com/Sandsy09/create-forge)
repository owns the CLI, interactive prompts, destination staging, filesystem
writes, Git initialisation, and project updates. The repositories remain
separate because Copier resolves template releases from this repository's
PEP 440 Git tags. Do not merge their responsibilities; see
[ADR 0003](docs/adr/0003-two-repo-split.md).

## Repository architecture

```text
forge-template/
├── copier.yml                 Direct-Copier question schema; must stay at root
├── template/                  Files rendered by the direct-Copier path
├── src/forge_template/
│   ├── engine.py              Supported discovery, planning, and render facade
│   ├── project_spec.py        Strict generation-request models
│   ├── component_manifest.py  Component metadata and compatibility validation
│   ├── composition.py         Deterministic selection and application order
│   ├── file_conflicts.py      Target collision and extension-point rules
│   ├── template_variables.py  Option resolution and render namespace
│   ├── generation_metadata.py Reproduction and update metadata
│   ├── foundation/            Mandatory generated-project content
│   └── components/            Archetype, capability, and platform packages
├── tests/                     Contract, render, build, update, and sweep tests
├── docs/                      Living contracts, ADRs, and roadmap records
└── scripts/                   Wheel, label, and generated-CI verification
```

`copier.yml`, the root tooling, and `src/` describe this repository; they are
not copied into a direct-Copier project. `_subdirectory: template` preserves
that boundary. Conversely, everything under `template/` is generated-project
source and must not be used to document this repository itself.

The engine composes package-bound content in memory:

1. A strict `ProjectSpec` selects exactly one archetype and any compatible
   capabilities or platform.
2. The implicit Foundation source supplies the neutral project baseline.
3. Component manifests declare owned content, dependencies, conflicts,
   options, contributions, and update metadata.
4. Composition applies Foundation, archetype, capabilities, then platform in
   deterministic order and resolves only declared extension points.
5. Rendered output is validated before it is returned to a client.

The engine never owns destination staging or finalisation. Keep generation
planning and validation side-effect free; clients such as `create-forge` own
filesystem and subprocess effects.

## Implementation rules

The living contracts are indexed in [docs/README.md](docs/README.md). Read the
contracts governing the area being changed instead of inferring behaviour
from historical ADRs or roadmap prose.

### Direct-Copier schema and content

`copier.yml` is a compatibility contract for projects that may later run
`copier update`.

- `build_backend` and `versioning` are linked. `versioning_resolved` is the
  hidden computed value and is the only versioning value `template/` may read.
- `python_matrix` is computed from the supported window in `python_all`.
  Follow [the Python support policy](docs/python-support.md) for every window
  change.
- Computed questions use `when: false` and place their value in `default`.
- `github_org` deliberately defaults to an empty value; the CLI may supply it.
- Conditional files and directories use conditional Jinja names. A rendered
  empty name omits the path.
- Files that need no rendering have no `.jinja` suffix. `py.typed` must remain
  byte-empty.

The direct-Copier path remains Library-only. Do not make it read engine
catalogue content or silently give the engine ownership of Copier update
behaviour.

### Engine and component boundaries

- Each archetype owns its package shape and never copies or reads another
  archetype's resources.
- Foundation stays conservative, universal, and runtime-free. Optional or
  owner-specific behaviour belongs in a component.
- Components interact through manifest-declared dependencies, conflicts, and
  extension contributions. Only published extension points may be extended;
  file overrides are denied.
- The organisation-policy protocol is a downstream-client contract. Do not
  add policy parsing, policy resolution, policy-specific exports, or new engine
  errors for it here.
- The supported client boundary is the top-level `forge_template` facade
  described by [the engine API contract](docs/template-engine-api.md). Do not
  expose arbitrary catalogue roots or test-only Foundation/component override
  seams.
- Generation metadata and `plan_update` describe reproducible output changes.
  The engine plans updates; the client performs merges and protects user files.
- Component and protocol compatibility changes follow
  [the compatibility policy](docs/compatibility-policy.md), including its
  deprecation window and structured unsupported-version reporting.

### Package boundary

The published wheel contains the public facade, Foundation, and component
resources. It deliberately excludes this repository's check-only modules:
`adr.py`, `github_actions.py`, `render.py`, and `schema.py`. Keep dependencies
used only by those modules out of runtime requirements. Built distributions
must continue to pass `scripts/check_wheel.py`.

## Invariants — do not break these

The full rationale and migration consequences live in
[docs/invariants.md](docs/invariants.md). The stable rules are:

1. [Generated output must be pre-commit clean](docs/invariants.md#1-generated-output-must-be-pre-commit-clean).
2. [`.copier-answers.yml` must be generated and committed](docs/invariants.md#2-copier-answersyml-must-be-generated-and-committed).
3. [Moving or deleting files under `template/` breaks updates](docs/invariants.md#3-moving-or-deleting-files-under-template-breaks-updates).
4. [Jinja and GitHub Actions both use `${{ }}`](docs/invariants.md#4-jinja-and-github-actions-both-use--).
5. [`.gitattributes` is mandatory at both roots](docs/invariants.md#5-gitattributes-is-mandatory-in-the-template-and-at-repo-root).
6. [User-facing template changes require a release tag](docs/invariants.md#6-every-template-change-that-should-reach-users-needs-a-tag).

## Conventions

- Python 3.11+, strict mypy, and Ruff formatting/linting.
- `from __future__ import annotations` in Python modules.
- Pydantic contract models are strict and reject unknown input.
- Public results and errors remain deterministic and structured.
- External GitHub Actions use full reviewed commit SHAs with version comments.
- Architectural decisions are immutable Nygard-format records in
  [docs/adr/](docs/adr/); living behaviour belongs in `docs/*.md` contracts.
- Historical and planned work belongs in the appropriate
  [roadmap directory](docs/), not in this file.

## Current state

`forge-template 0.5.0` is the current published engine line. Its catalogue has
fourteen components: three archetypes (`library`, `cli`, `data-science`), ten
capabilities (`changelog`, `coverage`, `documentation`, `dotenv-example`,
`dependabot`, `jupyter`, `pre-commit`, `pyright`, `renovate`, and
`scientific-python`), and the `github` platform. Data Science requires Jupyter;
Documentation requires Library; Dependabot requires GitHub and conflicts with
Renovate.

`main` is ahead of that release: FT-20.01 to FT-20.03 have added and validated a
fifteenth component, the `streamlit` archetype, which is unreleased and
unpublished until a later `forge-template` release. It has no `requires` or
`conflicts`, its owned content is fixed by
[docs/streamlit-archetype.md](docs/streamlit-archetype.md), its line and
acceptance matrix by
[docs/streamlit-compatibility-and-acceptance.md](docs/streamlit-compatibility-and-acceptance.md).

The public engine supports component-manifest protocols 1–3, generation
metadata, deterministic full-catalogue rendering, and reproducible update
planning. The direct-Copier compatibility path remains available and
Library-only. Current contracts are in [docs/README.md](docs/README.md), past
decisions in [docs/adr/](docs/adr/), and completed or proposed feature lines in
the roadmap directories.
