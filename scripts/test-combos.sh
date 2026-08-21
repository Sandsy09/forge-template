#!/usr/bin/env bash
# =============================================================================
# scripts/test-combos.sh
# Scaffolds every meaningful answer combination, asserts the render is clean,
# and runs the same checks CI will run.
#
# Usage:  ./scripts/test-combos.sh [/path/to/template-repo]
# =============================================================================
set -euo pipefail

TEMPLATE_SRC="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
WORK="${TMPDIR:-/tmp}/copier-combos"
SNAPSHOT="$WORK/.template-snapshot"

RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
FAILURES=0

pass() { echo "  ${GREEN}PASS${RESET}  $1"; }
fail() { echo "  ${RED}FAIL${RESET}  $1"; FAILURES=$((FAILURES + 1)); }
info() { echo "${YELLOW}==>${RESET} $1"; }

# -----------------------------------------------------------------------------
# Snapshot the template WITHOUT .git so uncommitted edits are picked up.
# -----------------------------------------------------------------------------
info "Snapshotting template from $TEMPLATE_SRC"
rm -rf "$WORK"
mkdir -p "$SNAPSHOT"
snapshot_template() {
  local src="$1" dst="$2"
  mkdir -p "$dst"
  if command -v rsync > /dev/null 2>&1; then
    rsync -a --exclude='.git' --exclude='.venv' --exclude='__pycache__' "$src"/ "$dst"/
  else
    # Git Bash / minimal environments: copy everything, then prune.
    cp -r "$src"/. "$dst"/
    rm -rf "$dst/.git" "$dst/.venv"
    find "$dst" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  fi
}

snapshot_template "$TEMPLATE_SRC" "$SNAPSHOT"

# -----------------------------------------------------------------------------
# Combination matrix.
# 1-3 are the build_backend x versioning pairs.
# 4 flips every remaining conditional at once, so no branch is untested.
# -----------------------------------------------------------------------------
declare -A COMBOS=(
  [c1-uvbuild-static]="--data build_backend=uv_build"
  [c2-hatch-static]="--data build_backend=hatchling --data versioning=static"
  [c3-hatch-vcs]="--data build_backend=hatchling --data versioning=vcs"
  [c4-kitchen-sink]="--data build_backend=hatchling --data versioning=vcs \
                     --data type_checking=both \
                     --data use_docs=true --data coverage_fail_under=80 \
                     --data changelog_tool=manual --data dependency_updates=dependabot"
)

