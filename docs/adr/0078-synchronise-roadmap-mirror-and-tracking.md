# 78. Synchronise the roadmap mirror and tracking conventions

Date: 2026-09-26

## Status

Accepted

## Context

[FT-24.03](https://github.com/Sandsy09/forge-template/issues/193): Stages 22 to
29 were filed as 37 issues (10 epics, 27 children) without a roadmap pack,
`roadmap:N` labels, stage milestones, native sub-issue or blocked-by edges, or
reconciled status labels. The validator was written for two fixed packs. The
original review text is not in either repository.

## Decision

1. **A new pack, `docs/roadmap-v5`.** Completed packs and ADRs stay untouched;
   the pack holds the exact filed bodies, hash-pinned, in both repositories.
2. **A per-pack rules table in `scripts/check_roadmaps.py`.** v3 and v4 behave as
   before; v5 has its own counts, headings, priority rule, milestone rule and
   traceability rule.
3. **Traceability is derived from the filed bodies** and says so. The validator
   recomputes it. *Rejected:* inventing review identifiers.
4. **Live state is not frozen.** Open/closed and `status:*` appear only in a
   regenerated, dated snapshot; GitHub stays authoritative.
5. **Native relationships are the authority** and the milestone convention is
   retained. `scripts/roadmap_sync.py` reconciles them: read first, dry run by
   default, add-only, idempotent, with a read-back `verify`.
6. **Body files are lint-exempt**, not reformatted, because their hash is the
   proof of fidelity.

## Consequences

- The roadmap can be checked, mirrored and reconciled mechanically; drift in a
  body, hash, parent, milestone or mirror byte fails the validator or `verify`.
- Older stale status labels (Stages 14–18) are reported, not changed.
- Reconciliation writes to GitHub and is run deliberately; nothing in CI writes.
- No template, engine, protocol, component or version changes.
