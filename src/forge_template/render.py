"""Checks that a *rendered* scaffold is clean.

These used to be `pass`/`fail` lines in `scripts/test-combos.sh`, duplicated a
second time as bash inside `.github/workflows/test-template.yml`. That
duplication already caused a real bug (CI's Jinja regex was broader than the
script's and false-positived on the intentionally-raw git-cliff Tera block).
This module is now the single definition; both `tests/test_combos.py` and CI
call it.

Unlike `schema.py` (which inspects `copier.yml` and `template/` themselves)
and `adr.py` (which inspects `docs/adr/`), everything here inspects an
*already-rendered* project tree -- the output of `copier.run_copy`, or a
built wheel/sdist. Nothing in this module scaffolds anything.
"""

from __future__ import annotations

import re
import subprocess
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from forge_template.github_actions import check_action_pins

if TYPE_CHECKING:
    from collections.abc import Iterable

# Matches Jinja syntax that should have been consumed by rendering: a `{%`
# not followed by a space (Copier's own raw blocks always emit `{% raw %}`
# with a space), a `{{ name }}` variable reference, or a control-flow tag
# using the `{%- ... -%}` whitespace-trim form.
_JINJA_LEFTOVER_RE = re.compile(
    r"\{%[^ ]|\{\{ *[a-z_]+ *\}\}|\{%- *(if|for|endif|endfor)"
)
_VERSION_UNRESOLVED_RE = re.compile(r"(dev0|\+d\d{8})")
_ZERO_BYTE_ALLOWLIST = ("py.typed", "tests/__init__.py")
_WHEEL_BAD_PREFIXES = ("tests/", "docs/", ".github/")
_DEFAULT_EXCLUDE_DIRS = frozenset({".venv", ".git", "dist", "node_modules"})

# A safe `.env.example` line is a comment, blank, or `NAME=` with an empty
# (optionally quoted-empty) right-hand side -- never a real value.
_ENV_EXAMPLE_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=(|\"\"|'')$")


def _is_excluded(path: Path, root: Path, exclude_dirs: Iterable[str]) -> bool:
    rel_parts = path.relative_to(root).parts
    return any(part in exclude_dirs for part in rel_parts)


def _iter_files(
    root: Path, *, exclude_dirs: Iterable[str] = _DEFAULT_EXCLUDE_DIRS
) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and not _is_excluded(path, root, exclude_dirs):
            yield path


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def check_no_unrendered_jinja(root: Path) -> list[str]:
    """No rendered file may contain leftover Jinja syntax."""
    errors = []
    for path in _iter_files(root):
        text = _read_text(path)
        if text is None:
            continue
        match = _JINJA_LEFTOVER_RE.search(text)
        if match:
            rel = path.relative_to(root)
            errors.append(f"{rel}: unrendered Jinja found: {match.group(0)!r}")
    return errors


def check_no_jinja_suffixes(root: Path) -> list[str]:
    """No `*.jinja` file should survive rendering."""
    errors = []
    for path in root.rglob("*.jinja"):
        if path.is_file() and not _is_excluded(path, root, {".venv"}):
            errors.append(f"{path.relative_to(root)}: .jinja suffix present in output")
    return errors


def check_gha_expressions(root: Path) -> list[str]:
    """`${{ }}` GitHub Actions expressions must survive the `{% raw %}` block
    (CLAUDE.md invariant 4) rather than being consumed by Jinja.
    """  # noqa: D205
    ci_workflow = root / ".github" / "workflows" / "ci.yml"
    if not ci_workflow.is_file():
        return [f"{ci_workflow}: missing -- cannot verify GHA expressions survived"]
    text = _read_text(ci_workflow) or ""
    if "${{" not in text:
        return [
            f"{ci_workflow}: no \\${{{{ }}}} expressions found -- Jinja consumed them"
        ]
    return []


def check_yaml_parses(root: Path) -> list[str]:
    """Every rendered `.yml`/`.yaml` file must be valid YAML."""
    errors = []
    for path in _iter_files(root):
        if path.suffix not in {".yml", ".yaml"}:
            continue
        text = _read_text(path)
        if text is None:
            continue
        try:
            yaml.safe_load(text)
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(root)}: YAML parse error: {exc}")
    return errors


def check_answers_file(root: Path, *, require_commit: bool = False) -> list[str]:
    """`.copier-answers.yml` must exist and be usable by `copier update`.

    `_commit` is only required when scaffolded from real git history --
    a non-git snapshot render legitimately has no commit to record.
    """
    answers = root / ".copier-answers.yml"
    if not answers.is_file():
        return [f"{answers}: .copier-answers.yml not generated"]
    text = _read_text(answers) or ""
    errors = []
    if "_src_path" not in text:
        errors.append(f"{answers}: missing _src_path")
    if require_commit and "_commit" not in text:
        errors.append(f"{answers}: missing _commit (expected when scaffolded from git)")
    return errors


