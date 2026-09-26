"""`scripts/ci_timings.py`: the reproducible baseline behind the validation
budget (FT-26.01, ADR 0076).

Every test runs the script through an injected `gh`/`git` runner. The fixtures
under `tests/fixtures/ci_timings/` are real `gh run list` / `gh run view --json
jobs` output, trimmed to the fields the script reads: five runs (three
successful, one cancelled, one failed) and the jobs of three of them, one from
before the reusable workflow (bare job names) and two after (prefixed names).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = ROOT / "tests" / "fixtures" / "ci_timings"


def _load_script() -> Any:
    path = ROOT / "scripts" / "ci_timings.py"
    spec = importlib.util.spec_from_file_location("ci_timings", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ci_timings"] = module
    spec.loader.exec_module(module)
    return module


timings = _load_script()

RUN_LIST = json.loads((_FIXTURES / "run_list.json").read_text(encoding="utf-8"))
_SUCCESSFUL = (35739922722, 35741510636, 36241783316)  # oldest first


def _jobs(run_id: int) -> dict[str, Any]:
    text = (_FIXTURES / f"jobs_{run_id}.json").read_text(encoding="utf-8")
    payload: dict[str, Any] = json.loads(text)
    return payload


def _fixture_runner(command: Sequence[str]) -> str:
    """Answers `gh run list` and `gh run view <id>` from the fixtures."""
    command = list(command)
    if command[:3] == ["gh", "run", "list"]:
        return json.dumps(RUN_LIST)
    if command[:3] == ["gh", "run", "view"]:
        return json.dumps(_jobs(int(command[3])))
    if command[:3] == ["git", "show", "-s"]:
        return "2026-09-22T14:30:00+00:00\n"
    raise AssertionError(f"unexpected command {command}")


def _expected(name_part: str) -> list[float]:
    """An independent computation of a job's minutes across the fixtures."""
    found = []
    for run_id in _SUCCESSFUL:
        for job in _jobs(run_id)["jobs"]:
            if name_part in job["name"] and job["conclusion"] == "success":
                start = datetime.fromisoformat(job["startedAt"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(job["completedAt"].replace("Z", "+00:00"))
                found.append((end - start).total_seconds() / 60)
    return found


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Linux (ubuntu-24.04) / Archetype builds", "Archetype builds"),
        ("Runner canary (ubuntu-26.04) / Archetype builds", "Archetype builds"),
        ("Archetype builds", "Archetype builds"),
        ("Windows smoke", "Windows smoke"),
    ],
)
def test_job_names_compare_across_the_reusable_workflow_change(
    raw: str, expected: str
) -> None:
    assert timings.normalise_job_name(raw) == expected


def test_minutes_between_and_naive_times_are_utc() -> None:
    assert (
        timings.minutes_between("2026-09-26T12:00:00Z", "2026-09-26T12:10:30Z") == 10.5
    )
    aware = timings._time("2026-09-26T12:00:00Z")
    naive = timings._time("2026-09-26T12:00:00")
    assert aware == naive


def test_percentile_and_stats() -> None:
    assert timings.percentile([1, 2, 3, 4, 5], 0.5) == 3
    assert timings.percentile([10], 0.9) == 10
    assert timings.percentile([1, 2, 3, 4], 0.9) == pytest.approx(3.7)
    stats = timings.Stats.of([2.0, 4.0, 6.0])
    assert (stats.n, stats.minimum, stats.p50, stats.maximum) == (3, 2.0, 4.0, 6.0)


def test_resolve_since_accepts_a_timestamp_or_a_commit() -> None:
    assert (
        timings.resolve_since("2026-09-19T23:00", _fixture_runner) == "2026-09-19T23:00"
    )
    assert timings.resolve_since("47a7430", _fixture_runner).startswith("2026-09-22")


# ---------------------------------------------------------------------------
# Selecting runs
# ---------------------------------------------------------------------------


def test_only_successful_runs_are_selected_oldest_first() -> None:
    chosen = timings.select_runs(RUN_LIST, None, None, None)
    assert [run["databaseId"] for run in chosen] == list(_SUCCESSFUL)


def test_the_window_and_event_filters_apply() -> None:
    since = timings.select_runs(RUN_LIST, "2026-09-22T14:30", None, None)
    assert [run["databaseId"] for run in since] == [35741510636, 36241783316]
    until = timings.select_runs(RUN_LIST, None, "2026-09-22T14:30", None)
    assert [run["databaseId"] for run in until] == [35739922722]
    pushes = timings.select_runs(RUN_LIST, None, None, ["push"])
    assert {run["event"] for run in pushes} == {"push"}


