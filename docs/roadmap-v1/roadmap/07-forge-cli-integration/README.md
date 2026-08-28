# Stage 07 — Forge CLI Integration

## Repository ownership

### forge-template

- [x] [**FT-07.05 — Add generated-project validation**](../../../generated-project-validation.md)
  — the public engine validates each immutable rendered result before return;
  [ADR 0030](../../../adr/0030-generated-project-validation.md) records the
  boundary.

### create-forge

- **CF-07.01 — Implement shared create pipeline**
- **CF-07.02 — Implement interactive project creation**
- **CF-07.03 — Implement non-interactive CLI parity**
- **CF-07.04 — Implement safe filesystem generation**
- **CF-07.06 — Create end-to-end CLI generation tests**

## Stage completion rule

- [x] Repo-local issues are complete or explicitly deferred.
- [x] Cross-repository blockers are resolved or retained as completed
  predecessors for create-forge.
- [x] Public contracts changed by this stage are documented/versioned.
- [x] No implementation concern is duplicated across repositories.

The forge-template side of Stage 07 is complete. The shared stage remains open
in create-forge for pipeline, filesystem-finalisation, and end-to-end work.
