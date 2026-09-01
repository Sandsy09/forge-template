# 43. Split invariants out of CLAUDE.md

## Status

Accepted

## Context

[ADR 0001](0001-record-architecture-decisions.md) records that "`CLAUDE.md`
keeps the operational rules and links out here for rationale, rather than
carrying both." That arrangement mixed two audiences in one file: agent
onboarding ("What this is", "Layout", "Current state") and six hard rules
that bind any change under `template/` or `copier.yml`, human or agent
alike. `CLAUDE.md`'s own subtitle — "Guidance for Claude Code working in
this repository" — undersold the rules, and both `CONTRIBUTING.md` and
`README.md` had to send readers into an agent-facing file to find them.

[#7](https://github.com/Sandsy09/forge-template/issues/7) was deferred out
of #3 (the ADR directory) during planning, since moving a file under heavy
active edit warranted its own review. #3 already removed the third mixed
concern — rationale for past decisions — into `docs/adr/`; this closes the
remaining split.

The six invariants are cited by number from eleven places, six of them
already-accepted ADRs. Records are immutable, so the rules could not simply
move and leave those citations to resolve on their own terms — the
numbering itself had to be treated as a stable contract.

## Decision

Move the six numbered invariants verbatim into
[docs/invariants.md](../invariants.md), alongside this repository's other
canonical contracts and indexed from `docs/README.md`. `CLAUDE.md` keeps a
`## Invariants` section holding only a numbered index with anchor links back
into the new file, so "invariant 4" still resolves in one hop from either
document.

The `1`–`6` numbering does not change and is never renumbered; a future rule
appends as `7`. Every reference this ADR could edit without violating another
record's immutability was repointed at `docs/invariants.md` in the same
change. The six ADRs that already say "CLAUDE.md invariant N" are left
exactly as written — they were accurate descriptions of the repository when
recorded, and an ADR is not amended after acceptance.

No wording, numbering, or rationale within any invariant changed — this is a
location split, not a content revision.

## Consequences

- `docs/invariants.md` is now the canonical home for the six rules;
  `CLAUDE.md` narrows toward agent onboarding, layout, validation commands,
  and backlog state.
- `CONTRIBUTING.md`, `README.md`, `.github/pull_request_template.md`,
  `.pre-commit-config.yaml`, and two `src/forge_template` docstrings now
  point at `docs/invariants.md` instead of `CLAUDE.md`'s invariant section.
- The six ADRs mentioning "CLAUDE.md invariant N" remain unedited and are not
  errata; a reader following one still lands on the correct rule via
  `CLAUDE.md`'s index.
- The `1`–`6` numbering is now an explicit citation contract: any future
  invariant is appended, never inserted or renumbered, so existing citations
  — in ADRs, code comments, and this record — stay correct indefinitely.
- No template, Copier answer, generated output, runtime dependency, tag, or
  release changes as a result of this decision.
