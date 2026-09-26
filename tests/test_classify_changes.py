"""`scripts/classify_changes.py`: which changes require the exhaustive sweeps
(FT-26.02, ADR 0077). Every test injects the `git` runner; the escalation
rules come from the real `.github/validation-budgets.toml`."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_script() -> Any:
    path = ROOT / "scripts" / "classify_changes.py"
    spec = importlib.util.spec_from_file_location("classify_changes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["classify_changes"] = module
    spec.loader.exec_module(module)
    return module


classify = _load_script()
BUDGETS = classify.BUDGETS_FILE


def _git(files: Sequence[str]) -> Any:
    def runner(command: Sequence[str]) -> str:
        assert list(command[:3]) == ["git", "diff", "--name-only"]
        assert command[3] == "main...HEAD"
        return "\n".join(files) + "\n"

    return runner


def _decide(event: str, files: Sequence[str] = ("README.md",)) -> Any:
    return classify.decide(event, "main", "HEAD", BUDGETS, _git(files))


@pytest.mark.parametrize("event", ["push", "schedule", "workflow_dispatch"])
def test_the_exhaustive_tier_always_runs_outside_pull_requests(event: str) -> None:
    decision = classify.decide(event, None, None, BUDGETS, _git([]))
    assert decision.sweeps is True
    assert "always runs" in decision.reason


@pytest.mark.parametrize(
    "path",
    [
        "src/forge_template/engine.py",
        "src/forge_template/components/library/manifest.toml",
        "src/forge_template/foundation/content/pyproject.toml.jinja",
        "tests/composition_matrix.py",
        "tests/test_no_copy_inheritance.py",
        "tests/conftest.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/test-template.yml",
    ],
)
def test_a_pull_request_touching_a_sensitive_path_requires_the_sweeps(
    path: str,
) -> None:
    decision = _decide("pull_request", ["README.md", path])
    assert decision.sweeps is True
    assert path in decision.reason
    assert "1 of 2 changed files" in decision.reason


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "CONTRIBUTING.md",
        "docs/validation-budget.md",
        "docs/adr/0077-x.md",
        "src/forge_template/adr.py",
        "src/forge_template/schema.py",
        "src/forge_template/render.py",
        "src/forge_template/github_actions.py",
        "tests/test_living_docs.py",
        "scripts/labels.py",
        "template/README.md.jinja",
        ".github/audit-exceptions.toml",
    ],
)
def test_an_insensitive_pull_request_does_not_require_the_sweeps(path: str) -> None:
    decision = _decide("pull_request", [path])
    assert decision.sweeps is False
    assert (
        "still run on main, weekly, on dispatch and before a release" in decision.reason
    )


def test_one_sensitive_file_among_many_insensitive_ones_is_enough() -> None:
    files = ["README.md", *[f"docs/page{i}.md" for i in range(20)], "uv.lock"]
    assert _decide("pull_request", files).sweeps is True


def test_the_reason_lists_only_the_first_few_sensitive_paths() -> None:
    files = [f"src/forge_template/mod{i}.py" for i in range(6)]
    reason = _decide("pull_request", files).reason
    assert "6 of 6" in reason and "(+3 more)" in reason


# ---------------------------------------------------------------------------
# Fail closed
# ---------------------------------------------------------------------------


def test_an_empty_diff_cannot_prove_insensitivity() -> None:
    decision = classify.decide("pull_request", "main", "HEAD", BUDGETS, _git([]))
    assert decision.sweeps is True
    assert decision.reason.startswith("fail-closed:")


def test_a_git_failure_fails_closed() -> None:
    def broken(command: Sequence[str]) -> str:
        raise classify.ClassifyError("git diff failed: bad revision")

    decision = classify.decide("pull_request", "main", "HEAD", BUDGETS, broken)
    assert decision.sweeps is True
    assert "bad revision" in decision.reason


@pytest.mark.parametrize(("base", "head"), [(None, "HEAD"), ("main", None), ("", "")])
def test_a_pull_request_without_both_commits_fails_closed(
    base: str | None, head: str | None
) -> None:
    decision = classify.decide("pull_request", base, head, BUDGETS, _git(["a.md"]))
    assert decision.sweeps is True
    assert "needs --base and --head" in decision.reason


def test_an_unrecognised_event_fails_closed() -> None:
    decision = classify.decide("merge_group", "main", "HEAD", BUDGETS, _git(["a.md"]))
    assert decision.sweeps is True
    assert "unrecognised event" in decision.reason
    assert classify.decide("", None, None, BUDGETS, _git([])).sweeps is True


@pytest.mark.parametrize(
    "document",
    [
        "not toml [[",
        "schema = 1\n",
        "[escalation]\nsensitive_paths = []\nexcluded_paths = []\n",
        "[escalation]\nsensitive_paths = 'src/**'\nexcluded_paths = []\n",
        "[escalation]\nsensitive_paths = ['src/**']\n",
    ],
)
def test_an_unusable_budgets_file_fails_closed(tmp_path: Path, document: str) -> None:
    broken = tmp_path / "budgets.toml"
    broken.write_text(document, encoding="utf-8")
    decision = classify.decide("pull_request", "main", "HEAD", broken, _git(["a.md"]))
    assert decision.sweeps is True
    assert decision.reason.startswith("fail-closed:")


def test_a_missing_budgets_file_fails_closed(tmp_path: Path) -> None:
    decision = classify.decide(
        "pull_request", "main", "HEAD", tmp_path / "nope.toml", _git(["a.md"])
    )
    assert decision.sweeps is True


def test_a_missing_git_executable_is_a_classify_error() -> None:
    with pytest.raises(classify.ClassifyError, match="cannot run"):
        classify.default_runner(["definitely-not-an-installed-git"])


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------


def test_main_publishes_the_decision_to_the_workflow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output, summary = tmp_path / "out.txt", tmp_path / "summary.md"
    code = classify.main(
        ["--event", "pull_request", "--base", "main", "--head", "HEAD"],
        runner=_git(["docs/a.md"]),
        environ={"GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)},
    )
    assert code == 0
    assert output.read_text(encoding="utf-8") == "sweeps=false\n"
    assert "NOT REQUIRED" in summary.read_text(encoding="utf-8")
    assert "exhaustive sweeps: NOT REQUIRED" in capsys.readouterr().out


def test_main_reads_the_event_from_the_environment(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    classify.main(
        [],
        runner=_git([]),
        environ={"GITHUB_EVENT_NAME": "schedule", "GITHUB_OUTPUT": str(output)},
    )
    assert output.read_text(encoding="utf-8") == "sweeps=true\n"


def test_main_with_no_event_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    classify.main([], runner=_git([]), environ={"GITHUB_OUTPUT": str(output)})
    assert output.read_text(encoding="utf-8") == "sweeps=true\n"
