# 31. Define Library as a distributable-package archetype over Foundation

Date: 2026-08-29

## Status

Accepted

## Context

Forge already generates a production-quality Python Library through one
monolithic Copier tree. Stage 06 established ProjectSpec, component manifests,
composition, rendering, and validation, but deliberately left the installed
production catalogue empty. Migrating the current output without first
separating universal Foundation concerns from Library-only packaging concerns
would either duplicate the baseline in every archetype or make file ownership
implicit again.

The existing manifest and option-schema protocols model component-owned
content only. A real archetype must instead extend mandatory neutral files
owned by Foundation. The public planning model similarly identifies every
planned file with a component ID, which cannot truthfully represent a
Foundation-owned file.

## Decision

Define `library` as the distributable Python-package additions layered over
one implicit, package-bound Foundation content source. Library owns the
`src/` package shape, PEP 517/621 packaging contributions, wheel and sdist
behaviour, inline typing, package version exposure, explicit module API, and
package-specific validation. It initially adds no runtime dependency and no
publication, credential, signing, or attestation behaviour.

The production Library component will use manifest protocol `2`, component
version `1.0.0`, ProjectSpec protocol `1`, and Python compatibility `>=3.11`.
Its option-schema protocol `2` will replace the linked legacy packaging
answers with `packaging_mode` and validate `initial_version` through the first
string format constraint, `pep440`.

Make Foundation mandatory, non-selectable, undiscoverable, and applied before
the selected component order. Manifest protocol `2` identifies contribution
targets with a discriminated Foundation or component owner. The public plan
will use the same distinction instead of `owner_component_id`; that
incompatible pre-1.0 facade change requires package version `0.3.0` when the
migration is implemented. Retain manifest protocol `1` parsing for existing
component-to-component fixtures and keep ProjectSpec protocol `1`.

The complete living contract, including stable extension points, legacy
answer mapping, packaging modes, and acceptance evidence, is
[library-archetype.md](../library-archetype.md).

## Consequences

- Foundation remains one shared source rather than being copied into Library
  or represented as a selectable pseudo-component.
- Library has a bounded package contract that another archetype need not
  inherit.
- Mixed neutral files can accept explicit Library contributions without
  transferring their ownership or allowing implicit replacement.
- Existing Copier answers have a deterministic mapping into one packaging
  option, but migration and replay compatibility remain FT-08.02 work.
- Optional documentation, release, coverage, updater, editor, configuration,
  and GitHub concerns retain their capability or platform owners.
- FT-08.02 must implement manifest and option-schema protocol `2`, the
  discriminated planning owner, the production catalogue, and package version
  `0.3.0`. This decision itself changes no code, template, schema, answer,
  generated output, public API, tag, or release.
