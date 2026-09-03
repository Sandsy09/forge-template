# Stage 12 — Data Science Archetype

## Epic

[FT-EPIC-12 / forge-template#98](https://github.com/Sandsy09/forge-template/issues/98)
adds the third production archetype and publishes a consumable engine release.
**Complete** — all four children, the epic, and its milestone are closed.

## Dependencies

FT-EPIC-12 is natively blocked by FT-EPIC-11, now complete.

## Child sequence

1. [FT-12.01 / #109](https://github.com/Sandsy09/forge-template/issues/109)
   implements the independent `data-science` archetype with its hard Jupyter
   requirement. **Complete** — FT-12.01 /
   [ADR 0053](../../../adr/0053-production-data-science-archetype.md).
2. [FT-12.02 / #110](https://github.com/Sandsy09/forge-template/issues/110)
   adds its clean starter notebook and documented data/model/artefact layout.
   **Complete** — FT-12.02 /
   [ADR 0054](../../../adr/0054-data-science-notebook-and-artefact-layout.md).
3. [FT-12.03 / #111](https://github.com/Sandsy09/forge-template/issues/111)
   validates supported compositions and all three archetype regressions.
   **Complete** — FT-12.03 /
   [ADR 0055](../../../adr/0055-validate-data-science-generated-projects.md).
4. [FT-12.04 / #112](https://github.com/Sandsy09/forge-template/issues/112)
   publishes and verifies the `forge-template` 0.4.0 compatibility line.
   **Complete** — [preparation PR #128](https://github.com/Sandsy09/forge-template/pull/128),
   [`v0.4.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0),
   [PyPI](https://pypi.org/project/forge-template/0.4.0/), and the
   [published artefact audit](../../../data-science-validation.md#published-040-release-verification).

The four children formed a strict sequence beginning after FT-11.04. All four
are complete; the released provider line makes create-forge Stage 13
actionable.

## Entry criteria

- Stage 11 capabilities are production-ready, and their composition is
  validated (FT-11.04 / ADR 0052, complete).
- The Stage 10 contract supplies complete generated-project acceptance rules.

## Outcomes

- Add an independent Data Science manifest and owned content tree.
- Implement the package-plus-notebooks shape through reviewed extensions.
- Compose supported capability combinations without implicit mutation.
- Validate restoration, locking, packaging, imports, notebooks, and tests.
- Prove Library and CLI Application behavior remains unchanged.
- Publish the compatible engine line required by create-forge Stage 13.

## Exit criteria

The installed engine catalogue discovers and renders Data Science from a
released, verified package, with no cross-archetype resource access and no
Forge dependency in generated projects. **Met** by the published `0.4.0`
artefacts and both accepted Data Science composition audits.

## Non-goals

The direct-Copier tree, stored answers, and create-forge UX do not change here.
