# Stage 09 — Blueprint Compatibility

## Repository ownership

### forge-template

- **FT-09.01 — Define organisation policy model** — complete via the
  [canonical protocol](../../../organisation-policy.md) and
  [ADR 0038](../../../adr/0038-organisation-policy-selection-model.md).
  Strict JSON policy protocol `1` constrains component selections without
  adding an executable parser, resolver, or rendering authority.
- **FT-09.02 — Define safe override and extension points** — complete via the
  [canonical contract](../../../extension-points.md) and
  [ADR 0039](../../../adr/0039-deny-policy-file-overrides.md). The reserved
  `override` grant is denied; the complete sanctioned extension surface and
  the published, versioned content extension-point inventory are pinned by
  `tests/test_extension_points.py`.
- **FT-09.03 — Create generic downstream policy reference fixture** —
  complete via the
  [canonical fixture doc](../../../organisation-policy-fixtures.md) and
  [ADR 0040](../../../adr/0040-organisation-policy-reference-fixture.md).
  Five placeholder policy documents and a test-only reference resolver
  prove protocol `1`'s full authority order, merge semantics, and all 17
  structured-failure detail codes, plus one end-to-end resolution rendered
  through the real production catalogue -- pinned by
  `tests/test_organisation_policy_fixture.py`.
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
FT-09.02 decision closes the question those semantics deliberately left open:
no policy, client, or component gains `override` authority over another
owner's content, and the complete safe extension surface is published as a
versioned contract. The FT-09.03 fixture proves both decisions executably
against neutral placeholder data, with no shipped public resolver -- that
remains unscheduled in this roadmap. The downstream consumption hook is
create-forge's own work.

## Stage completion rule

- [ ] Repo-local issues are complete or explicitly deferred.
- [ ] Cross-repository blockers are resolved.
- [ ] Public contracts changed by this stage are documented/versioned.
- [ ] No implementation concern is duplicated across repositories.
