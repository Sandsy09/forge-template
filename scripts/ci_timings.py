"""Measures GitHub Actions job timings for the validation budget (FT-26.01).

Reproduces the baseline recorded in docs/validation-budget.md from a window of
real workflow runs, so a re-baseline is a re-run of this script and not a
hand-edited number. It reads run and job data through the `gh` CLI, keeps only
successful runs and jobs, and reports per-job wall time (min, p50, p90, max,
standard deviation), the whole run's wall time, and, when the approved budgets
in `.github/validation-budgets.toml` are present, how many historical runs
would have crossed each job's warning and failure limits.

Wall time here is a job's own `startedAt` to `completedAt`, so queueing is
excluded. The run wall is the first job's start to the last job's end.

Usage:
    uv run poe ci:timings -- --since 47a7430
    uv run python scripts/ci_timings.py --since 2026-09-19T23:05 --steps
    uv run python scripts/ci_timings.py --since 47a7430 --json > baseline.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import tomllib
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BUDGETS_FILE = REPO_ROOT / ".github" / "validation-budgets.toml"
MIN_RUNS = 20  # the smallest window a baseline may be taken from

# The reusable-workflow caller prefixes every Linux job's display name.
_JOB_PREFIX = re.compile(r"^(?:Linux|Runner canary) \(ubuntu-[0-9.]+\) / ")

Runner = Callable[[Sequence[str]], str]


class TimingsError(Exception):
    """The timings could not be collected or the input was invalid."""


def default_runner(command: Sequence[str]) -> str:
    """Run a command and return its stdout; the command is built here."""
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise TimingsError(f"cannot run {command[0]!r}: {exc}") from exc
    if result.returncode != 0:
        raise TimingsError(
            f"{' '.join(command[:3])} failed: {result.stderr.strip()[:300]}"
        )
    return result.stdout


# ---------------------------------------------------------------------------
# Small numeric helpers
# ---------------------------------------------------------------------------


def normalise_job_name(name: str) -> str:
    """Strip the reusable-workflow prefix so old and new run names compare."""
    return _JOB_PREFIX.sub("", name)


def _time(value: str) -> datetime:
    """Parse an ISO timestamp; one without a timezone is taken as UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def minutes_between(start: str, end: str) -> float:
    """Elapsed minutes between two ISO timestamps."""
    return (_time(end) - _time(start)).total_seconds() / 60


def percentile(values: Sequence[float], fraction: float) -> float:
    """Linear-interpolated percentile of a non-empty sequence."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


@dataclass(frozen=True)
class Stats:
    """Summary of a sample of wall times in minutes."""

    n: int
    minimum: float
    p50: float
    p90: float
    maximum: float
    sd: float

    @classmethod
    def of(cls, values: Sequence[float]) -> Stats:
        """Summarise a non-empty sample."""
        return cls(
            len(values),
            min(values),
            statistics.median(values),
            percentile(values, 0.9),
            max(values),
            statistics.pstdev(values),
        )


# ---------------------------------------------------------------------------
# Selecting and collecting runs
# ---------------------------------------------------------------------------


def resolve_since(value: str, runner: Runner) -> str:
    """An ISO timestamp as given, or a commit's committer date via git."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return runner(["git", "show", "-s", "--format=%cI", value]).strip()
    return value


def select_runs(
    runs: Sequence[dict[str, Any]],
    since: str | None,
    until: str | None,
    events: Sequence[str] | None,
) -> list[dict[str, Any]]:
    """Successful runs inside the window, oldest first."""
    chosen = []
    for run in runs:
        created = run["createdAt"].replace("Z", "+00:00")
        if run.get("conclusion") != "success":
            continue
        if since and _time(created) < _time(since.replace("Z", "+00:00")):
            continue
        if until and _time(created) > _time(until.replace("Z", "+00:00")):
            continue
        if events and run["event"] not in events:
            continue
        chosen.append(run)
    return sorted(chosen, key=lambda run: run["createdAt"])


@dataclass
class Timings:
    """Wall times gathered across a window of runs."""

    jobs: dict[str, list[float]]
    steps: dict[tuple[str, str], list[float]]
    walls: list[float]
    run_ids: list[int]
    commits: list[str]


def collect(runs: Sequence[dict[str, Any]], runner: Runner) -> Timings:
    """Fetch every selected run's jobs and gather job, step and run times."""
    timings = Timings(defaultdict(list), defaultdict(list), [], [], [])
    for run in runs:
        text = runner(["gh", "run", "view", str(run["databaseId"]), "--json", "jobs"])
        jobs = json.loads(text)["jobs"]
        starts: list[str] = []
        ends: list[str] = []
        for job in jobs:
            if job.get("conclusion") != "success":
                continue
            if not (job.get("startedAt") and job.get("completedAt")):
                continue
            name = normalise_job_name(job["name"])
            timings.jobs[name].append(
                minutes_between(job["startedAt"], job["completedAt"])
            )
            starts.append(job["startedAt"])
            ends.append(job["completedAt"])
            for step in job.get("steps", []):
                if step.get("conclusion") == "success" and step.get("startedAt"):
                    timings.steps[(name, step["name"])].append(
                        minutes_between(step["startedAt"], step["completedAt"])
                    )
        if starts:
            timings.walls.append(
                minutes_between(min(starts, key=_time), max(ends, key=_time))
            )
            timings.run_ids.append(run["databaseId"])
            timings.commits.append(run["headSha"][:7])
    return timings


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------


