"""Tests for immutable GitHub Actions workflow references."""

from __future__ import annotations

import textwrap
from pathlib import Path

from forge_template.github_actions import check_action_pins, check_runner_labels
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


def _jobs(tmp_path: Path, body: str) -> Path:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n" + textwrap.indent(textwrap.dedent(body), "  "),
        encoding="utf-8",
    )
    return workflows


def test_real_workflows_name_no_moving_ubuntu_alias() -> None:
    assert check_runner_labels(REPO_ROOT / ".github" / "workflows") == []


def test_generated_workflow_templates_are_out_of_scope() -> None:
    """Generated projects keep their own baseline (a separate decision)."""
    template = REPO_ROOT / "template" / ".github" / "workflows"
    assert "ubuntu-latest" in (template / "ci.yml.jinja").read_text(encoding="utf-8")
    assert check_runner_labels(template) == []


def test_ubuntu_latest_string_is_rejected(tmp_path: Path) -> None:
    body = """\
    build:
      runs-on: ubuntu-latest
    """
    errors = check_runner_labels(_jobs(tmp_path, body))
    assert len(errors) == 1
    assert "'build'" in errors[0]
    assert "ubuntu-latest" in errors[0]


def test_ubuntu_latest_in_a_list_is_rejected(tmp_path: Path) -> None:
    body = """\
    build:
      runs-on: [self-hosted, ubuntu-latest]
    """
    assert len(check_runner_labels(_jobs(tmp_path, body))) == 1


def test_ubuntu_latest_in_a_labels_mapping_is_rejected(tmp_path: Path) -> None:
    body = """\
    build:
      runs-on:
        labels: ubuntu-latest
    """
    assert len(check_runner_labels(_jobs(tmp_path, body))) == 1


def test_ubuntu_latest_handed_to_a_reusable_workflow_is_rejected(
    tmp_path: Path,
) -> None:
    body = """\
    linux:
      uses: ./.github/workflows/linux-checks.yml
      with:
        runner: ubuntu-latest
    """
    errors = check_runner_labels(_jobs(tmp_path, body))
    assert len(errors) == 1
    assert "'linux'" in errors[0]


def test_explicit_images_and_expressions_pass(tmp_path: Path) -> None:
    body = """\
    a:
      runs-on: ubuntu-24.04
    b:
      runs-on: ubuntu-26.04
    c:
      runs-on: ${{ inputs.runner }}
    d:
      runs-on: windows-latest
    """
    assert check_runner_labels(_jobs(tmp_path, body)) == []


def test_unparseable_workflow_is_reported(tmp_path: Path) -> None:
    errors = check_runner_labels(_jobs(tmp_path, "a: [unclosed\n"))
    assert len(errors) == 1
    assert "cannot read workflow" in errors[0]
