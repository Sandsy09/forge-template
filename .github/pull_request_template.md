## Summary

<!-- What does this change do, and why? -->

## Checklist

- [ ] `uv run poe check` passes locally
- [ ] `uv run poe combos` passes, if this touches `template/` or `copier.yml`
- [ ] `uv run poe update` passes, if this edits a file that already exists in
      released projects
- [ ] An ADR is added under `docs/adr/`, if this makes a real architectural call
- [ ] A `_migrations` block is added, if any `template/` path was renamed or
      deleted (see CLAUDE.md's invariant 3)
- [ ] Any conditional file I touched still ends in a real trailing newline
      (invariant 1)
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