def load_budgets(path: Path) -> dict[str, Any] | None:
    """The approved budgets file, or None when it does not exist yet."""
    if not path.is_file():
        return None
    return tomllib.loads(path.read_text(encoding="utf-8"))


def limits_for(budgets: dict[str, Any] | None, name: str) -> tuple[float, float] | None:
    """The (warn, fail) minutes approved for a job display name, if any."""
    if not budgets:
        return None
    for entry in budgets.get("job", []):
        if name in entry.get("display", []):
            return entry["warn_minutes"], entry["fail_minutes"]
    return None


def crossings(values: Sequence[float], warn: float, fail: float) -> tuple[int, int]:
    """How many samples exceed the warning and the failure limits."""
    return (
        sum(1 for value in values if value > warn),
        sum(1 for value in values if value > fail),
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def build_report(
    timings: Timings, budgets: dict[str, Any] | None, show_steps: bool
) -> dict[str, Any]:
    """Everything the text and JSON outputs are rendered from."""
    jobs = {}
    for name, values in timings.jobs.items():
        entry: dict[str, Any] = {"stats": Stats.of(values)}
        limits = limits_for(budgets, name)
        if limits:
            warn, fail = limits
            above_warn, above_fail = crossings(values, warn, fail)
            entry |= {
                "warn": warn,
                "fail": fail,
                "above_warn": above_warn,
                "above_fail": above_fail,
            }
        jobs[name] = entry
    report: dict[str, Any] = {
        "runs": len(timings.run_ids),
        "first_commit": timings.commits[0] if timings.commits else None,
        "last_commit": timings.commits[-1] if timings.commits else None,
        "first_run": timings.run_ids[0] if timings.run_ids else None,
        "last_run": timings.run_ids[-1] if timings.run_ids else None,
        "run_wall": Stats.of(timings.walls) if timings.walls else None,
        "jobs": jobs,
    }
    if show_steps:
        report["steps"] = {
            f"{job} / {step}": Stats.of(values)
            for (job, step), values in timings.steps.items()
            if statistics.median(values) >= 0.15
        }
    return report


def _row(label: str, stats: Stats, extra: str = "") -> str:
    return (
        f"{label[:52]:52} {stats.n:>3} {stats.minimum:>6.1f} {stats.p50:>6.1f} "
        f"{stats.p90:>6.1f} {stats.maximum:>6.1f} {stats.sd:>5.2f}{extra}"
    )


def render_text(report: dict[str, Any]) -> str:
    """The human-readable tables."""
    lines = [
        f"runs: {report['runs']} successful "
        f"({report['first_commit']} run {report['first_run']} .. "
        f"{report['last_commit']} run {report['last_run']})",
        f"{'job (minutes)':52} {'n':>3} {'min':>6} {'p50':>6} {'p90':>6} "
        f"{'max':>6} {'sd':>5}  warn/fail  above",
    ]
    ranked = sorted(report["jobs"].items(), key=lambda kv: -kv[1]["stats"].p50)
    for name, entry in ranked:
        extra = ""
        if "warn" in entry:
            extra = (
                f"  {entry['warn']:>4}/{entry['fail']:<4}  "
                f"{entry['above_warn']}/{entry['above_fail']}"
            )
        lines.append(_row(name, entry["stats"], extra))
    if report["run_wall"]:
        lines.append(_row("RUN WALL (first start .. last end)", report["run_wall"]))
    for label, stats in sorted(report.get("steps", {}).items()):
        lines.append(_row("step: " + label, stats))
    if report["runs"] < MIN_RUNS:
        lines.append(
            f"WARNING: only {report['runs']} runs; a baseline needs >= {MIN_RUNS}"
        )
    return "\n".join(lines)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Stats):
        return {
            "n": value.n,
            "min": round(value.minimum, 2),
            "p50": round(value.p50, 2),
            "p90": round(value.p90, 2),
            "max": round(value.maximum, 2),
            "sd": round(value.sd, 2),
        }
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def main(argv: Sequence[str] | None = None, *, runner: Runner | None = None) -> int:
    """Collect the window's timings and print them."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--workflow", default="test-template.yml")
    parser.add_argument("--since", help="ISO timestamp or a commit (its date)")
    parser.add_argument("--until", help="ISO timestamp or a commit (its date)")
    parser.add_argument("--limit", type=int, default=200, help="runs to list")
    parser.add_argument("--events", nargs="*", help="only these events")
    parser.add_argument("--steps", action="store_true", help="also step times")
    parser.add_argument("--json", action="store_true", help="machine-readable")
    parser.add_argument("--budgets", type=Path, default=BUDGETS_FILE)
    args = parser.parse_args(argv)
    run = runner or default_runner

    try:
        since = resolve_since(args.since, run) if args.since else None
        until = resolve_since(args.until, run) if args.until else None
        listing = json.loads(
            run(
                [
                    "gh",
                    "run",
                    "list",
                    "--workflow",
                    args.workflow,
                    "--limit",
                    str(args.limit),
                    "--json",
                    "databaseId,headSha,event,conclusion,createdAt",
                ]
            )
        )
        selected = select_runs(listing, since, until, args.events)
        if not selected:
            raise TimingsError("no successful runs in that window")
        timings = collect(selected, run)
    except TimingsError as exc:
        print(f"ERROR: {exc}")
        return 1

    report = build_report(timings, load_budgets(args.budgets), args.steps)
    print(json.dumps(_jsonable(report), indent=2) if args.json else render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
