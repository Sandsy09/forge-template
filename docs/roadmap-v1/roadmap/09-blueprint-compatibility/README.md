# Stage 09 — Blueprint Compatibility

## Repository ownership

### forge-template

- **FT-09.01 — Define organisation policy model** — complete via the
  [canonical protocol](../../../organisation-policy.md) and
  [ADR 0038](../../../adr/0038-organisation-policy-selection-model.md).
  Strict JSON policy protocol `1` constrains component selections without
  adding an executable parser, resolver, or rendering authority.
- **FT-09.02 — Define safe override and extension points**
- **FT-09.03 — Create generic downstream policy reference fixture**
- **FT-09.04 — Define Forge-Blueprint compatibility policy**
- **FT-09.05 — Validate no-copy inheritance model**

### create-forge

- **CF-09.01 — Define downstream policy-consumption hook**
- **CF-09.02 — Create downstream CLI integration reference**
- **CF-09.03 — Validate create-forge is a reference client, not a framework dependency**

The FT-09.01 decision fixes order-independent policy defaults, required and
forbidden selection validation, ProjectSpec provenance, and future structured
failure semantics. A downstream client still owns policy-source trust,
explicit-choice tracking, ProjectSpec construction, and diagnostics. The
reference fixture and consumption hook will implement this contract later in
Stage 09.

## Stage completion rule

- [ ] Repo-local issues are complete or explicitly deferred.
- [ ] Cross-repository blockers are resolved.
- [ ] Public contracts changed by this stage are documented/versioned.
- [ ] No implementation concern is duplicated across repositories.
