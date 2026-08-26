"""Tests for immutable GitHub Actions workflow references."""

from __future__ import annotations

from pathlib import Path

from forge_template.github_actions import check_action_pins
from forge_template.schema import REPO_ROOT


def _workflow(tmp_path: Path, uses: str) -> Path:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        f"jobs:\n  test:\n    steps:\n      - uses: {uses}\n",
        encoding="utf-8",
    )
    return workflows


def test_real_source_workflows_are_immutably_pinned() -> None:
    errors = [
        *check_action_pins(REPO_ROOT / ".github" / "workflows"),
        *check_action_pins(REPO_ROOT / "template" / ".github" / "workflows"),
    ]
    assert errors == []


def test_full_sha_with_exact_release_comment_passes(tmp_path: Path) -> None:
    workflows = _workflow(
        tmp_path,
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0",
    )
    assert check_action_pins(workflows) == []


def test_local_action_passes_without_release_comment(tmp_path: Path) -> None:
    workflows = _workflow(tmp_path, "./.github/actions/setup")
    assert check_action_pins(workflows) == []


def test_moving_tag_is_rejected(tmp_path: Path) -> None:
    errors = check_action_pins(_workflow(tmp_path, "actions/checkout@v4"))
    assert len(errors) == 2
    assert "full 40-character" in errors[0]
    assert "exact release comment" in errors[1]


def test_short_sha_is_rejected(tmp_path: Path) -> None:
    errors = check_action_pins(_workflow(tmp_path, "actions/checkout@11d5960 # v4.4.0"))
    assert len(errors) == 1
    assert "full 40-character" in errors[0]


def test_missing_release_comment_is_rejected(tmp_path: Path) -> None:
    errors = check_action_pins(
        _workflow(
            tmp_path,
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        )
    )
    assert len(errors) == 1
    assert "exact release comment" in errors[0]


def test_docker_action_is_rejected(tmp_path: Path) -> None:
    errors = check_action_pins(_workflow(tmp_path, "docker://alpine:3.22"))
    assert len(errors) == 1
    assert "docker action references are unsupported" in errors[0]