def check_no_zero_byte_files(root: Path) -> list[str]:
    """No rendered file should be zero bytes, except the deliberate
    allowlist (`py.typed`, `tests/__init__.py`).
    """  # noqa: D205
    errors = []
    for path in _iter_files(root):
        if path.stat().st_size != 0:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.endswith(_ZERO_BYTE_ALLOWLIST):
            continue
        errors.append(f"{rel}: unexpected zero-byte file")
    return errors


def check_secret_safeguards(root: Path) -> list[str]:
    """`.env.example` must carry placeholders only, and `.gitignore` must
    ignore `.env` without shadowing the tracked example.
    """  # noqa: D205
    errors = []

    example = root / ".env.example"
    if not example.is_file():
        errors.append(f"{example}: .env.example not generated")
    else:
        text = _read_text(example) or ""
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not _ENV_EXAMPLE_ASSIGNMENT_RE.match(stripped):
                errors.append(
                    f".env.example:{lineno}: not a safe placeholder line: {stripped!r}"
                )

    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        errors.append(f"{gitignore}: .gitignore not generated")
    else:
        lines = {line.strip() for line in (_read_text(gitignore) or "").splitlines()}
        if ".env" not in lines:
            errors.append(".gitignore: missing '.env' ignore rule")
        if "!.env.example" not in lines:
            errors.append(
                ".gitignore: missing '!.env.example' negation -- a broader "
                "'.env.*' rule would silently untrack the tracked example"
            )

    return errors


def check_env_example_tracked(root: Path) -> list[str]:
    """`.env.example` must be git-tracked and not excluded by `.gitignore`,
    while `.env` itself must be ignored.

    Exercises the real git ignore-matching engine rather than
    re-implementing it, catching the specific hazard where a broad `.env.*`
    rule shadows the tracked example despite `check_secret_safeguards`
    finding the expected `!.env.example` negation line present in isolation.
    """  # noqa: D205
    if not (root / ".env.example").is_file():
        return []  # check_secret_safeguards already reports the missing file
    errors = []
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env.example"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if tracked.returncode != 0:
        errors.append(".env.example: not tracked by git (shadowed by an ignore rule?)")

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".env"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if ignored.returncode != 0:
        errors.append(".env: not ignored by .gitignore")

    return errors


def check_wheel_contents(wheel: Path) -> list[str]:
    """The built wheel must contain only the package -- no tests/docs/CI."""
    errors = []
    with zipfile.ZipFile(wheel) as zf:
        for name in zf.namelist():
            if name.startswith(_WHEEL_BAD_PREFIXES):
                errors.append(f"{wheel.name}: contains {name}, which should not ship")
    return errors


def check_version_resolved(dist_dir: Path) -> list[str]:
    """Built artifact filenames must not carry an unresolved hatch-vcs
    fallback version (`dev0` / `+dYYYYMMDD`).
    """  # noqa: D205
    errors = []
    for path in dist_dir.iterdir():
        if _VERSION_UNRESOLVED_RE.search(path.name):
            errors.append(f"{path.name}: version did not resolve from tag")
    return errors


def check_tree_clean(root: Path) -> list[str]:
    """Nothing generated by the toolchain (`uv sync`, `uv build`, tasks)
    should be untracked or modified in the *rendered project's own* git tree.

    Ported from `scripts/test-combos.sh`, which ran this check after `cd -`
    back to the *template* repo rather than the scaffolded project -- so it
    was reporting the operator's own uncommitted work, not anything about the
    render. See CLAUDE.md's documented false-positive. This checks `root`.
    """  # noqa: D205
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if lines:
        shown = ", ".join(lines[:20])
        return [f"{root}: untracked/modified files after full run: {shown}"]
    return []


def check_all(root: Path, *, require_commit: bool = False) -> list[str]:
    """Run the render checks that apply to every scaffold, regardless of
    combo or build state. Build-artifact checks (`check_wheel_contents`,
    `check_version_resolved`) and `check_tree_clean` are run separately since
    they depend on a build having happened / a clean git tree already existing.
    """  # noqa: D205
    return [
        *check_no_unrendered_jinja(root),
        *check_no_jinja_suffixes(root),
        *check_gha_expressions(root),
        *check_yaml_parses(root),
        *check_action_pins(root / ".github" / "workflows"),
        *check_answers_file(root, require_commit=require_commit),
        *check_no_zero_byte_files(root),
        *check_secret_safeguards(root),
    ]
