# Stage 06 — Extension and Composition Contract

## Repository ownership

### forge-template

- [x] [**FT-06.01 — Design ProjectSpec schema**](../../../project-spec.md) —
  protocol v1 and its executable models are defined by
  [ADR 0023](../../../adr/0023-projectspec-protocol-v1.md).
- [x] [**FT-06.02 — Define component manifest format**](../../../component-manifests.md) —
  strict TOML protocol v1, resource loading, and provisional compatibility
  validation are defined by
  [ADR 0024](../../../adr/0024-component-manifest-protocol-v1.md).
- **FT-06.03 — Define deterministic composition order**
- **FT-06.04 — Define file conflict and override rules**
- **FT-06.05 — Design template variable contract**
- **FT-06.06 — Create composition contract tests**
- **FT-06.07 — Expose stable template-engine API**

### create-forge

- **CF-06.01 — Implement canonical ProjectSpec builder**
- **CF-06.02 — Implement component discovery adapter**
- **CF-06.03 — Add cross-repository contract tests**

## Stage completion rule

- [ ] Repo-local issues are complete or explicitly deferred.
- [ ] Cross-repository blockers are resolved.
- [ ] Public contracts changed by this stage are documented/versioned.
- [ ] No implementation concern is duplicated across repositories.
