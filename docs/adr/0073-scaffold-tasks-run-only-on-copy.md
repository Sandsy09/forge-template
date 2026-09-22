# 73. Scaffold tasks run only on copy

Date: 2026-09-22

## Status

Accepted

## Context

[forge-template#204](https://github.com/Sandsy09/forge-template/issues/204):
`copier update` on a generated project fails whenever the update produces no
change. Copier re-runs `_tasks` on every operation, `copy` and `update`
alike, and `copier.yml`'s scaffold commit
(`git commit --no-verify -m "feat: initial scaffold from template"`) has no
guard. On `update` against an already-initialised repository whose
regenerated tree is identical to what is committed, `git commit` exits 1
with "nothing to commit, working tree clean", and Copier surfaces this as a
generic `Task '...' returned non-zero exit status 1`. Observed against a real
`create-forge[legacy]` project (`create-forge`'s
`docs/release-0-5-0-validation.md`), on `create-forge 0.4.0` and `0.5.0`
alike, so the cause is this template, not that CLI or that release.

`_tasks` has no first-class "copy only" flag, but each task accepts a Jinja
`when` condition, and Copier injects `_copier_operation` (`"copy"` on `new`,
`"update"` on `update`) into every task's render context. Both existed before
this repository's declared floor: `when`/`condition` support since early
Copier (present already at 9.4.0, the current floor); `_copier_operation`
landed in Copier 9.6.0 (`Add _copier_operation variable`, copier#1733) — two
minor versions past this repository's declared `copier>=9.4,<10`.

## Decision

1. **Guard the git-bootstrap, both commits, and hook installation with
   `when: "{{ _copier_operation == 'copy' }}"`.** `git init`, `git add -A`,
   the scaffold commit, the lockfile commit, and
   `uv run pre-commit install --install-hooks` all become copy-only. An
   update is Copier's own three-way merge; the resulting changes (and any
   `uv.lock` drift) are left for the user to review and commit themselves,
   the same as any other file an update touches. *Rejected:* adding
   `--allow-empty` to the scaffold commit, matching the lockfile task's
   existing flag. It keeps `update` re-running `git init` ("Reinitialized
   existing Git repository") and the commit unconditionally, landing a
   commit titled "feat: initial scaffold from template" on top of the user's
   own history on every idle update — it hides the symptom without
   addressing that these are copy-time-only operations.
2. **Hook installation is copy-only too, not for symmetry but because it
   must be.** `copier update`'s own implementation renders old and new
   template states into ephemeral temporary directories and runs `_tasks`
   there as part of computing its diff, expecting this template's own
   `git init` task to make each one a git repository — Copier only
   `git init`s them itself *after* `_tasks` finishes. Discovered while
   verifying this record's own fix: with the git tasks made copy-only,
   `uv run pre-commit install --install-hooks` (left unconditional in the
   first draft) failed inside those temp directories with "git failed. Is
   it installed, and are you in a Git repository directory?", because
   installing a hook script needs `.git` to exist. This is also the right
   behaviour independent of that constraint: the stub scripts `pre-commit
   install` plants read `.pre-commit-config.yaml` fresh at each real commit,
   so a hook revision an update brings in takes effect without reinstalling
   anything.
3. **`uv sync --all-groups` stays unconditional.** It needs no git
   repository and is worth repeating: an update that moves a dependency
   floor should still leave the project's environment correct.
4. **Raise the declared Copier floor to `copier>=9.6,<10`.** Below 9.6,
   `_copier_operation` is never injected into the task context at all, and
   this repository does not enable strict Jinja undefined rendering, so
   `{{ _copier_operation == 'copy' }}` renders as the literal string
   `"False"` (verified directly against Jinja's default `Undefined`) —
   `cast_to_bool` reads that as false unconditionally, and every guarded
   task, `git init` included, would silently never run, on `copy` as well
   as `update`. That is a worse failure than the one this record fixes, not
   a milder one, so the floor bump is not optional cleanup.

## Consequences

- `copier update` on a project that needs no change now succeeds; the
  generated project's own git history is untouched by an idle update instead
  of gaining (or failing to gain) a stray scaffold commit.
- `tests/test_update.py::test_update_with_nothing_to_apply_succeeds` is the
  first test covering an update with nothing to apply; confirmed to fail
  against the pre-fix `_tasks` before this change.
- The `copier` floor moves from 9.4 to 9.6. No other declared range,
  protocol, or CLI surface changes; `create-forge`'s own `legacy` extra
  already declares `copier>=9.16,<10`, well above this floor.
- Nothing here publishes. The fix reaches `--legacy` users on whatever
  template version is tagged next; no tag is cut by this record.
