# Stage 11 — Reusable Data Science Capabilities

## Epic

[FT-EPIC-11 / forge-template#97](https://github.com/Sandsy09/forge-template/issues/97)
delivers the first production capability layer selected by Stage 10.

## Dependencies

FT-EPIC-11 is natively blocked by FT-EPIC-10, now complete.

## Child sequence

1. [FT-11.01 / #105](https://github.com/Sandsy09/forge-template/issues/105)
   is complete: the three additive Foundation
   [capability-tooling extension points](../../../extension-points.md#capability-tooling-extends-the-same-foundation-content)
   (`pyproject-development-dependencies`, `pyproject-task-definitions`,
   `pyproject-aggregate-check`) and
   [ADR 0049](../../../adr/0049-foundation-capability-tooling-extension-points.md).
2. [FT-11.02 / #106](https://github.com/Sandsy09/forge-template/issues/106)
   is complete: the optionless package-bound `jupyter` capability, generated
   safe notebook validator, Foundation contributions, tests, and [ADR
   0050](../../../adr/0050-production-jupyter-capability.md).
3. [FT-11.03 / #107](https://github.com/Sandsy09/forge-template/issues/107)
   implements the independently applicable `scientific-python` capability.
4. [FT-11.04 / #108](https://github.com/Sandsy09/forge-template/issues/108)
   validates omission, independent and combined selection, compatibility,
   deterministic rendering, and packaged resources.

FT-11.01 and FT-11.02 are complete. `FT-11.03 / #107` is the next actionable
implementation; FT-11.04 remains blocked only by FT-11.03 because its other
predecessor is complete.

## Entry criteria

- Stage 10's contract is accepted — all four children are complete, including
  the [compatibility and acceptance contract](../../../data-science-compatibility-and-acceptance.md).
- Capability ownership, applicability, options, and compatibility are fixed.
- The Foundation extension points a development-tooling capability needs are
  published (FT-11.01, complete).

## Outcomes

- Add reviewed package-bound capability manifests and content.
- Define options, requirements, conflicts, contributions, and compatibility.
- Use only published extension points and deterministic composition order.
- Expose path-free descriptors through the public discovery facade.
- Prove valid, omitted, conflicting, and inapplicable selections.
- Preserve a provider-, framework-, and domain-neutral Foundation.

## Exit criteria

The selected capability layer is production-ready, documented, deterministic,
and suitable for the Data Science archetype. Stage 12 may then implement that
archetype against real components.

## Non-goals

This stage does not implement the archetype, client UX, plugins, or a remote
component registry.
