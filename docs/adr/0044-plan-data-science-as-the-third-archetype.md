# 44. Plan Data Science as the third production archetype

## Status

Accepted

## Context

[ADR 0034](0034-select-cli-application-reference-archetype.md) selected CLI
Application as Forge's second reference archetype and rejected Data Science
*for then*: notebook conventions, scientific dependencies, datasets, and a
larger compatibility matrix would have committed an unproven composition
engine to a domain too early.

That sequencing risk has now changed. Library and CLI Application are
independent production components, the Foundation boundary has survived a
two-archetype review, create-forge consumes public discovery and rendering
behind `--engine-preview`, and Stages 06–09 prove composition, client, policy,
and no-copy boundaries. create-forge #91 also replaces Library-shaped engine
prompts with descriptor-driven component options.

The next roadmap must choose a useful third shape without treating notebooks,
scientific dependencies, data, models, or deployment as universal Foundation
concerns. It must also avoid choosing a fashionable stack before its ownership
and maintenance costs are evaluated.

## Decision

Plan Data Science as Forge's third production archetype through Stages 10–14
of the two-repository Data Science roadmap.

The product direction is a package-backed, notebook-oriented project. The
archetype will compose with reusable optional capabilities rather than absorb
every scientific concern or add domain dependencies to Foundation. Stage 10
will decide the minimal useful shape, the exact archetype/capability/platform
boundary, technology choices, safeguards, validation, and compatibility
impact before implementation issues are filed.

Delivery through create-forge remains behind `new --engine-preview`. The
default direct-Copier Library path and its update contract remain unchanged;
an engine cutover requires a separate future decision.

Only epic issues are filed during roadmap creation. Each epic is reviewed and
then decomposed into native child issues, preventing an unaccepted stack or
component boundary from being encoded prematurely in the backlog.

## Consequences

- Data Science is the planned third archetype, while exact libraries and
  tooling remain deliberately undecided until Stage 10.
- Forge will exercise production capabilities for the first time, including
  generic capability selection in create-forge.
- The roadmap adds no component, dependency, protocol, public API, generated
  output, tag, or release by itself.
- Library and CLI Application remain independent; Data Science may not inherit
  from or access either component's resources.
- Plugins, remote component registries, organisation-specific content, and
  the default engine cutover remain out of scope.
- The completed Foundation roadmap remains historical evidence at its stable
  path; the Data Science work is documented separately under `roadmap-v2`.