for name in "${!COMBOS[@]}"; do
  echo
  echo "============================================================"
  echo " $name"
  echo "============================================================"
  out="$WORK/$name"

  # ---- scaffold ------------------------------------------------------------
  info "Scaffolding"
  uvx copier copy "$SNAPSHOT" "$out" --trust --defaults \
    --data project_name="Test ${name}" \
    --data github_org="test-org" \
    --data author_name="Test User" \
    --data author_email="test@example.com" \
    ${COMBOS[$name]} > /dev/null

  cd "$out"

  # ---- assertion 1: no leftover Jinja --------------------------------------
  # Excludes .venv (third-party packages legitimately contain templates).
  leftover=$(grep -rIl --exclude-dir={.venv,.git,dist,node_modules} \
    -E '\{%[^ ]|\{\{ *[a-z_]+ *\}\}|\{%- *(if|for|endif|endfor)' . 2>/dev/null || true)
  if [[ -n "$leftover" ]]; then
    fail "unrendered Jinja found in: $(echo "$leftover" | tr '\n' ' ')"
  else
    pass "no unrendered Jinja"
  fi

  # ---- assertion 2: no .jinja suffixes survived ----------------------------
  if find . -name '*.jinja' -not -path './.venv/*' | grep -q .; then
    fail ".jinja files present in output"
  else
    pass "no .jinja suffixes"
  fi

  # ---- assertion 3: GHA expressions preserved ------------------------------
  if grep -q '\${{' .github/workflows/ci.yml; then
    pass "GHA \${{ }} expressions survived raw blocks"
  else
    fail "GHA expressions were consumed by Jinja"
  fi

  # ---- assertion 4: every YAML file parses ---------------------------------
  if find . -path ./.venv -prune -o \( -name '*.yml' -o -name '*.yaml' \) -print \
     | xargs -r -I{} python -c "import yaml,sys; yaml.safe_load(open('{}'))" 2>/dev/null; then
    pass "all YAML parses"
  else
    fail "YAML parse error"
  fi

  # ---- assertion 5: answers file usable by copier update -------------------
  if [[ ! -f .copier-answers.yml ]]; then
    fail ".copier-answers.yml not generated — template is missing it"
  elif ! grep -q '_src_path' .copier-answers.yml; then
    fail ".copier-answers.yml has no _src_path"
  elif grep -q '_commit' .copier-answers.yml; then
    pass ".copier-answers.yml complete (_commit present)"
  else
    pass ".copier-answers.yml present (_commit absent — expected from snapshot)"
  fi

  # ---- assertion 8: no rendered file is zero bytes -------------------------
  # py.typed and tests/__init__.py are allowed to be empty by design; anything
  # else at 0 bytes means a template file was never filled in.
  zero_byte=$(find . -path './.venv' -prune -o -path './.git' -prune -o \
    -path './dist' -prune -o -type f -empty -print 2>/dev/null \
    | grep -vE '/py\.typed$|/tests/__init__\.py$' || true)
  if [[ -n "$zero_byte" ]]; then
    fail "zero-byte files in rendered output: $(echo "$zero_byte" | tr '\n' ' ')"
  else
    pass "no unexpected zero-byte files"
  fi

  # ---- give hatch-vcs a tag to resolve -------------------------------------
  if grep -q 'hatch-vcs' pyproject.toml; then
    git tag v0.1.0 2>/dev/null || fail "could not tag (is there a commit?)"
  fi

  # ---- CI-equivalent checks ------------------------------------------------
  info "Running CI-equivalent checks"
  uv lock --check          && pass "lockfile current"       || fail "lockfile stale"
  uv run ruff format --check . && pass "format"             || fail "format"
  uv run ruff check .      && pass "lint"                   || fail "lint"
  uv run poe typecheck     && pass "typecheck"              || fail "typecheck"
  uv run pytest -q         && pass "tests"                  || fail "tests"
  uv build > /dev/null     && pass "build"                  || fail "build"

  # ---- assertion 6: version actually resolved ------------------------------
  if grep -q 'hatch-vcs' pyproject.toml; then
    if ls dist/ | grep -qE '(dev0|\+d[0-9]{8})'; then
      fail "version did not resolve from tag: $(ls dist/)"
    else
      pass "version resolved from tag: $(ls dist/ | head -1)"
    fi
  fi

  # ---- assertion 7: wheel contains only the package ------------------------
  wheel=$(ls dist/*.whl | head -1)
  if python -m zipfile -l "$wheel" | grep -qE '^(tests|docs|\.github)/'; then
    fail "wheel contains files it should not"
  else
    pass "wheel contents clean"
  fi

  # ---- docs, when enabled --------------------------------------------------
  if [[ -f mkdocs.yml ]]; then
    uv run mkdocs build --strict > /dev/null \
      && pass "docs build" || fail "docs build"
  fi

  cd - > /dev/null
  
  # Nothing generated by the toolchain should be untracked.
  if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
    fail "untracked files after full run:"
    git status --short --untracked-files=all | head -20
  else
    pass "working tree clean after build"
  fi
done

echo
echo "============================================================"
if [[ $FAILURES -eq 0 ]]; then
  echo "${GREEN}All combos passed locally.${RESET} Outputs in: $WORK"
  echo "Next: push to GitHub to confirm CI is green."
else
  echo "${RED}${FAILURES} failure(s).${RESET} Fix before pushing."
  exit 1
fi
