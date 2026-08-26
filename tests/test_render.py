"""Tests for forge_template.render -- each check gets a tmp_path negative
test proving it can fail, per the standing rule that a check which cannot
fail is not a check.
"""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

from forge_template.render import (
    check_all,
    check_answers_file,
    check_env_example_tracked,
    check_gha_expressions,
    check_no_jinja_suffixes,
    check_no_unrendered_jinja,
    check_no_zero_byte_files,
    check_secret_safeguards,
    check_tree_clean,
    check_version_resolved,
    check_wheel_contents,
    check_yaml_parses,
)


def _ci_workflow(root: Path, content: str) -> None:
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(content)


# -----------------------------------------------------------------------------
# check_no_unrendered_jinja
# -----------------------------------------------------------------------------


def test_check_no_unrendered_jinja_passes_on_clean_tree(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Hello, world.\n")
    assert check_no_unrendered_jinja(tmp_path) == []


def test_check_no_unrendered_jinja_flags_leftover_variable(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Hello, {{ project_name }}.\n")
    errors = check_no_unrendered_jinja(tmp_path)
    assert len(errors) == 1
    assert "README.md" in errors[0]


def test_check_no_unrendered_jinja_ignores_venv(tmp_path: Path) -> None:
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "pkg.py").write_text("{{ not_ours }}\n")
    assert check_no_unrendered_jinja(tmp_path) == []


# -----------------------------------------------------------------------------
# check_no_jinja_suffixes
# -----------------------------------------------------------------------------


def test_check_no_jinja_suffixes_passes_when_none_present(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    assert check_no_jinja_suffixes(tmp_path) == []


def test_check_no_jinja_suffixes_flags_survivor(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml.jinja").write_text("[project]\n")
    errors = check_no_jinja_suffixes(tmp_path)
    assert len(errors) == 1
    assert "pyproject.toml.jinja" in errors[0]


# -----------------------------------------------------------------------------
# check_gha_expressions
# -----------------------------------------------------------------------------


def test_check_gha_expressions_passes_when_preserved(tmp_path: Path) -> None:
    _ci_workflow(tmp_path, "run: echo ${{ github.workflow }}\n")
    assert check_gha_expressions(tmp_path) == []


def test_check_gha_expressions_flags_consumed_expression(tmp_path: Path) -> None:
    _ci_workflow(tmp_path, "run: echo nothing-to-see-here\n")
    errors = check_gha_expressions(tmp_path)
    assert len(errors) == 1
    assert "consumed" in errors[0]


def test_check_gha_expressions_flags_missing_workflow(tmp_path: Path) -> None:
    errors = check_gha_expressions(tmp_path)
    assert len(errors) == 1
    assert "missing" in errors[0]


# -----------------------------------------------------------------------------
# check_yaml_parses
# -----------------------------------------------------------------------------


def test_check_yaml_parses_passes_on_valid_yaml(tmp_path: Path) -> None:
    (tmp_path / "config.yml").write_text("key: value\n")
    assert check_yaml_parses(tmp_path) == []


def test_check_yaml_parses_flags_broken_yaml(tmp_path: Path) -> None:
    (tmp_path / "config.yml").write_text("key: [unterminated\n")
    errors = check_yaml_parses(tmp_path)
    assert len(errors) == 1
    assert "config.yml" in errors[0]


# -----------------------------------------------------------------------------
# check_answers_file
# -----------------------------------------------------------------------------


def test_check_answers_file_passes_with_src_path(tmp_path: Path) -> None:
    (tmp_path / ".copier-answers.yml").write_text("_src_path: /template\n")
    assert check_answers_file(tmp_path) == []


def test_check_answers_file_flags_missing_file(tmp_path: Path) -> None:
    errors = check_answers_file(tmp_path)
    assert len(errors) == 1
    assert "not generated" in errors[0]


def test_check_answers_file_flags_missing_src_path(tmp_path: Path) -> None:
    (tmp_path / ".copier-answers.yml").write_text("_commit: v1.0.0\n")
    errors = check_answers_file(tmp_path)
    assert any("_src_path" in e for e in errors)


def test_check_answers_file_requires_commit_when_asked(tmp_path: Path) -> None:
    (tmp_path / ".copier-answers.yml").write_text("_src_path: /template\n")
    errors = check_answers_file(tmp_path, require_commit=True)
    assert any("_commit" in e for e in errors)


def test_check_answers_file_allows_missing_commit_from_snapshot(tmp_path: Path) -> None:
    (tmp_path / ".copier-answers.yml").write_text("_src_path: /template\n")
    assert check_answers_file(tmp_path, require_commit=False) == []


# -----------------------------------------------------------------------------
# check_no_zero_byte_files
# -----------------------------------------------------------------------------


def test_check_no_zero_byte_files_passes_when_none(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("content\n")
    assert check_no_zero_byte_files(tmp_path) == []


def test_check_no_zero_byte_files_flags_empty_file(tmp_path: Path) -> None:
    (tmp_path / "empty.py").write_text("")
    errors = check_no_zero_byte_files(tmp_path)
    assert len(errors) == 1
    assert "empty.py" in errors[0]


def test_check_no_zero_byte_files_allows_py_typed(tmp_path: Path) -> None:
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "py.typed").write_text("")
    assert check_no_zero_byte_files(tmp_path) == []


def test_check_no_zero_byte_files_allows_tests_init(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    assert check_no_zero_byte_files(tmp_path) == []


# -----------------------------------------------------------------------------
# check_secret_safeguards
# -----------------------------------------------------------------------------


def _safe_scaffold(root: Path) -> None:
    (root / ".env.example").write_text("# comment\n\nEXAMPLE_API_KEY=\n")
    (root / ".gitignore").write_text(".env\n.env.*\n!.env.example\n")


def test_check_secret_safeguards_passes_on_safe_scaffold(tmp_path: Path) -> None:
    _safe_scaffold(tmp_path)
    assert check_secret_safeguards(tmp_path) == []


def test_check_secret_safeguards_flags_missing_env_example(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".env\n!.env.example\n")
    errors = check_secret_safeguards(tmp_path)
    assert any(".env.example not generated" in e for e in errors)


def test_check_secret_safeguards_flags_real_value(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("EXAMPLE_API_KEY=sk-live-abc123\n")
    (tmp_path / ".gitignore").write_text(".env\n!.env.example\n")
    errors = check_secret_safeguards(tmp_path)
    assert any("not a safe placeholder line" in e for e in errors)


def test_check_secret_safeguards_flags_missing_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("EXAMPLE_API_KEY=\n")
    errors = check_secret_safeguards(tmp_path)
    assert any(".gitignore not generated" in e for e in errors)


def test_check_secret_safeguards_flags_missing_env_rule(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("EXAMPLE_API_KEY=\n")
    (tmp_path / ".gitignore").write_text("!.env.example\n")
    errors = check_secret_safeguards(tmp_path)
    assert any("missing '.env' ignore rule" in e for e in errors)


def test_check_secret_safeguards_flags_missing_negation(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("EXAMPLE_API_KEY=\n")
    (tmp_path / ".gitignore").write_text(".env\n.env.*\n")
    errors = check_secret_safeguards(tmp_path)
    assert any("!.env.example" in e for e in errors)


# -----------------------------------------------------------------------------
# check_env_example_tracked
# -----------------------------------------------------------------------------


def test_check_env_example_tracked_passes_when_tracked_and_env_ignored(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    _safe_scaffold(tmp_path)
    (tmp_path / ".env").write_text("EXAMPLE_API_KEY=real-value\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    assert check_env_example_tracked(tmp_path) == []


def test_check_env_example_tracked_flags_shadowed_example(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    # No `!.env.example` negation -- `.env.*` shadows the tracked example, so
    # `git add -A` (as `_tasks` runs) silently never tracks it.
    (tmp_path / ".gitignore").write_text(".env\n.env.*\n")
    (tmp_path / ".env.example").write_text("EXAMPLE_API_KEY=\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    errors = check_env_example_tracked(tmp_path)
    assert any("not tracked by git" in e for e in errors)


def test_check_env_example_tracked_flags_unignored_env(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / ".gitignore").write_text("!.env.example\n")
    (tmp_path / ".env.example").write_text("EXAMPLE_API_KEY=\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    errors = check_env_example_tracked(tmp_path)
    assert any(".env: not ignored" in e for e in errors)


def test_check_env_example_tracked_skips_when_no_example(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    assert check_env_example_tracked(tmp_path) == []


# -----------------------------------------------------------------------------
# check_wheel_contents
# -----------------------------------------------------------------------------


def test_check_wheel_contents_passes_on_clean_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "pkg-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("pkg/__init__.py", "")
    assert check_wheel_contents(wheel) == []


def test_check_wheel_contents_flags_leaked_tests(tmp_path: Path) -> None:
    wheel = tmp_path / "pkg-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("pkg/__init__.py", "")
        zf.writestr("tests/test_pkg.py", "")
    errors = check_wheel_contents(wheel)
    assert len(errors) == 1
    assert "tests/test_pkg.py" in errors[0]


# -----------------------------------------------------------------------------
# check_version_resolved
# -----------------------------------------------------------------------------


def test_check_version_resolved_passes_on_tagged_version(tmp_path: Path) -> None:
    (tmp_path / "pkg-0.1.0-py3-none-any.whl").write_bytes(b"")
    assert check_version_resolved(tmp_path) == []


def test_check_version_resolved_flags_dev0_fallback(tmp_path: Path) -> None:
    (tmp_path / "pkg-0.1.dev0-py3-none-any.whl").write_bytes(b"")
    errors = check_version_resolved(tmp_path)
    assert len(errors) == 1
    assert "dev0" in errors[0] or "did not resolve" in errors[0]


def test_check_version_resolved_flags_dirty_date_fallback(tmp_path: Path) -> None:
    (tmp_path / "pkg-0.1.0+d20260101-py3-none-any.whl").write_bytes(b"")
    errors = check_version_resolved(tmp_path)
    assert len(errors) == 1


# -----------------------------------------------------------------------------
# check_tree_clean
# -----------------------------------------------------------------------------


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)


def test_check_tree_clean_passes_on_committed_tree(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("content\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    assert check_tree_clean(tmp_path) == []


def test_check_tree_clean_flags_untracked_file(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("content\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    (tmp_path / "leftover.txt").write_text("oops\n")
    errors = check_tree_clean(tmp_path)
    assert len(errors) == 1
    assert "leftover.txt" in errors[0]


# -----------------------------------------------------------------------------
# check_all
# -----------------------------------------------------------------------------


def test_check_all_passes_on_a_fully_clean_render(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Hello.\n")
    (tmp_path / ".copier-answers.yml").write_text("_src_path: /template\n")
    _ci_workflow(tmp_path, "run: echo ${{ github.workflow }}\n")
    _safe_scaffold(tmp_path)
    assert check_all(tmp_path) == []


def test_check_all_aggregates_multiple_failures(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Hello, {{ leftover }}.\n")
    # No .copier-answers.yml, no .github/workflows/ci.yml either.
    errors = check_all(tmp_path)
    assert len(errors) >= 3
