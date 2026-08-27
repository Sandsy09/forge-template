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
- [x] [**FT-06.03 — Define deterministic composition order**](../../../composition-order.md) —
  tier and within-tier order, cross-tier dependency handling, and
  catalogue-wide cycle rejection are defined by
  [ADR 0025](../../../adr/0025-deterministic-composition-order.md).
- [x] [**FT-06.04 — Define file conflict and override rules**](../../../file-conflicts.md) —
  output targets, the create/extend/merge/override disposition table,
  extension-point declaration, and catalogue-wide contribution validation
  are defined by
  [ADR 0026](../../../adr/0026-file-conflict-and-override-rules.md).
- [x] [**FT-06.05 — Design template variable contract**](../../../template-variables.md) —
  the rendered variable namespace, the Forge-owned option-schema format, and
  required/unknown-option rejection rules are defined by
  [ADR 0027](../../../adr/0027-template-variable-contract.md).
- [x] [**FT-06.06 — Create composition contract tests**](../../../composition-fixtures.md) —
  golden composed-output fixtures, on-disk invalid-catalogue scenarios, and
  the determinism guarantee are defined by
  [ADR 0028](../../../adr/0028-composition-contract-fixtures.md).
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
