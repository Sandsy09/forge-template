#!/usr/bin/env bash
# =============================================================================
# scripts/test-update.sh
# Validates `copier update`: local edits survive, template changes arrive,
# conflicts surface rather than silently clobbering.
#
# Usage: ./scripts/test-update.sh [/path/to/template-repo]
# =============================================================================
set -euo pipefail

TEMPLATE="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
WORK="${TMPDIR:-/tmp}/copier-update-test"
PROJ="$WORK/project"
TMPL="$WORK/template"

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
FAILURES=0
pass() { echo "  ${GREEN}PASS${RESET}  $1"; }
fail() { echo "  ${RED}FAIL${RESET}  $1"; FAILURES=$((FAILURES + 1)); }
info() { echo; echo "${YELLOW}==>${RESET} $1"; }

rm -rf "$WORK"; mkdir -p "$WORK"

# -----------------------------------------------------------------------------
# Work against a CLONE of the template. Update needs real git history and tags,
# so the snapshot trick used by test-combos.sh does not apply here.
# -----------------------------------------------------------------------------
info "Cloning template"
git clone -q "$TEMPLATE" "$TMPL"
cd "$TMPL"
git tag -l 'v*' | grep -q . || { echo "Template has no tags. Run: git tag v0.1.0"; exit 1; }
BASE_TAG=$(git tag -l 'v*' --sort=-v:refname | head -1)
echo "  base version: $BASE_TAG"

# -----------------------------------------------------------------------------
# 1. Scaffold from the released version
# -----------------------------------------------------------------------------
info "Scaffolding from $BASE_TAG"
uvx copier copy "$TMPL" "$PROJ" --trust --defaults --vcs-ref="$BASE_TAG" \
  --data project_name="Update Test" \
  --data github_org="test-org" \
  --data build_backend=hatchling \
  --data versioning=static \
  > /dev/null

cd "$PROJ"
grep -q "_commit: $BASE_TAG" .copier-answers.yml \
  && pass "answers file records $BASE_TAG" \
  || fail "answers file missing or wrong _commit"

# -----------------------------------------------------------------------------
# 2. Local changes a real user would make
# -----------------------------------------------------------------------------
info "Making local edits"

# (a) edit a templated file - the hard case
python - <<'PY'
import re, pathlib
p = pathlib.Path("pyproject.toml")
t = p.read_text()
t = t.replace("dependencies = []", 'dependencies = ["httpx>=0.28"]')
p.write_text(t)
PY

# (b) add a file the template knows nothing about
mkdir -p src/update_test
cat > src/update_test/client.py <<'PY'
"""Local module the template has never seen."""


def fetch() -> str:
    """Return a greeting."""
    return "local"
PY

# (c) edit a templated doc
python - <<'PY'
import pathlib
p = pathlib.Path("README.md")
t = p.read_text()
marker = "## Development"
t = t.replace(marker, "## Local section\n\nAdded by the project team, not the template.\n\n" + marker, 1)
p.write_text(t)
PY

# echo "" >> README.md
# echo "## Local section" >> README.md
# echo "Added by the project team, not the template." >> README.md

git add -A
git commit -q -m "feat: local customisations" --no-verify

# -----------------------------------------------------------------------------
# 3. Change the template and release a new version
# -----------------------------------------------------------------------------
info "Changing the template"
cd "$TMPL"

# (a) new file every project should receive
cat > template/CODE_OF_CONDUCT.md.jinja <<'EOF'
# Code of Conduct

Contact {{ author_email or 'the maintainers' }} to report an issue.
EOF

# (b) change an existing templated file - same file the project edited
python - <<'PY'
import pathlib
p = pathlib.Path("template/pyproject.toml.jinja")
t = p.read_text()
t = t.replace('"RUF",       # ruff-specific', '"RUF",       # ruff-specific\n    "TID",       # flake8-tidy-imports')
p.write_text(t)
PY

# (c) change a file the project also edited - should conflict
printf '\n## Support\n\nRaise an issue on the repository.\n' >> template/README.md.jinja

git add -A
git commit -q -m "feat: add code of conduct, TID lint rules, support section"
NEW_TAG="v0.2.0"
git tag "$NEW_TAG"
echo "  released $NEW_TAG"

# -----------------------------------------------------------------------------
# 4. Update
# -----------------------------------------------------------------------------
info "Running copier update"
cd "$PROJ"

[[ -z "$(git status --porcelain)" ]] \
  && pass "working tree clean (update would refuse otherwise)" \
  || fail "working tree dirty"

uvx copier update --trust --defaults --conflict=inline || true

# -----------------------------------------------------------------------------
# 5. Assertions
# -----------------------------------------------------------------------------
info "Checking the merge"

grep -q "_commit: $NEW_TAG" .copier-answers.yml \
  && pass "answers file advanced to $NEW_TAG" \
  || fail "answers file still on old version"

test -f CODE_OF_CONDUCT.md \
  && pass "new template file arrived" \
  || fail "new template file missing"

grep -q '"TID"' pyproject.toml \
  && pass "template change to pyproject.toml applied" \
  || fail "template change to pyproject.toml lost"

grep -q 'httpx' pyproject.toml \
  && pass "LOCAL edit to pyproject.toml preserved" \
  || fail "LOCAL edit to pyproject.toml CLOBBERED"

test -f src/update_test/client.py \
  && pass "untemplated local file untouched" \
  || fail "untemplated local file removed"

grep -q 'Local section' README.md \
  && pass "local README section preserved" \
  || fail "local README section lost"

if grep -q '^<<<<<<<' README.md; then
  echo "  ${YELLOW}NOTE${RESET}  README.md has conflict markers — expected, both sides changed it"
  CONFLICTED=1
else
  grep -q 'Support' README.md \
    && pass "README merged cleanly, both changes present" \
    || fail "template README change lost"
  CONFLICTED=0
fi

# -----------------------------------------------------------------------------
# 6. Project still works (after resolving any conflict)
# -----------------------------------------------------------------------------
if [[ "${CONFLICTED:-0}" -eq 1 ]]; then
  info "Resolving conflict markers to verify the project still builds"
  python - <<'PY'
import pathlib
for p in pathlib.Path(".").rglob("*"):
    if p.is_file() and p.suffix in {".md", ".toml", ".yml", ".yaml", ".py"}:
        try:
            lines = p.read_text().splitlines(keepends=True)
        except UnicodeDecodeError:
            continue
        if not any(l.startswith("<<<<<<<") for l in lines):
            continue
        out, skip = [], False
        for l in lines:
            if l.startswith("<<<<<<<"): continue
            if l.startswith("======="): skip = True; continue
            if l.startswith(">>>>>>>"): skip = False; continue
            if not skip: out.append(l)
        p.write_text("".join(out))
        print(f"resolved {p}")
PY
fi

info "Verifying the updated project"
uv sync --all-groups > /dev/null 2>&1 && pass "sync" || fail "sync"
uv run poe check > /dev/null 2>&1 && pass "checks pass after update" || fail "checks FAIL after update"

echo
if [[ $FAILURES -eq 0 ]]; then
  echo "${GREEN}copier update validated.${RESET} Project at: $PROJ"
else
  echo "${RED}${FAILURES} failure(s).${RESET} Inspect: $PROJ"
  exit 1
fi
