"""The runner-image contract in ``docs/ci-runner-baseline.md``, executably.

Expected labels are read from the contract's ``Baseline`` and ``Canary`` table
rows, so moving the baseline is one reviewed change to the workflows *and* the
document, and the two cannot drift apart. ``check_runner_labels`` (covered in
``test_github_actions.py``) separately rejects the moving ``ubuntu-latest``
alias.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from forge_template.schema import REPO_ROOT

_WORKFLOWS = REPO_ROOT / ".github" / "workflows"
_CONTRACT = REPO_ROOT / "docs" / "ci-runner-baseline.md"
_REUSABLE = "./.github/workflows/linux-checks.yml"
_REQUIRED_CHECK = "All checks passed"


def _workflow(name: str) -> dict[str, Any]:
    document = yaml.safe_load((_WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(document, dict), name
    return document


def _contract_label(role: str) -> str:
    """The label the contract records for a ``Baseline`` / ``Canary`` row."""
    text = _CONTRACT.read_text(encoding="utf-8")
    match = re.search(rf"^\| {role} \| `([^`]+)` \|", text, re.MULTILINE)
    assert match is not None, f"docs/ci-runner-baseline.md has no {role} row"
    return match.group(1)


def _on(document: dict[Any, Any]) -> dict[str, Any]:
    # PyYAML (YAML 1.1) parses a bare ``on`` key as the boolean True.
    triggers = document.get("on", document.get(True))
    assert isinstance(triggers, dict)
    return triggers


def test_contract_names_distinct_baseline_and_canary_images() -> None:
    baseline, canary = _contract_label("Baseline"), _contract_label("Canary")
    assert baseline.startswith("ubuntu-")
    assert canary.startswith("ubuntu-")
    assert canary != baseline, "the canary must be a different image"


def test_protected_ubuntu_jobs_run_on_the_contract_baseline() -> None:
    baseline = _contract_label("Baseline")

    ci = _workflow("test-template.yml")["jobs"]
    assert ci["linux"]["uses"] == _REUSABLE
    assert ci["linux"]["with"]["runner"] == baseline
    assert ci["all-green"]["runs-on"] == baseline

    release = _workflow("release.yml")["jobs"]
    assert {job["runs-on"] for job in release.values()} == {baseline}


def test_every_shared_linux_job_takes_its_runner_from_the_caller() -> None:
    document = _workflow("linux-checks.yml")
    inputs = _on(document)["workflow_call"]["inputs"]
    assert inputs["runner"]["required"] is True
    assert inputs["runner"]["type"] == "string"

    jobs = document["jobs"]
    assert set(jobs) == {
        "lint",
        "scaffold",
        "archetype",
        "sweep-composition",
        "sweep-independence",
        "update-compat",
        "wheel",
        "released-client",
    }
    for name, job in jobs.items():
        assert job["runs-on"] == "${{ inputs.runner }}", name


def test_canary_runs_the_same_checks_on_the_contract_canary_label() -> None:
    jobs = _workflow("runner-canary.yml")["jobs"]
    assert list(jobs) == ["canary"]
    assert jobs["canary"]["uses"] == _REUSABLE
    assert jobs["canary"]["with"] == {
        "runner": _contract_label("Canary"),
        "sweeps": True,  # the canary always runs the full set (ADR 0077)
    }


def test_canary_uses_the_same_triggers_as_protected_ci() -> None:
    canary = _on(_workflow("runner-canary.yml"))
    ci = _on(_workflow("test-template.yml"))
    assert canary == ci, "promotion counts the same Monday cron runs as CI"


def test_canary_cannot_gate_a_merge() -> None:
    """The canary lives in its own workflow, is not a ``needs`` of the required
    check, and cannot produce that check's name."""
    canary = _workflow("runner-canary.yml")
    assert _REQUIRED_CHECK not in {job.get("name") for job in canary["jobs"].values()}
    assert set(canary["permissions"]) == {"contents"}

    for path in sorted(_WORKFLOWS.glob("*.yml")):
        for name, job in yaml.safe_load(path.read_text(encoding="utf-8"))[
            "jobs"
        ].items():
            needs = job.get("needs", [])
            needs = [needs] if isinstance(needs, str) else needs
            assert "canary" not in needs, f"{path.name}:{name} depends on the canary"


def test_the_required_aggregate_gates_linux_windows_and_the_audit() -> None:
    jobs = _workflow("test-template.yml")["jobs"]
    assert jobs["all-green"]["name"] == _REQUIRED_CHECK
    assert set(jobs["all-green"]["needs"]) == {
        "classify",
        "linux",
        "windows",
        "audit",
        "budget",
    }
    assert jobs["all-green"]["if"] == "always()"
    # The Linux result is checked explicitly: a skipped call would otherwise
    # slip past the failure/cancelled grep.
    steps = jobs["all-green"]["steps"]
    assert 'needs.linux.result }}" != "success"' in steps[0]["run"]


def test_every_workflow_keeps_least_privilege() -> None:
    """Workflow-level scope is read-only everywhere; only ``release.yml``
    grants ``contents: write`` (and ``publish`` alone gets ``id-token``)."""
    for path in sorted(_WORKFLOWS.glob("*.yml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        scopes = document["permissions"]
        expected = "write" if path.name == "release.yml" else "read"
        assert scopes == {"contents": expected}, path.name

    publish = _workflow("release.yml")["jobs"]["publish"]
    assert publish["permissions"] == {"id-token": "write"}


def test_generated_workflows_keep_their_own_baseline() -> None:
    """The exclusion in FT-24.01: this contract must not silently alter what
    users' projects run on."""
    template = REPO_ROOT / "template" / ".github" / "workflows" / "ci.yml.jinja"
    github = (
        REPO_ROOT
        / "src"
        / "forge_template"
        / "components"
        / "github"
        / "content"
        / ".github"
        / "workflows"
        / "ci.yml.jinja"
    )
    for path in (template, github):
        text = Path(path).read_text(encoding="utf-8")
        assert "runs-on: ubuntu-latest" in text, path
        assert "ubuntu-24.04" not in text and "ubuntu-26.04" not in text, path


def test_archetype_job_keeps_temp_data_off_the_26_04_tmpfs() -> None:
    """ubuntu-26.04 mounts ``/tmp`` as a ~7.8G RAM tmpfs with a per-user quota
    (actions/runner-images#14777), which the archetype builds' temp venvs fill
    (#209). Its first step exports ``TMPDIR`` from ``RUNNER_TEMP`` -- on the
    workspace disk, like the uv cache -- so the fix cannot be dropped silently."""
    steps = _workflow("linux-checks.yml")["jobs"]["archetype"]["steps"]
    assert steps[0]["run"] == 'echo "TMPDIR=$RUNNER_TEMP" >> "$GITHUB_ENV"'
