# CI runner baseline

This is the living contract for which GitHub-hosted runner images
`forge-template`'s own workflows run on, how the next Ubuntu image is trialled,
and when it is promoted. [ADR
0074](adr/0074-pin-the-ubuntu-runner-baseline-with-a-canary.md) records the
decision. `check_runner_labels` in `src/forge_template/github_actions.py`
(run by `uv run poe check` through `schema.check_all()`) and
`tests/test_runner_baseline.py` enforce the parts a CI edit could silently
break. The sibling `create-forge` repository made the same decision
independently for its own workflows.

## Why it matters

`ubuntu-latest` is an alias GitHub repoints on its own schedule. Left in place,
the effective Linux baseline changes without a reviewed commit, and the first
sign is a red protected check. The
[17 September 2026 announcement](https://github.blog/changelog/2026-09-17-ubuntu-26-generally-available-and-latest-migration/)
([runner-images #14747](https://github.com/actions/runner-images/issues/14747),
[#14748](https://github.com/actions/runner-images/issues/14748)) says
`ubuntu-latest` moves from Ubuntu 24.04 to **26.04**, rolling out gradually
between **19 October and 19 November 2026**, and that the move may break
workflows relying on software that differs between the images. The
review-reported 19 October date is the start of that window, not a single
cut-over day. GitHub does not state an end-of-support date for 24.04.

## Current labels

The `Baseline` and `Canary` rows are read by `tests/test_runner_baseline.py`,
which fails if the workflows disagree with them.

| Role | Label | Runs |
| --- | --- | --- |
| Baseline | `ubuntu-24.04` | every protected Ubuntu job: the `linux` call and the `all-green` aggregate in `test-template.yml`, and both jobs in `release.yml` |
| Canary | `ubuntu-26.04` | the identical Linux checks, in `runner-canary.yml`, non-blocking |
| Unpinned | `windows-latest` | the `windows` smoke job in `test-template.yml`; a known gap, see below |

Pinning is per image, so it still receives GitHub's routine image updates (a
new `20260920.314.1`-style version of the same OS). What it removes is the
*OS* moving under a merge.

## How the pieces fit

- `linux-checks.yml` is a reusable workflow (`workflow_call`, one required
  `runner` input) holding the eight Linux jobs: lint with the fast suite, the
  four direct-Copier combinations, archetype builds, both composition sweeps,
  `copier update` compatibility, wheel contents and the released-client check.
  It has read-only permissions and the same SHA pins as every other workflow.
- `test-template.yml` calls it once with the baseline label. The required
  aggregate `All checks passed` needs that call and the Windows job.
- `runner-canary.yml` calls it once with the canary label, on the same
  triggers (push to `main`, pull requests, the Monday cron, manual dispatch).
  It has no aggregate job and nothing depends on it, so it cannot block a
  merge and cannot produce the required check's name.

Because both callers share one definition, the canary cannot drift from the
protected checks: what is proven on 26.04 is exactly what is required on
24.04.

`release.yml` holds release-capable scopes (`contents: write`, `id-token:
write`), so it is pinned to the baseline and deliberately not canaried. The
checks that protect a release are the ones the canary runs.

## Generated-project boundary

This contract governs this repository's workflows only. The workflow the
`github` platform and the direct-Copier template *generate* still name
`runs-on: ubuntu-latest` (`tests/test_github_platform.py`,
`tests/test_pyright_capability.py`), and `check_runner_labels` is not applied
to `template/`. Changing what a user's project runs on is a compatibility
decision for that project, not a repository housekeeping change, and needs
its own decision under [the compatibility
policy](compatibility-policy.md).

The canary still gives advance evidence about that decision. Its `scaffold`,
`archetype` and `update-compat` jobs render real projects, resolve and build
native scientific dependencies, run each generated project's own checks and
exercise Git initialisation and `copier update` on 26.04.

## Ownership

The repository maintainer owns the canary. A red canary is triaged within one
week of the first failing run, by one of:

1. fixing the code or test so it works on both images;
2. filing an `area:ci` issue that names the failing job and the image
   difference, when the fix is larger than the change that surfaced it.

An open canary-attributed issue blocks promotion.

## Promotion

The baseline moves to the canary's image when **all** of these hold:

- the canary is green on `main` HEAD;
- the canary is green on each of the four most recent Monday scheduled runs;
- no canary-attributed issue is open;
- the counted runs include the `scaffold`, `archetype`, `update-compat` and
  `wheel` jobs, not merely lint.

Promotion is one pull request that changes the label everywhere it is named:
the `linux` call and `all-green` in `test-template.yml`, both jobs in
`release.yml`, and the `Baseline` row above. The canary is then pointed at
the next candidate image, or kept on the old baseline as a rollback lane. A
promotion needs no new ADR while it follows these criteria; changing the
criteria, or dropping the canary, does.

If GitHub announces a deprecation or brownout schedule for the baseline
image, promotion moves ahead of it regardless of the four-run window. Tracked
in [#206](https://github.com/Sandsy09/forge-template/issues/206).

## Rollback

Every label is explicit, so rolling back is reverting the promotion pull
request. Nothing else moves: the canary lane is the previous baseline until
it is retired.

## Known gap: `windows-latest`

The Windows smoke job still uses the moving alias (today the image reports
`windows-2025-vs2026`). The decision was scoped to Ubuntu, and a tracked
follow-up pins it: [#207](https://github.com/Sandsy09/forge-template/issues/207).
`check_runner_labels` rejects `ubuntu-latest` only. Whoever pins Windows
extends that check and this document in the same change.

## Evidence

Recorded for FT-24.01 ([#191](https://github.com/Sandsy09/forge-template/issues/191)).

### Inventory before the change

Image observed in `main` run 35741510636 (22 September 2026, `be1ee24`) and,
for `release.yml`, in the `0.6.0` release run 35539758128 (20 September
2026). Everything below was `ubuntu-latest` or `windows-latest` before this
change.

| Workflow | Jobs | Label | Resolved image |
| --- | --- | --- | --- |
| `test-template.yml` | `lint`, `scaffold` ×4, `archetype`, `sweep-composition`, `sweep-independence`, `update-compat`, `wheel`, `released-client`, `all-green` | `ubuntu-latest` | `ubuntu-24.04`, version `20260907.300.1`–`20260920.314.1` |
| `test-template.yml` | `windows` | `windows-latest` | `windows-2025-vs2026` |
| `release.yml` | `release`, `publish` | `ubuntu-latest` | `ubuntu-24.04`, version `20260907.300.1` |

The repository has no reusable workflows and no third-party runner labels.
The only required status check is `All checks passed`.

### Validation of this change

Filled in from the pull request's real runs before merge.
