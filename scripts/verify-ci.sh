#!/usr/bin/env bash
# =============================================================================
# scripts/verify-ci.sh
# Pushes each scaffolded combo to a throwaway private repo and waits for CI.
# Run scripts/test-combos.sh FIRST — this costs Actions minutes.
#
# Requires: gh CLI, authenticated (`gh auth status`)
# Usage:    ./scripts/verify-ci.sh <github-org-or-username>
#           ./scripts/verify-ci.sh <org> --cleanup    # delete the repos after
# =============================================================================
set -euo pipefail

ORG="${1:?Usage: verify-ci.sh <github-org-or-username> [--cleanup]}"
CLEANUP="${2:-}"
WORK="${TMPDIR:-/tmp}/copier-combos"
STAMP=$(date +%Y%m%d%H%M%S)
COMBOS=(c1-uvbuild-static c2-hatch-static c3-hatch-vcs c4-kitchen-sink)
REPOS=()

gh auth status > /dev/null || { echo "Run: gh auth login"; exit 1; }

for name in "${COMBOS[@]}"; do
  [[ -d "$WORK/$name" ]] || { echo "Missing $WORK/$name — run test-combos.sh"; exit 1; }
  repo="copier-ci-test-${name}-${STAMP}"
  echo "==> $repo"
  cd "$WORK/$name"

  # .venv/ and dist/ are gitignored — nothing to clean.
  git remote remove origin 2>/dev/null || true

  gh repo create "$ORG/$repo" --private > /dev/null
  git remote add origin "https://github.com/$ORG/$repo.git"
  git add -A
  if [[ -n "$(git status --porcelain)" ]]; then
    git commit -q -am "chore: test artifacts"
  fi
  git push -q -u origin main

  # Tag AFTER the push so the vcs combos get a resolvable version in CI.
  if grep -q 'hatch-vcs' pyproject.toml; then
    git tag -f v0.1.0 > /dev/null
    git push -q origin v0.1.0 --force
  fi

  REPOS+=("$ORG/$repo")
  cd - > /dev/null
done

echo
echo "==> Waiting for CI (this takes a few minutes)"
FAILED=0
for repo in "${REPOS[@]}"; do
  echo
  echo "--- $repo"
  sleep 5   # let the run register
  run_id=$(gh run list --repo "$repo" --limit 1 --json databaseId --jq '.[0].databaseId')
  if gh run watch "$run_id" --repo "$repo" --exit-status > /dev/null 2>&1; then
    echo "  PASS"
  else
    echo "  FAIL — $(gh run view "$run_id" --repo "$repo" --json url --jq '.url')"
    gh run view "$run_id" --repo "$repo" --log-failed | head -40
    FAILED=$((FAILED + 1))
  fi
done

echo
if [[ $FAILED -eq 0 ]]; then
  echo "All CI runs green."
else
  echo "$FAILED repo(s) failed."
fi

if [[ "$CLEANUP" == "--cleanup" ]]; then
  echo "==> Deleting throwaway repos"
  for repo in "${REPOS[@]}"; do
    gh repo delete "$repo" --yes
  done
else
  echo
  echo "Throwaway repos left in place. Delete with:"
  for repo in "${REPOS[@]}"; do echo "  gh repo delete $repo --yes"; done
fi

exit $FAILED