# ---------------------------------------------------------------------------
# Collecting and reporting
# ---------------------------------------------------------------------------


def test_collect_reproduces_an_independent_computation() -> None:
    chosen = timings.select_runs(RUN_LIST, None, None, None)
    collected = timings.collect(chosen, _fixture_runner)
    assert collected.run_ids == list(_SUCCESSFUL)
    assert collected.commits == [run["headSha"][:7] for run in chosen]
    # Old bare names and new prefixed names land in the same series.
    got = collected.jobs["Composition sweep -- independent client"]
    assert got == pytest.approx(_expected("Composition sweep -- independent client"))
    assert len(got) == 3
    assert len(collected.walls) == 3 and all(wall > 1 for wall in collected.walls)


def test_steps_are_collected_for_the_heavy_jobs() -> None:
    chosen = timings.select_runs(RUN_LIST, None, None, None)
    collected = timings.collect(chosen, _fixture_runner)
    key = (
        "Composition sweep -- independent client",
        "Render every valid composition through a policy-driven client",
    )
    assert len(collected.steps[key]) == 3


def test_a_job_that_did_not_succeed_is_left_out() -> None:
    runner_calls: list[str] = []

    def runner(command: Sequence[str]) -> str:
        runner_calls.append(command[3])
        payload = _jobs(36241783316)
        payload["jobs"][0]["conclusion"] = "failure"
        return json.dumps(payload)

    only = [run for run in RUN_LIST if run["databaseId"] == 36241783316]
    collected = timings.collect(only, runner)
    first = timings.normalise_job_name(_jobs(36241783316)["jobs"][0]["name"])
    assert first not in collected.jobs


def test_the_report_counts_runs_above_the_approved_limits() -> None:
    budgets = timings.load_budgets(timings.BUDGETS_FILE)
    assert budgets is not None
    limits = timings.limits_for(budgets, "Composition sweep -- independent client")
    assert limits == (13.5, 16.0)
    assert timings.limits_for(budgets, "no such job") is None
    assert timings.limits_for(None, "Archetype builds") is None
    assert timings.crossings([10.0, 14.0, 17.0], 13.5, 16.0) == (2, 1)

    chosen = timings.select_runs(RUN_LIST, None, None, None)
    collected = timings.collect(chosen, _fixture_runner)
    report = timings.build_report(collected, budgets, show_steps=False)
    entry = report["jobs"]["Composition sweep -- independent client"]
    assert (entry["warn"], entry["fail"]) == (13.5, 16.0)
    assert entry["above_warn"] == 0 and entry["above_fail"] == 0

    collected.jobs["Composition sweep -- independent client"].append(17.0)
    slower = timings.build_report(collected, budgets, show_steps=False)
    assert slower["jobs"]["Composition sweep -- independent client"]["above_fail"] == 1


def test_text_output_flags_a_window_too_small_for_a_baseline() -> None:
    chosen = timings.select_runs(RUN_LIST, None, None, None)
    collected = timings.collect(chosen, _fixture_runner)
    text = timings.render_text(timings.build_report(collected, None, show_steps=True))
    assert "runs: 3 successful" in text
    assert "RUN WALL" in text
    assert "WARNING: only 3 runs; a baseline needs >= 20" in text
    assert "step: Composition sweep -- direct engine" in text


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------


def test_main_prints_the_baseline_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = timings.main(["--since", "47a7430"], runner=_fixture_runner)
    out = capsys.readouterr().out
    assert code == 0
    assert "runs: 2 successful" in out  # the git-resolved date excludes the oldest
    assert "Composition sweep -- independent client" in out


def test_main_json_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    code = timings.main(["--json"], runner=_fixture_runner)
    document = json.loads(capsys.readouterr().out)
    assert code == 0
    assert document["runs"] == 3
    stats = document["jobs"]["Archetype builds"]["stats"]
    assert set(stats) == {"n", "min", "p50", "p90", "max", "sd"}
    assert document["run_wall"]["n"] == 3


def test_main_reports_an_empty_window_as_an_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = timings.main(["--since", "2030-01-01"], runner=_fixture_runner)
    assert code == 1
    assert "no successful runs in that window" in capsys.readouterr().out


def test_a_failing_command_is_a_clear_error(capsys: pytest.CaptureFixture[str]) -> None:
    def broken(command: Sequence[str]) -> str:
        raise timings.TimingsError("gh run list failed: not logged in")

    assert timings.main([], runner=broken) == 1
    assert "not logged in" in capsys.readouterr().out


def test_a_missing_executable_is_a_timings_error() -> None:
    with pytest.raises(timings.TimingsError, match="cannot run"):
        timings.default_runner(["definitely-not-an-installed-gh"])
