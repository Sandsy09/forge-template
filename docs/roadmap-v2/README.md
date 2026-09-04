# Forge Data Science Roadmap — Two-Repository Edition

This roadmap continues the completed
[Forge Foundation roadmap](../roadmap-v1/README.md) through Stages 10–14.
It plans the next production archetype without reopening the Foundation,
composition, reference-client, or Blueprint decisions completed in Stages
00–09.

The target is a package-backed, notebook-oriented Data Science project with
reusable optional capabilities. Exact scientific libraries, notebook front
ends, data-versioning systems, model tooling, and deployment integrations are
not selected here; Stage 10 owns those decisions.

Delivery remains behind `create-forge new --engine-preview`. Retiring the
default direct-Copier path is a separate future initiative.

Stages 10–13 are complete, and forge-template's provider side of Stage 14 is
now complete too. The package-bound Data Science catalogue is available in
[`forge-template 0.4.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0),
and current `create-forge` `main` consumes it behind `--engine-preview` with
the `forge-template>=0.4,<0.5` range. FT-14.01 completed the provider boundary
review, FT-14.02 completed cross-repository validation of both `main`
branches paired locally, and FT-14.03 published that same unchanged catalogue
as the reviewed
[`forge-template 0.4.1`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.1)
— `FT-EPIC-14` is closed. `create-forge`'s client-side rollout (`CF-EPIC-14`)
remains open.

## Repository roles

- **forge-template** owns the Data Science contract, capabilities, archetype,
  composition review, generated content, and engine releases.
- **create-forge** owns discovery-driven user input, ProjectSpec construction,
  diagnostics, staging, lock finalisation, and end-to-end client validation.

See the [architecture](ARCHITECTURE.md),
[ownership model](REPOSITORY-OWNERSHIP.md), and
[stage roadmap](ROADMAP.md) for the complete boundary.

## Live GitHub work

Six epics and 24 child issues are filed across the two repositories. GitHub
issue bodies and native parent/dependency relationships are authoritative:

- [forge-template epic index](https://github.com/Sandsy09/forge-template/blob/main/docs/roadmap-v2/github-issues/forge-template/ISSUE-INDEX.md)
- [create-forge epic index](https://github.com/Sandsy09/create-forge/blob/main/docs/roadmap-v2/github-issues/create-forge/ISSUE-INDEX.md)
- [cross-repository dependency matrix](github-issues/CROSS-REPO-DEPENDENCIES.md)
- [GitHub setup and taxonomy](github-issues/GITHUB-SETUP.md)
