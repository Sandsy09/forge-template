# 56. Confirm the three-archetype composition boundaries

Date: 2026-09-04

## Status

Accepted

## Context

ADR 0037 corrected the Foundation boundary after Library and CLI Application
first composed through the public engine. Forge-template `0.4.0` has since
added the Data Science archetype and the reusable Jupyter and Scientific
Python capabilities. Create-forge Stage 13 now exercises that catalogue
through the shared `--engine-preview` pipeline, making the planned Stage 14
review concrete.

The review must compare ownership and intentional duplication across the six
catalogue layers and their create-forge client, assess every selection and
composition surface, and leave a compatible release candidate for
cross-repository validation. It must also
record security, reproducibility, package-size, and maintenance consequences
without absorbing the later validation or release issues.

The executable audit found no production boundary defect. Foundation contains
no notebook, scientific, data/model, framework, provider, or client concern.
All ten valid compositions remain deterministic, and invalid selection,
requirement, kind, conflict, and option cases remain structured engine
failures before rendering. The gaps were in the Stage 08-specific review tests
and mutable documents that still described composition or client adoption as
future work.

## Decision

Retain the current Foundation, archetype, capability, and client boundaries.
Keep the seven byte-identical resource groups independently component-owned:
the three archetypes' package `__init__.py`, `py.typed`, and test-package
markers; Library and Data Science's smoke test; and CLI and Data Science's
static metadata, uv-build configuration, and build-system fragments. Their
892-byte raw duplication overhead is preferable to a package-shaped
Foundation, cross-archetype inheritance, or a capability with no independent
user value.

Retain the eleven Foundation extension points and their existing contributors.
Foundation continues to own `pyproject.toml`, `README.md`, and `.gitignore`;
selected components contribute additive, ordered fragments with explicit
`PlannedExtension` ownership. No component publishes another point or gains
merge/override authority.

Expand `tests/test_composition_architecture_review.py` to cover Data Science
with its required Jupyter capability, all ten valid compositions, the complete
duplicate inventory, classifier ownership, layout neutrality, and locked
quality contract. Expand `tests/test_extension_points.py` to cover every
production component and strengthen the Foundation exclusion vocabulary in
`tests/test_capability_composition.py`.

Update the living review and mutable contract/roadmap status to the real
Stage 13 client state. Do not rewrite ADR 0037 or another historical record.

Keep the source package at `0.4.0`, Library and CLI at `1.0.1`, and Data
Science, Jupyter, and Scientific Python at `1.0.0`. Keep every public API,
result model, error code, protocol tuple, manifest/schema shape,
extension-point identifier, discovery result, and rendered byte unchanged.
FT-14.02 owns cross-repository validation; FT-14.03 alone bumps and publishes
`0.4.1`.

## Consequences

- Foundation remains implicit, runtime-free, shape-neutral, provider-neutral,
  and free of Data Science or client orchestration concerns.
- Every retained duplicate and extension contribution has a named owner,
  rationale, and executable regression assertion.
- The ten accepted compositions retain deterministic planning, rendering,
  generated validation, and real Python 3.11/3.14 endpoint evidence.
- A local review wheel measured 72,566 bytes; the Foundation/component trees
  total 39,182 raw bytes across 60 files. FT-14.02 can compare its candidate
  against this reproducible point-in-time baseline.
- Create-forge `main` consumes the unchanged facade with
  `forge-template>=0.4,<0.5`; released create-forge `0.2.1` remains on the
  older `>=0.3.1,<0.4` range until Stage 14 publication.
- No template, Copier answer, component resource, engine implementation,
  dependency, golden digest, tag, release, or default-path cutover changes.
