# Architecture Decision Records

Records of significant decisions, in [Nygard
format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

- [0001 — Record architecture decisions](0001-record-architecture-decisions.md)
- [0002 — Copier over Cookiecutter](0002-copier-over-cookiecutter.md)
- [0003 — Two-repo split](0003-two-repo-split.md)
- [0004 — Build backend + versioning](0004-build-backend-and-versioning.md)
- [0005 — git-cliff over hand-written changelogs](0005-git-cliff-for-changelogs.md)
- [0006 — mypy default, pyright optional](0006-mypy-default-pyright-optional.md)
- [0007 — MkDocs pinned below 2.0](0007-mkdocs-pinned-below-2.md)
- [0008 — Remove `make` as a task_runner choice](0008-remove-make-task-runner.md)
- [0009 — Branch and pull request workflow](0009-branch-and-pr-workflow.md)
- [0010 — Canonical Forge architectural terminology](0010-forge-architectural-terminology.md)
- [0011 — Outcome-based Forge Foundation guarantees](0011-forge-foundation-guarantees.md)
- [0012 — Keep Forge Foundation conservative and runtime-free](0012-conservative-foundation-scope.md)
- [0013 — Adopt a rolling CPython support policy](0013-python-support-policy.md)
- [0014 — Keep Foundation and the default profile editor-neutral](0014-editor-neutral-foundation.md)
- [0015 — Keep runtime configuration owner-local and explicitly injected](0015-owner-local-runtime-configuration.md)
- [0016 — Keep environment inputs owner-local and dotenv explicit](0016-owner-local-environment-inputs.md)

Add a new record by copying the most recent one and incrementing the number.
Records are immutable: supersede them rather than editing.

`uv run poe check` verifies the set stays consistent — filenames match
`NNNN-slug.md`, numbers are contiguous with no gaps or duplicates, every
record is linked here, and each has all four Nygard headings. See
[src/forge_template/adr.py](../../src/forge_template/adr.py).
