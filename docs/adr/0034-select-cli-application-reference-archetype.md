# 34. Select CLI Application as the second reference archetype

Date: 2026-08-30

## Status

Accepted

## Context

Stage 08 needs a second archetype that is structurally different from the
Library production component and exercises composition behavior Library does
not. The choice must also be useful, maintainable, safe for existing Copier
updates, and bounded enough that one reference implementation does not turn
domain- or framework-specific behavior into Foundation policy.

The viable candidates were a CLI application, HTTP service, data pipeline,
and Data Science project. A service would prove more runtime configuration
and logging behavior, but would also select a server lifecycle, framework,
deployment model, and larger security surface. Pipeline ownership remains
ambiguous across schedulers, data sources, retries, and state. Data Science
would add notebooks, native/scientific dependencies, and a much larger
compatibility matrix.

Library already proves selectable packaging modes, an option schema, a
consumer import surface, inline typing, and package artifacts. The second
archetype should add a different executable boundary without inheriting or
depending on Library.

## Decision

Select **CLI Application**, canonical component ID `cli`, as the second
reference archetype.

Define it as an independent, package-bound archetype over the implicit
Foundation source. It uses manifest protocol `2`, component version `1.0.0`,
ProjectSpec protocol `1`, Python compatibility `>=3.11`, fixed
`uv-build-static` packaging, static version `0.1.0`, and no option schema,
requirements, or conflicts. Its command name derives from ProjectSpec's
repository name rather than duplicating that value in component options.

CLI Application owns one direct runtime dependency, `typer>=0.27,<1`, one
console-script entry point, equivalent `python -m` behavior, and the help,
version, and `hello` starter command contract. Use the supported `typer`
package, not the retired `typer-slim` migration shim.

Add neutral Foundation extension points for archetype metadata, runtime
dependencies, classifiers, and entry points when FT-08.04 implements the
component. Reuse the existing build-system, build-configuration, and README
points. Empty new points must leave Library output unchanged.

Implement `cli` only through the package-bound engine catalogue. Leave the
Library-only direct-Copier tree and its stored answers unchanged; add no
Copier migration. Keep `forge-template` package version `0.3.0`, ProjectSpec
protocol `1`, manifest protocol `2`, Foundation version `1`, and the public
engine facade unchanged.

The complete file, metadata, dependency, command, ownership, and acceptance
contract is
[cli-application-archetype.md](../cli-application-archetype.md).

## Consequences

- Forge gains a domain-neutral executable reference shape that proves runtime
  dependency and entry-point composition absent from Library.
- The CLI and Library components remain independent and select exactly one
  archetype over the same mandatory Foundation.
- The fixed build/version choice and absent option schema keep the second
  implementation and its test matrix deliberately bounded.
- Typer remains archetype-owned; Foundation gains no CLI runtime package,
  module, configuration, or error policy.
- Existing direct-Copier Library generations and updates remain unchanged.
- HTTP service, data pipeline, and Data Science shapes remain valid future
  decisions rather than implied parts of this archetype.
- FT-08.04 owns all behavior. This decision itself changes no manifest,
  Foundation source, engine code, template, schema, dependency, rendered
  output, public API, package version, tag, or release.
