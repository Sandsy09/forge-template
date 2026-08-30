# Stage 08 — Reference Archetype Validation

## Repository ownership

### forge-template

- **FT-08.01 — Define Library archetype contract** — complete via the
  [canonical contract](../../../library-archetype.md) and
  [ADR 0031](../../../adr/0031-library-archetype-contract.md).
- **FT-08.02 — Migrate the Library archetype to the composition contract** —
  complete via the same [contract](../../../library-archetype.md) and
  [ADR 0033](../../../adr/0033-migrate-library-production-catalogue.md). The
  installed production catalogue now contains `library`, proven by real
  `uv build` output across all three packaging modes
  (`tests/test_library_build.py`).
- **FT-08.03 — Select and define the second reference archetype contract** —
  complete via the [CLI Application
  contract](../../../cli-application-archetype.md) and
  [ADR 0034](../../../adr/0034-select-cli-application-reference-archetype.md).
- **FT-08.04 — Implement the CLI Application reference archetype** —
  complete via the same [CLI Application
  contract](../../../cli-application-archetype.md) and
  [ADR 0035](../../../adr/0035-implement-cli-application-archetype.md). The
  installed production catalogue now contains `cli` alongside `library`,
  proven by real `uv build`, install, console-script, and `python -m` output
  (`tests/test_cli_build.py`).
- **FT-08.05 — Run composition architecture review**

### create-forge

- **CF-08.01 — Expose Library archetype through create-forge**
- **CF-08.02 — Expose CLI Application through create-forge**
- **CF-08.03 — Run CLI archetype-parity review**
- **CF-08.04 — Extend end-to-end generation to the public engine**

The accepted Library contract defined manifest protocol `2`, option-schema
protocol `2`, one implicit Foundation content source, and the `0.3.0` planning
owner migration as requirements for FT-08.02, implemented in full; none was
implemented by the documentation-only FT-08.01 decision.

FT-08.03 selected `cli` as an independent, optionless executable distribution
over Foundation. FT-08.04 implemented it in the package-bound engine
catalogue, which now contains both `cli` and `library`; the direct Copier
path remains unchanged.

## Stage completion rule

- [ ] Repo-local issues are complete or explicitly deferred.
- [ ] Cross-repository blockers are resolved.
- [ ] Public contracts changed by this stage are documented and versioned.
- [ ] No implementation concern is duplicated across repositories.
