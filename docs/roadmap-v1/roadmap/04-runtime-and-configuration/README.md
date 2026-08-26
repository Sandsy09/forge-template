# Stage 04 — Runtime and Configuration

## Repository ownership

### forge-template

- [x] [**FT-04.01 — Define configuration ownership and extension conventions**](../../../configuration-ownership.md)
  ([ADR 0015](../../../adr/0015-owner-local-runtime-configuration.md),
  [#24](https://github.com/Sandsy09/forge-template/issues/24))
- **FT-04.02 — Define environment-variable conventions**
- **FT-04.03 — Define structured logging capability**
- **FT-04.04 — Define path and resource ownership conventions**
- **FT-04.05 — Define exception ownership conventions**

### create-forge

- **CF-04.01 — Define template-engine source and version resolution**

## Stage record

FT-04.01 establishes owner-local typed configuration fragments and explicit
entrypoint assembly without changing the current Library scaffold. FT-04.02
remains responsible for environment sources and conventions; the remaining
runtime concerns stay with their listed owners.

## Stage completion rule

- [ ] Repo-local issues are complete or explicitly deferred.
- [ ] Cross-repository blockers are resolved.
- [ ] Public contracts changed by this stage are documented/versioned.
- [ ] No implementation concern is duplicated across repositories.
