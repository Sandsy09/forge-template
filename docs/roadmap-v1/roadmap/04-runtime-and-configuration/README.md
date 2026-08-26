# Stage 04 — Runtime and Configuration

## Repository ownership

### forge-template

- [x] [**FT-04.01 — Define configuration ownership and extension conventions**](../../../configuration-ownership.md)
  ([ADR 0015](../../../adr/0015-owner-local-runtime-configuration.md),
  [#24](https://github.com/Sandsy09/forge-template/issues/24))
- [x] [**FT-04.02 — Define environment-variable conventions**](../../../environment-variables.md)
  ([ADR 0016](../../../adr/0016-owner-local-environment-inputs.md),
  [#25](https://github.com/Sandsy09/forge-template/issues/25))
- [x] [**FT-04.03 — Define structured logging capability**](../../../structured-logging.md)
  ([ADR 0017](../../../adr/0017-owner-local-structured-logging.md),
  [#26](https://github.com/Sandsy09/forge-template/issues/26))
- [x] [**FT-04.04 — Define path and resource ownership conventions**](../../../paths-and-resources.md)
  ([ADR 0018](../../../adr/0018-owner-local-paths-and-resources.md),
  [#27](https://github.com/Sandsy09/forge-template/issues/27))
- **FT-04.05 — Define exception ownership conventions**

### create-forge

- **CF-04.01 — Define template-engine source and version resolution**

## Stage record

FT-04.01 establishes owner-local typed configuration fragments and explicit
entrypoint assembly. FT-04.02 adds owner-prefixed environment names,
deterministic source precedence, one explicitly enabled local dotenv file, and
provider-neutral environment identity. FT-04.03 assigns event vocabularies to
runtime owners and process-wide structured logging configuration to one
entrypoint-owned capability, with a portable envelope and redaction boundary.
FT-04.04 keeps path and resource access owner-local, forbids implicit process
context such as the current working directory or a discovered project root,
and resolves FT-04.02's deferred `.env` location by requiring the runtime
entrypoint to receive it explicitly rather than search for it. All four are
documentation-only decisions; the current Library scaffold remains unchanged.
The remaining exception concern stays with its listed owner.

## Stage completion rule

- [ ] Repo-local issues are complete or explicitly deferred.
- [ ] Cross-repository blockers are resolved.
- [ ] Public contracts changed by this stage are documented/versioned.
- [ ] No implementation concern is duplicated across repositories.
