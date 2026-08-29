# Stage 08 — Reference Archetype Validation

## Repository ownership

### forge-template

- **FT-08.01 — Define Library archetype contract** — complete via the
  [canonical contract](../../../library-archetype.md) and
  [ADR 0031](../../../adr/0031-library-archetype-contract.md).
- **FT-08.02 — Migrate the Library archetype to the composition contract**
- **FT-08.03 — Select and define the second reference archetype contract**
- **FT-08.04 — Implement the selected second reference archetype**
- **FT-08.05 — Run composition architecture review**

### create-forge

- **CF-08.01 — Expose Library archetype through create-forge**
- **CF-08.02 — Expose the second archetype through create-forge**
- **CF-08.03 — Run CLI archetype-parity review**
- **CF-08.04 — Extend end-to-end generation to the public engine**

The accepted Library contract defines manifest protocol `2`, option-schema
protocol `2`, one implicit Foundation content source, and the `0.3.0` planning
owner migration as requirements for FT-08.02. None is implemented by the
documentation-only FT-08.01 decision.

Archetype two remains intentionally generic until
[FT-08.03](https://github.com/Sandsy09/forge-template/issues/42) records the
selection and contract.

## Stage completion rule

- [ ] Repo-local issues are complete or explicitly deferred.
- [ ] Cross-repository blockers are resolved.
- [ ] Public contracts changed by this stage are documented and versioned.
- [ ] No implementation concern is duplicated across repositories.
