# GitHub Setup and Applied Taxonomy

The shared taxonomy is defined by
[`create-forge/.github/labels.toml`](https://github.com/Sandsy09/create-forge/blob/main/.github/labels.toml)
and was applied to `forge-template` on 2026-08-23.

## Labels

Every roadmap child has:

- one `type:*` label;
- one or more `area:*` labels;
- one `priority:*` and one `size:*` label;
- its `roadmap:00` through `roadmap:09` label;
- `status:blocked` or `status:deferred` where applicable;
- `cross-repo` when it participates directly in cross-repository work; and
- `breaking-change` when Copier migrations or coordinated compatibility work
  may be required.

Epics use `type:epic`, the stage and priority labels, and `cross-repo`. Stock
labels have not yet been pruned because the pending local
`docs/contributing-branch-workflow` branch still refers to `bug` and
`enhancement`; update those issue forms to `type:bug` and `type:feature` before
running the shared label sync with `--prune`.

## Milestones

Matching milestones exist in both repositories:

1. Foundation Contract — Stage 00
2. Foundation Baseline — Stages 01–03
3. Runtime & Security — Stages 04–05
4. Composition Contract — Stage 06
5. CLI Scaffolding — Stage 07
6. Reference Archetypes — Stage 08
7. Blueprint Compatibility — Stage 09

## Relationship rules

- GitHub's native parent/sub-issue relationship is authoritative for epic
  membership.
- GitHub's native `blocked by` relationship is authoritative for sequencing,
  including cross-repository dependencies.
- Counterpart epics are linked as related work in their issue bodies.
- Completed-before-import work is evidence in the live index, not a
  retrospective closed issue.

## ID convention

`FT-xx.xx` identifies `forge-template` work and `CF-xx.xx` identifies
`create-forge` work. Keep these IDs in titles alongside GitHub's issue numbers.
