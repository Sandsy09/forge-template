"""`scripts/validation_report.py`: evidence, thresholds and the release gate
(FT-26.02, ADR 0077).

The fixtures under `tests/fixtures/validation_report/` are real: JUnit XML
recorded from a parallel local run of both sweeps over six compositions, and
`gh run view --json jobs` output (with steps) for a successful run, two history
runs, a run that failed in a test step and a run that was cancelled. No test
touches the network; the `gh` runner is injected.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = ROOT / "tests" / "fixtures" / "validation_report"


def _load_script() -> Any:
    path = ROOT / "scripts" / "validation_report.py"
    spec = importlib.util.spec_from_file_location("validation_report", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validation_report"] = module
    spec.loader.exec_module(module)
    return module


report = _load_script()
BUDGETS = report.load_budgets()
SLUGS = frozenset(
    {
        "cli",
        "cli+github",
        "data-science+jupyter",
        "library",
        "library+coverage",
        "streamlit",
    }
)
DIRECT = (_FIXTURES / "direct.xml").read_text(encoding="utf-8")
INDEPENDENT = (_FIXTURES / "independent.xml").read_text(encoding="utf-8")
VALID = BUDGETS["cost"]["valid_compositions"]
_INDEPENDENT = "Composition sweep -- independent client"
_DIRECT = "Composition sweep -- direct engine"


def _jobs(label: str) -> list[dict[str, Any]]:
    text = (_FIXTURES / f"jobs_{label}.json").read_text(encoding="utf-8")
    jobs: list[dict[str, Any]] = json.loads(text)["jobs"]
    return jobs


def _job(jobs: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(job for job in jobs if report.normalise(job["name"]) == name)


def _budget(
    current: list[dict[str, Any]],
    history: Sequence[list[dict[str, Any]]] = (),
    *,
    required: bool = True,
    executed: dict[str, str] | None = None,
    cpus: dict[str, str] | None = None,
    budgets: dict[str, Any] | None = None,
) -> Any:
    return report.build_budget_report(
        current,
        history,
        budgets or BUDGETS,
        sweeps_required=required,
        cpus=cpus or {},
        executed=executed or {"direct": str(VALID), "independent": str(VALID)},
    )


# ---------------------------------------------------------------------------
# verify-sweep: expected versus executed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "xml"), [("direct", DIRECT), ("independent", INDEPENDENT)]
)
def test_a_complete_real_sweep_proves_zero_silent_omissions(
    kind: str, xml: str
) -> None:
    cases, others = report.parse_junit(xml, kind)
    evidence = report.verify(cases, others, SLUGS, kind)
    assert evidence.ok
    assert (evidence.expected, evidence.executed, evidence.passed) == (6, 6, 6)
    text = "\n".join(report.evidence_lines(evidence, "AMD EPYC 7763"))
    assert "expected 6 compositions, executed 6, passed 6" in text
    assert "RESULT: zero silent omissions" in text
    assert "runner CPU: AMD EPYC 7763" in text


def test_the_order_of_execution_does_not_matter() -> None:
    """xdist runs cases in any order; only the set matters."""
    cases, others = report.parse_junit(DIRECT, "direct")
    assert [c.slug for c in cases] != sorted(c.slug for c in cases)
    assert report.verify(list(reversed(cases)), others, SLUGS, "direct").ok


def test_a_silently_omitted_composition_is_named_and_fails() -> None:
    cases, others = report.parse_junit(DIRECT, "direct")
    evidence = report.verify(cases[:-1], others, SLUGS, "direct")
    assert not evidence.ok
    assert evidence.executed == 5 and len(evidence.missing) == 1
    text = "\n".join(report.evidence_lines(evidence, "x"))
    assert "MISSING (silently omitted): 1" in text
    assert "RESULT: FAILED" in text


def test_an_unexpected_composition_fails() -> None:
    cases, others = report.parse_junit(DIRECT, "direct")
    extra = [*cases, report.Case("ghost+capability", "passed")]
    evidence = report.verify(extra, others, SLUGS, "direct")
    assert evidence.unexpected == ("ghost+capability",) and not evidence.ok


def test_a_duplicated_composition_fails() -> None:
    cases, others = report.parse_junit(DIRECT, "direct")
    evidence = report.verify([*cases, cases[0]], others, SLUGS, "direct")
    assert evidence.duplicates == (cases[0].slug,) and not evidence.ok


def test_a_skipped_composition_did_not_execute() -> None:
    cases, others = report.parse_junit(DIRECT, "direct")
    skipped = [report.Case(cases[0].slug, "skipped"), *cases[1:]]
    evidence = report.verify(skipped, others, SLUGS, "direct")
    assert evidence.skipped == (cases[0].slug,)
    assert evidence.executed == 5 and evidence.passed == 5 and not evidence.ok


def test_a_failed_composition_is_executed_but_not_passed() -> None:
    cases, others = report.parse_junit(DIRECT, "direct")
    failed = [report.Case(cases[0].slug, "failed"), *cases[1:]]
    evidence = report.verify(failed, others, SLUGS, "direct")
    assert evidence.executed == 6 and evidence.passed == 5 and not evidence.ok
    assert evidence.failed == (cases[0].slug,)


def test_an_empty_sweep_proves_nothing() -> None:
    assert not report.verify([], [], SLUGS, "direct").ok
    assert not report.verify([], [], frozenset(), "direct").ok


def test_junit_outcomes_are_read_from_failure_error_and_skipped_children() -> None:
    def case(name: str, child: str = "") -> str:
        body = f"<{child}/>" if child else ""
        return f'<testcase name="{name}">{body}</testcase>'

    prefix = "test_every_valid_composition_plans_and_renders"
    tripwire = "test_the_derived_matrix_size_is_the_recorded_tripwire"
    body = "".join(
        [
            case(f"{prefix}[a]"),
            case(f"{prefix}[b]", "failure"),
            case(f"{prefix}[c]", "error"),
            case(f"{prefix}[d]", "skipped"),
            case(tripwire, "failure"),
            case("test_unrelated"),
        ]
    )
    xml = f"<testsuites><testsuite>{body}</testsuite></testsuites>"
    cases, others = report.parse_junit(xml, "direct")
    assert {c.slug: c.outcome for c in cases} == {
        "a": "passed",
        "b": "failed",
        "c": "failed",
        "d": "skipped",
    }
    assert others == ["test_the_derived_matrix_size_is_the_recorded_tripwire (failed)"]


def test_another_test_failing_in_the_sweep_file_fails_the_evidence() -> None:
    cases, _ = report.parse_junit(DIRECT, "direct")
    evidence = report.verify(cases, ["tripwire (failed)"], SLUGS, "direct")
    assert not evidence.ok and evidence.other_problems == ("tripwire (failed)",)


def test_the_two_sweeps_are_told_apart_by_their_test_function() -> None:
    assert report.parse_junit(INDEPENDENT, "direct")[0] == []
    assert len(report.parse_junit(INDEPENDENT, "independent")[0]) == 6


def test_invalid_junit_is_a_report_error() -> None:
    with pytest.raises(report.ReportError, match="not valid"):
        report.parse_junit("<not xml", "direct")


def test_the_cpu_model_is_read_from_lscpu_or_unknown() -> None:
    sample = (
        "Architecture: x86_64\nModel name:           AMD EPYC 7763 64-Core Processor\n"
    )
    assert report.cpu_model(lambda command: sample) == "AMD EPYC 7763 64-Core Processor"
    assert report.cpu_model(lambda command: "nothing useful") == "unknown"

    def broken(command: Sequence[str]) -> str:
        raise report.ReportError("no lscpu")

    assert report.cpu_model(broken) == "unknown"


def test_expected_slugs_are_the_catalogues_valid_compositions() -> None:
    slugs = report.expected_slugs()
    assert len(slugs) == VALID
    assert {"library", "cli+github"} <= slugs


# ---------------------------------------------------------------------------
# The approved threshold rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("samples", "expected"),
    [
        ([10.5, 10.6, 10.4], "ok"),
        ([14.0, 10.0, 10.0], "ok"),  # one run above warn is noise
        ([14.0, 14.0, 10.0], "WARN"),  # 2 of the last 3 above warn
        ([10.0, 14.0, 14.0], "WARN"),
        ([17.0, 11.0, 11.0], "OUTLIER"),  # above fail, median below warn
        ([17.0, 16.8, 16.9], "FAIL"),  # above fail and median above warn
        ([17.0, 14.0, 10.0], "FAIL"),  # median 14 > 13.5
        ([16.0, 16.0, 16.0], "WARN"),  # at the failure limit is not over it
        ([20.0], "FAIL"),  # no history: the run is its own median
        ([10.0], "ok"),
    ],
)
def test_the_noise_rule_over_the_last_three_runs(
    samples: list[float], expected: str
) -> None:
    assert report.verdict(samples, 13.5, 16.0) == expected


def test_only_the_three_newest_samples_count() -> None:
    assert report.verdict([10.0, 10.0, 10.0, 30.0, 30.0], 13.5, 16.0) == "ok"


# ---------------------------------------------------------------------------
# budget: the report over real runs
# ---------------------------------------------------------------------------


def test_a_healthy_real_run_reports_ok_with_the_baseline_comparison() -> None:
    result = _budget(
        _jobs("success"),
        [_jobs("history1"), _jobs("history2")],
        cpus={"direct": "AMD EPYC 7763", "independent": "AMD EPYC 9V74"},
    )
    text = "\n".join(result.lines)
    assert result.ok and result.problems == []
    assert "| Composition sweep -- independent client | T3 |" in text
    assert "| 10.5 / 10.6 | 13.5 / 16.0 |" in text  # baseline and limits shown
    assert "**Run wall (critical path)**" in text and "16.0 / 20.0" in text
    assert f"Valid compositions: **{VALID}**" in text
    assert "AMD EPYC 9V74" in text
    assert text.rstrip().endswith("RESULT: OK")


def test_required_sweeps_that_did_not_execute_everything_fail() -> None:
    result = _budget(_jobs("success"), executed={"direct": str(VALID)})
    assert not result.ok
    assert any(
        "independent sweep reports no executed compositions" in p
        for p in result.problems
    )
    short = _budget(
        _jobs("success"), executed={"direct": "10", "independent": str(VALID)}
    )
    assert any(
        "reports 10 executed compositions, expected" in p for p in short.problems
    )


def test_a_skipped_sweep_is_a_failure_when_the_sweeps_were_required() -> None:
    jobs = copy.deepcopy(_jobs("success"))
    _job(jobs, _INDEPENDENT)["conclusion"] = "skipped"
    result = _budget(jobs)
    assert not result.ok
    assert any(
        "independent sweep was required but its job was skipped" in p
        for p in result.problems
    )
    assert any(
        "skipped or missing exhaustive tier is never acceptable" in p
        for p in result.problems
    )


def test_a_sweep_skipped_after_an_upstream_failure_says_so() -> None:
    """Lint failing skips the sweeps that need it; the report names the cause."""
    jobs = copy.deepcopy(_jobs("success"))
    lint = _job(jobs, "Lint template")
    lint["conclusion"] = "failure"
    lint["steps"] = [{"name": "Schema and unit tests", "conclusion": "failure"}]
    for name in (_DIRECT, _INDEPENDENT):
        _job(jobs, name)["conclusion"] = "skipped"
    result = _budget(jobs)
    skipped = [p for p in result.problems if "sweep was required" in p]
    assert len(skipped) == 2
    assert all("an earlier job failed in this run" in p for p in skipped)
    assert result.problems[0].startswith("Lint template: test failure")


def test_a_missing_sweep_is_a_failure_when_the_sweeps_were_required() -> None:
    jobs = [job for job in _jobs("success") if _INDEPENDENT not in job["name"]]
    result = _budget(jobs)
    assert any("job was missing" in p for p in result.problems)


def test_a_skipped_sweep_is_fine_when_the_change_did_not_need_it() -> None:
    jobs = copy.deepcopy(_jobs("success"))
    for name in (_DIRECT, _INDEPENDENT):
        _job(jobs, name)["conclusion"] = "skipped"
    result = _budget(jobs, required=False, executed={})
    text = "\n".join(result.lines)
    assert result.ok
    assert "no (not needed)" in text and "skipped" in text


@pytest.mark.parametrize(
    ("label", "kind", "fragment"),
    [
        ("failure", "test", "step 'Schema and unit tests' failed"),
        ("cancelled", "infrastructure", "the job was cancelled"),
    ],
)
def test_real_failed_runs_are_classified_and_advised(
    label: str, kind: str, fragment: str
) -> None:
    result = _budget(_jobs(label), required=False, executed={})
    assert not result.ok
    first = result.problems[0]
    assert f"{kind} failure" in first and fragment in first
    if kind == "test":
        assert "fix the change, do not just rerun" in first
    else:
        assert "rerun the failed job" in first and "gh run rerun --failed" in first


def test_the_aggregate_gate_is_never_reported_as_a_cause() -> None:
    result = _budget(_jobs("failure"), required=False, executed={})
    assert not any("All checks passed" in p for p in result.problems)


@pytest.mark.parametrize(
    ("step", "kind"),
    [
        ("Set up job", "infrastructure"),
        ("Run actions/checkout@abc", "infrastructure"),
        ("Install uv", "infrastructure"),
        ("Install dependencies", "infrastructure"),
        ("Post Run actions/checkout@abc", "infrastructure"),
        ("Pre-commit", "test"),
        ("Check wheel", "test"),
        ("Plan and render every valid composition", "test"),
        ("Verify expected versus executed compositions", "test"),
    ],
)
def test_a_failed_step_decides_infrastructure_versus_test(step: str, kind: str) -> None:
    job = {
        "conclusion": "failure",
        "steps": [
            {"name": "Set up job", "conclusion": "success"},
            {"name": step, "conclusion": "failure"},
        ],
    }
    if step == "Set up job":
        job["steps"] = [{"name": step, "conclusion": "failure"}]
    assert report.classify_failure(job)[0] == kind


def test_a_job_that_failed_without_a_failing_step_is_infrastructure() -> None:
    assert (
        report.classify_failure({"conclusion": "failure", "steps": []})[0]
        == "infrastructure"
    )
    assert report.classify_failure({"conclusion": "failure"})[0] == "infrastructure"


def _tightened(job_id: str, warn: float, fail: float) -> dict[str, Any]:
    budgets: dict[str, Any] = copy.deepcopy(BUDGETS)
    for entry in budgets["job"]:
        if entry["id"] == job_id:
            entry["warn_minutes"], entry["fail_minutes"] = warn, fail
    return budgets


def test_a_real_regression_fails_with_attribution() -> None:
    """Tighten the independent sweep's limits below its real timings on both
    the current run and the history, as a genuine regression would."""
    budgets = _tightened("linux-checks.yml:sweep-independence", 3.0, 4.0)
    result = _budget(
        _jobs("success"),
        [_jobs("history1"), _jobs("history2")],
        budgets=budgets,
        cpus={"independent": "AMD EPYC 7763 64-Core Processor"},
    )
    assert not result.ok
    text = "\n".join(result.lines)
    assert "| FAIL |" in text
    problem = next(
        p for p in result.problems if "exceeded its approved failure limit" in p
    )
    assert _INDEPENDENT in problem and "median of the last 3 runs" in problem
    attribution = next(
        line for line in result.lines if line.startswith("- ") and "(T3)" in line
    )
    assert "x its baseline p90 10.6" in attribution
    assert (
        "step 'Render every valid composition through a policy-driven client'"
        in attribution
    )
    assert "runner CPU AMD EPYC 7763" in attribution
    assert "a regression" in attribution


def test_a_single_slow_run_is_an_outlier_not_a_failure() -> None:
    """The current run is slow but the recent runs were fast: hardware noise."""
    budgets = _tightened("linux-checks.yml:sweep-independence", 3.0, 4.0)
    fast = copy.deepcopy(_jobs("history1"))
    for job in fast:
        if report.normalise(job["name"]) == _INDEPENDENT:
            job["completedAt"] = job["startedAt"]  # a 0-minute history run
    result = _budget(_jobs("success"), [fast, fast], budgets=budgets)
    text = "\n".join(result.lines)
    assert result.ok
    assert "| OUTLIER |" in text
    assert "consistent with slower runner hardware, not a regression" in text


def test_two_of_the_last_three_above_warn_is_a_warning_that_does_not_fail() -> None:
    budgets = _tightened("linux-checks.yml:sweep-independence", 3.0, 30.0)
    result = _budget(
        _jobs("success"), [_jobs("history1"), _jobs("history2")], budgets=budgets
    )
    assert result.ok
    assert "| WARN |" in "\n".join(result.lines)


def test_the_critical_path_budget_is_enforced() -> None:
    budgets = copy.deepcopy(BUDGETS)
    budgets["critical_path"].update(warn_minutes=1.0, fail_minutes=2.0)
    result = _budget(
        _jobs("success"), [_jobs("history1"), _jobs("history2")], budgets=budgets
    )
    assert any(
        "critical path took" in p and "approved 2.0 min limit" in p
        for p in result.problems
    )


def test_a_missing_sweep_entry_in_the_budgets_file_is_an_error() -> None:
    budgets = copy.deepcopy(BUDGETS)
    budgets["job"] = [
        e for e in budgets["job"] if e["id"] != "linux-checks.yml:sweep-independence"
    ]
    with pytest.raises(report.ReportError, match="no \\[\\[job\\]\\]"):
        _budget(_jobs("success"), budgets=budgets)


# ---------------------------------------------------------------------------
# release-evidence
# ---------------------------------------------------------------------------

_SHA = "26262338771531acf0b91a05bb079d62100bd638"


def _runs(*runs: dict[str, Any]) -> str:
    return json.dumps(list(runs))


def _run(
    run_id: int, status: str, conclusion: str | None, created: str
) -> dict[str, Any]:
    return {
        "databaseId": run_id,
        "status": status,
        "conclusion": conclusion,
        "createdAt": created,
    }


def _release(
    runs: str, jobs: list[dict[str, Any]] | None = None
) -> tuple[bool, list[str]]:
    def runner(command: Sequence[str]) -> str:
        if list(command[:3]) == ["gh", "run", "list"]:
            assert "--commit" in command and _SHA in command and "push" in command
            return runs
        return json.dumps({"jobs": jobs if jobs is not None else _jobs("success")})

    result: tuple[bool, list[str]] = report.check_release_evidence(
        _SHA, "test-template.yml", BUDGETS, runner
    )
    return result


def test_a_release_commit_with_both_sweeps_green_has_evidence() -> None:
    ok, lines = _release(_runs(_run(7, "completed", "success", "2026-09-26T13:00:00Z")))
    assert ok
    text = "\n".join(lines)
    assert "run 7 for 2626233 succeeded" in text
    assert "direct sweep (Composition sweep -- direct engine): success" in text
    assert (
        "independent sweep (Composition sweep -- independent client): success" in text
    )


def test_a_release_commit_with_no_run_is_refused() -> None:
    ok, lines = _release(_runs())
    assert not ok and "no `push` run" in lines[0] and "cannot be skipped" in lines[0]


def test_a_release_commit_whose_run_is_still_going_is_refused() -> None:
    ok, lines = _release(_runs(_run(7, "in_progress", None, "2026-09-26T13:00:00Z")))
    assert not ok and "still in_progress" in lines[0]


@pytest.mark.parametrize("conclusion", ["failure", "cancelled"])
def test_a_release_commit_whose_run_is_red_is_refused(conclusion: str) -> None:
    ok, lines = _release(
        _runs(_run(7, "completed", conclusion, "2026-09-26T13:00:00Z"))
    )
    assert not ok and f"concluded {conclusion}" in lines[0]


def test_the_newest_run_for_the_commit_decides() -> None:
    older_green = _run(1, "completed", "success", "2026-09-26T12:00:00Z")
    newer_red = _run(2, "completed", "failure", "2026-09-26T13:00:00Z")
    ok, lines = _release(_runs(older_green, newer_red))
    assert not ok and "run 2" in lines[0]


def test_a_skipped_sweep_in_the_release_commits_run_is_refused() -> None:
    jobs = copy.deepcopy(_jobs("success"))
    _job(jobs, _INDEPENDENT)["conclusion"] = "skipped"
    ok, lines = _release(
        _runs(_run(7, "completed", "success", "2026-09-26T13:00:00Z")), jobs
    )
    assert not ok
    assert any("independent sweep job was skipped in run 7" in line for line in lines)
    assert any(
        "independent-client evidence on its own commit" in line for line in lines
    )


def test_a_missing_sweep_in_the_release_commits_run_is_refused() -> None:
    jobs = [job for job in _jobs("success") if _DIRECT not in job["name"]]
    ok, lines = _release(
        _runs(_run(7, "completed", "success", "2026-09-26T13:00:00Z")), jobs
    )
    assert not ok and any("direct sweep job was missing" in line for line in lines)


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_verify_sweep_passes_writes_outputs_and_a_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output, summary = tmp_path / "out.txt", tmp_path / "summary.md"
    code = report.main(
        ["verify-sweep", "--kind", "direct", "--junit", str(_FIXTURES / "direct.xml")],
        runner=lambda command: "Model name: Test CPU\n",
        environ={"GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)},
        expected=SLUGS,
    )
    assert code == 0
    assert output.read_text(encoding="utf-8") == "expected=6\nexecuted=6\n"
    assert "zero silent omissions" in summary.read_text(encoding="utf-8")
    assert "runner CPU: Test CPU" in capsys.readouterr().out


def test_verify_sweep_fails_and_annotates_on_an_omission(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    trimmed = DIRECT.replace(
        'name="test_every_valid_composition_plans_and_renders[streamlit]"',
        'name="something_else"',
    )
    code = report.main(
        [
            "verify-sweep",
            "--kind",
            "direct",
            "--junit",
            str(_write(tmp_path, "d.xml", trimmed)),
        ],
        runner=lambda command: "",
        environ={"GITHUB_ACTIONS": "true"},
        expected=SLUGS,
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "MISSING (silently omitted)" in out and "::error::" in out


def test_verify_sweep_with_unreadable_junit_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = report.main(
        [
            "verify-sweep",
            "--kind",
            "direct",
            "--junit",
            str(_write(tmp_path, "d.xml", "<bad")),
        ],
        runner=lambda command: "",
        environ={},
        expected=SLUGS,
    )
    assert code == 1 and "ERROR:" in capsys.readouterr().out


def _gh(runs_for: dict[str, list[int]]) -> Any:
    """A fake `gh`: `run list` returns history ids, `run view` a fixture by id."""
    by_id = {9: "success", 8: "history1", 7: "history2"}

    def runner(command: Sequence[str]) -> str:
        if list(command[:3]) == ["gh", "run", "list"]:
            return json.dumps([{"databaseId": i} for i in runs_for["ids"]])
        assert list(command[:3]) == ["gh", "run", "view"]
        return json.dumps({"jobs": _jobs(by_id[int(command[3])])})

    return runner


def test_budget_command_passes_for_a_healthy_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    code = report.main(
        [
            "budget",
            "--run-id",
            "9",
            "--sweeps-required",
            "true",
            "--cpu",
            "direct=AMD EPYC 7763",
            "--executed",
            f"direct={VALID}",
            "--executed",
            f"independent={VALID}",
        ],
        runner=_gh({"ids": [9, 8, 7]}),
        environ={"GITHUB_STEP_SUMMARY": str(summary)},
    )
    assert code == 0
    assert "RESULT: OK" in capsys.readouterr().out
    assert summary.read_text(encoding="utf-8").startswith("## Validation report")


def test_budget_command_excludes_the_current_run_from_its_history(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[str] = []

    def runner(command: Sequence[str]) -> str:
        if list(command[:3]) == ["gh", "run", "view"]:
            seen.append(command[3])
        text: str = _gh({"ids": [9, 8, 7]})(command)
        return text

    report.main(
        [
            "budget",
            "--run-id",
            "9",
            "--sweeps-required",
            "false",
            "--history",
            "2",
        ],
        runner=runner,
        environ={},
    )
    assert seen == ["9", "8", "7"]  # the run itself once, then two history runs


def test_budget_command_fails_and_annotates_when_required_sweeps_did_not_execute(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = report.main(
        ["budget", "--run-id", "9", "--sweeps-required", "true"],
        runner=_gh({"ids": [9, 8, 7]}),
        environ={"GITHUB_ACTIONS": "true"},
    )
    out = capsys.readouterr().out
    assert (
        code == 1
        and "::error::the direct sweep reports no executed compositions" in out
    )


def test_release_evidence_command_exit_codes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def runner(runs: str) -> Any:
        def call(command: Sequence[str]) -> str:
            if list(command[:3]) == ["gh", "run", "list"]:
                return runs
            return json.dumps({"jobs": _jobs("success")})

        return call

    green = _runs(_run(7, "completed", "success", "2026-09-26T13:00:00Z"))
    assert (
        report.main(
            ["release-evidence", "--sha", _SHA], runner=runner(green), environ={}
        )
        == 0
    )
    assert (
        report.main(
            ["release-evidence", "--sha", _SHA], runner=runner(_runs()), environ={}
        )
        == 1
    )
    assert "Release evidence" in capsys.readouterr().out


def test_gh_failures_are_reported_as_errors(capsys: pytest.CaptureFixture[str]) -> None:
    def broken(command: Sequence[str]) -> str:
        raise report.ReportError("gh run view failed: not logged in")

    code = report.main(
        ["budget", "--run-id", "1", "--sweeps-required", "false"],
        runner=broken,
        environ={},
    )
    assert code == 1 and "not logged in" in capsys.readouterr().out


def test_the_budgets_file_names_both_sweeps_by_display_name() -> None:
    names = report.sweep_display_names(BUDGETS)
    assert names == {"direct": _DIRECT, "independent": _INDEPENDENT}
    assert (
        tomllib.loads(
            (ROOT / ".github" / "validation-budgets.toml").read_text(encoding="utf-8")
        )["schema"]
        == 1
    )


def test_a_missing_gh_executable_is_a_report_error() -> None:
    with pytest.raises(report.ReportError, match="cannot run"):
        report.default_runner(["definitely-not-an-installed-gh"])
