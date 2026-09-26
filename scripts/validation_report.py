"""Evidence, timing and threshold checks for the validation tiers.

FT-26.02 / ADR 0077, implementing docs/validation-budget.md. Three subcommands:

`verify-sweep`
    Compares the compositions a sweep *executed* (from its JUnit XML) with the
    compositions the catalogue says are valid, and fails on any difference:
    that is the evidence of zero silent omissions.

`budget`
    Reads this run's jobs from the Actions API and the previous runs on `main`,
    applies the approved warning and failure rule from
    `.github/validation-budgets.toml`, checks that required sweeps ran, and
    writes the matrix-size and timing report with attribution. A failed job is
    reported as an *infrastructure* failure (a setup step failed, or the job was
    cancelled or lost) or a *test* failure, with what to do about each.

`release-evidence`
    Requires the `push` run for a release commit to have both sweep jobs
    `success`: a release cannot proceed without the exhaustive tier.

Usage:
    uv run python scripts/validation_report.py verify-sweep --kind direct --junit x.xml
    uv run python scripts/validation_report.py release-evidence --sha <commit>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BUDGETS_FILE = REPO_ROOT / ".github" / "validation-budgets.toml"

# The test function each sweep kind is made of, and the job that runs it.
SWEEP_TESTS = {
    "direct": "test_every_valid_composition_plans_and_renders",
    "independent": "test_downstream_client_renders_every_valid_composition_identically",
}
SWEEP_JOB_IDS = {
    "direct": "linux-checks.yml:sweep-composition",
    "independent": "linux-checks.yml:sweep-independence",
}

# A job that fails in one of these steps failed to *start* the checks: a
# transient infrastructure problem, not a test result.
# Jobs whose result follows from the others; never reported as a cause.
_CONSEQUENCE_JOBS = frozenset({"Validation budget", "All checks passed"})
_SETUP_STEP_PREFIXES = (
    "Set up job",
    "Run actions/",
    "Install uv",
    "Install dependencies",
    "Complete job",
    "Post ",
)
_JOB_PREFIX = re.compile(r"^(?:Linux|Runner canary) \(ubuntu-[0-9.]+\) / ")

Runner = Callable[[Sequence[str]], str]


class ReportError(Exception):
    """The evidence or the timings could not be produced or trusted."""


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
        raise ReportError(f"cannot run {command[0]!r}: {exc}") from exc
    if result.returncode != 0:
        raise ReportError(
            f"{' '.join(command[:3])} failed: {result.stderr.strip()[:300]}"
        )
    return result.stdout


# ---------------------------------------------------------------------------
# verify-sweep: expected versus executed compositions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    """One executed test case of a sweep and how it ended."""

    slug: str
    outcome: str  # passed | failed | skipped


@dataclass(frozen=True)
class Evidence:
    """Expected versus executed compositions for one sweep."""

    kind: str
    expected: int
    executed: int  # distinct compositions that ran to a pass or a failure
    passed: int
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]
    duplicates: tuple[str, ...]
    failed: tuple[str, ...]
    skipped: tuple[str, ...]
    other_problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Every expected composition ran once and passed, and nothing else did."""
        return (
            self.expected > 0
            and self.passed == self.expected == self.executed
            and not (
                self.missing
                or self.unexpected
                or self.duplicates
                or self.failed
                or self.skipped
                or self.other_problems
            )
        )


def parse_junit(xml_text: str, kind: str) -> tuple[list[Case], list[str]]:
    """The sweep's cases, plus any other test in the file that did not pass."""
    function = SWEEP_TESTS[kind]
    try:
        root = ET.fromstring(xml_text)  # our own pytest output
    except ET.ParseError as exc:
        raise ReportError(f"the JUnit XML is not valid: {exc}") from exc
    cases: list[Case] = []
    others: list[str] = []
    for testcase in root.iter("testcase"):
        name = testcase.get("name", "")
        outcome = "passed"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            outcome = "failed"
        elif testcase.find("skipped") is not None:
            outcome = "skipped"
        if name.startswith(f"{function}[") and name.endswith("]"):
            cases.append(Case(name[len(function) + 1 : -1], outcome))
        elif outcome != "passed":
            others.append(f"{name} ({outcome})")
    return cases, others


def verify(
    cases: Sequence[Case], others: Sequence[str], expected: frozenset[str], kind: str
) -> Evidence:
    """Compare what ran with what the catalogue says is valid."""
    seen = Counter(case.slug for case in cases)
    ran = {case.slug for case in cases if case.outcome in ("passed", "failed")}
    passed = {case.slug for case in cases if case.outcome == "passed"}
    return Evidence(
        kind=kind,
        expected=len(expected),
        executed=len(ran & expected),
        passed=len(passed & expected),
        missing=tuple(sorted(expected - set(seen))),
        unexpected=tuple(sorted(set(seen) - expected)),
        duplicates=tuple(sorted(slug for slug, count in seen.items() if count > 1)),
        failed=tuple(sorted(c.slug for c in cases if c.outcome == "failed")),
        skipped=tuple(sorted(c.slug for c in cases if c.outcome == "skipped")),
        other_problems=tuple(others),
    )


def _sample(values: Sequence[str], limit: int = 5) -> str:
    shown = ", ".join(values[:limit])
    return shown + (f" (+{len(values) - limit} more)" if len(values) > limit else "")


def evidence_lines(evidence: Evidence, cpu: str) -> list[str]:
    """The human-readable evidence for one sweep."""
    label = f"{evidence.kind} sweep"
    lines = [
        f"{label}: expected {evidence.expected} compositions, executed "
        f"{evidence.executed}, passed {evidence.passed}",
        f"  runner CPU: {cpu}",
    ]
    for title, values in (
        ("MISSING (silently omitted)", evidence.missing),
        ("UNEXPECTED (not in the catalogue)", evidence.unexpected),
        ("DUPLICATED", evidence.duplicates),
        ("FAILED", evidence.failed),
        ("SKIPPED", evidence.skipped),
        ("OTHER TESTS NOT PASSING", evidence.other_problems),
    ):
        if values:
            lines.append(f"  {title}: {len(values)}: {_sample(values)}")
    lines.append(
        "  RESULT: zero silent omissions"
        if evidence.ok
        else "  RESULT: FAILED - the exhaustive tier is not proven"
    )
    return lines


def expected_slugs() -> frozenset[str]:
    """Every valid composition, derived from the installed catalogue."""
    sys.path.insert(0, str(REPO_ROOT))
    from tests.composition_matrix import valid_compositions

    return frozenset(composition.slug for composition in valid_compositions())


def cpu_model(runner: Runner) -> str:
    """The runner's CPU model, or `unknown` where `lscpu` is unavailable."""
    try:
        text = runner(["lscpu"])
    except ReportError:
        return "unknown"
    match = re.search(r"^Model name:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else "unknown"


# ---------------------------------------------------------------------------
# budget: thresholds, attribution, infrastructure versus test failures
# ---------------------------------------------------------------------------


def normalise(name: str) -> str:
    """Strip the reusable-workflow prefix so job names compare across runs."""
    return _JOB_PREFIX.sub("", name)


def load_budgets(path: Path = BUDGETS_FILE) -> dict[str, Any]:
    """The approved budgets file."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ReportError(f"cannot read {path.name}: {exc}") from exc


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def job_minutes(job: Mapping[str, Any]) -> float | None:
    """A completed job's own wall time in minutes, else None."""
    if not (job.get("startedAt") and job.get("completedAt")):
        return None
    return (_time(job["completedAt"]) - _time(job["startedAt"])).total_seconds() / 60


def fetch_jobs(run_id: int | str, runner: Runner) -> list[dict[str, Any]]:
    """A run's jobs, with steps, through `gh`."""
    text = runner(["gh", "run", "view", str(run_id), "--json", "jobs"])
    return list(json.loads(text)["jobs"])


def run_wall(jobs: Sequence[Mapping[str, Any]]) -> float | None:
    """First job start to last job end across the completed jobs."""
    done = [job for job in jobs if job_minutes(job) is not None]
    if not done:
        return None
    start = min(_time(job["startedAt"]) for job in done)
    end = max(_time(job["completedAt"]) for job in done)
    return (end - start).total_seconds() / 60


def verdict(samples: Sequence[float], warn: float, fail: float) -> str:
    """The approved noise rule over the newest-first `samples`.

    A warning needs 2 of the last 3 runs above `warn`. A failure needs the
    current run above `fail` AND the median of the last 3 above `warn`, so one
    hardware outlier cannot fail a build but a real shift does.
    """
    recent = list(samples[:3])
    if recent[0] > fail and statistics.median(recent) > warn:
        return "FAIL"
    if recent[0] > fail:
        return "OUTLIER"
    if sum(1 for value in recent if value > warn) >= 2:
        return "WARN"
    return "ok"


def classify_failure(job: Mapping[str, Any]) -> tuple[str, str]:
    """Whether a failed job is an infrastructure or a test failure, and why."""
    if job.get("conclusion") == "cancelled":
        return "infrastructure", "the job was cancelled"
    for step in job.get("steps") or []:
        if step.get("conclusion") == "failure":
            name = step.get("name", "")
            if name.startswith(_SETUP_STEP_PREFIXES):
                return "infrastructure", f"it failed in setup step {name!r}"
            return "test", f"step {name!r} failed"
    return "infrastructure", "it failed without a failing step (runner lost)"


def _longest_step(job: Mapping[str, Any]) -> str:
    steps = [
        (job_minutes(step) or 0.0, step.get("name", ""))
        for step in job.get("steps") or []
    ]
    if not steps:
        return "no step data"
    minutes, name = max(steps)
    total = job_minutes(job) or minutes or 1.0
    return f"step {name!r} took {minutes:.1f} min ({minutes / total:.0%} of the job)"


def _entry_for(budgets: Mapping[str, Any], name: str) -> dict[str, Any] | None:
    for entry in budgets.get("job", []):
        if name in entry.get("display", []):
            return dict(entry)
    return None


def sweep_display_names(budgets: Mapping[str, Any]) -> dict[str, str]:
    """The display name of each sweep job, from the budgets file."""
    names: dict[str, str] = {}
    for kind, job_id in SWEEP_JOB_IDS.items():
        entry = next((e for e in budgets.get("job", []) if e["id"] == job_id), None)
        if entry is None:
            raise ReportError(f"the budgets file has no [[job]] for {job_id}")
        names[kind] = entry["display"][0]
    return names


@dataclass
class BudgetResult:
    """The rendered report and whether it should fail the run."""

    lines: list[str]
    problems: list[str]

    @property
    def ok(self) -> bool:
        """No threshold, omission or job failure to report."""
        return not self.problems


def build_budget_report(
    current: Sequence[Mapping[str, Any]],
    history: Sequence[Sequence[Mapping[str, Any]]],
    budgets: Mapping[str, Any],
    *,
    sweeps_required: bool,
    cpus: Mapping[str, str],
    executed: Mapping[str, str],
) -> BudgetResult:
    """Apply the approved budgets to this run and its recent history."""
    lines = [
        "## Validation report",
        "",
        "| Job | Tier | Wall (min) | Baseline p50 / p90 | Warn / fail | Verdict |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    problems: list[str] = []
    attribution: list[str] = []
    history_minutes = _history_by_job(history)
    sweep_names = sweep_display_names(budgets)
    by_name = {normalise(job["name"]): job for job in current}

    for name, job in sorted(by_name.items()):
        # The report's own job and the aggregate gate are consequences, not causes.
        if job.get("status") != "completed" or name in _CONSEQUENCE_JOBS:
            continue
        conclusion = job.get("conclusion")
        entry = _entry_for(budgets, name)
        if conclusion == "failure" or conclusion == "cancelled":
            kind, detail = classify_failure(job)
            advice = (
                "transient: rerun the failed job (`gh run rerun --failed`)"
                if kind == "infrastructure"
                else "a real failure: fix the change, do not just rerun"
            )
            problems.append(f"{name}: {kind} failure, {detail}; {advice}")
        minutes = job_minutes(job)
        if entry is None or minutes is None or conclusion != "success":
            if conclusion == "skipped":
                tier = (entry or {}).get("tier", "-")
                lines.append(f"| {name} | {tier} | skipped | | | skipped |")
            continue
        warn, fail = entry["warn_minutes"], entry["fail_minutes"]
        samples = [minutes, *history_minutes.get(name, [])]
        result = verdict(samples, warn, fail)
        lines.append(
            f"| {name} | {entry['tier']} | {minutes:.1f} | "
            f"{entry['baseline_p50']} / {entry['baseline_p90']} | "
            f"{warn} / {fail} | {result} |"
        )
        if result in ("WARN", "FAIL", "OUTLIER"):
            attribution.append(_attribution(name, entry, job, samples, result, cpus))
        if result == "FAIL":
            problems.append(
                f"{name} exceeded its approved failure limit "
                f"({minutes:.1f} > {fail} min) and the median of the last 3 runs "
                f"is above {warn} min"
            )

    wall = run_wall(
        [job for job in current if normalise(job["name"]) not in _CONSEQUENCE_JOBS]
    )
    if wall is not None:
        path = budgets["critical_path"]
        walls = [wall, *[w for w in (run_wall(run) for run in history) if w]]
        result = verdict(walls, path["warn_minutes"], path["fail_minutes"])
        lines.append(
            f"| **Run wall (critical path)** | | {wall:.1f} | "
            f"p90 {path['baseline_p90_minutes']} | "
            f"{path['warn_minutes']} / {path['fail_minutes']} | {result} |"
        )
        if result == "FAIL":
            problems.append(
                f"the run's critical path took {wall:.1f} min, over the approved "
                f"{path['fail_minutes']} min limit"
            )

    lines += _sweep_section(
        by_name, sweep_names, budgets, sweeps_required, cpus, executed, problems
    )
    if attribution:
        lines += ["", "### Attribution", ""] + [f"- {item}" for item in attribution]
    if problems:
        lines += ["", "### Problems", ""] + [f"- {item}" for item in problems]
    lines += ["", "RESULT: " + ("OK" if not problems else "FAILED")]
    return BudgetResult(lines, problems)


def _history_by_job(
    history: Sequence[Sequence[Mapping[str, Any]]],
) -> dict[str, list[float]]:
    by_job: dict[str, list[float]] = {}
    for run in history:
        for job in run:
            minutes = job_minutes(job)
            if minutes is not None and job.get("conclusion") == "success":
                by_job.setdefault(normalise(job["name"]), []).append(minutes)
    return by_job


def _attribution(
    name: str,
    entry: Mapping[str, Any],
    job: Mapping[str, Any],
    samples: Sequence[float],
    result: str,
    cpus: Mapping[str, str],
) -> str:
    minutes = samples[0]
    ratio = minutes / entry["baseline_p90"]
    kind = (
        "direct"
        if "direct engine" in name
        else "independent"
        if "independent" in name
        else None
    )
    cpu = cpus.get(kind or "", "")
    hardware = f"; runner CPU {cpu}" if cpu else ""
    meaning = {
        "FAIL": "a regression: both the failure limit and the recent median exceeded",
        "WARN": "2 of the last 3 runs are above the warning limit",
        "OUTLIER": "one run above the failure limit while the recent median is not: "
        "consistent with slower runner hardware, not a regression",
    }[result]
    return (
        f"{name} ({entry['tier']}): {minutes:.1f} min is {ratio:.2f}x its baseline "
        f"p90 {entry['baseline_p90']}; {meaning}; {_longest_step(job)}{hardware}; "
        f"last 3 runs {', '.join(f'{s:.1f}' for s in samples[:3])}"
    )


def _sweep_section(
    by_name: Mapping[str, Mapping[str, Any]],
    sweep_names: Mapping[str, str],
    budgets: Mapping[str, Any],
    sweeps_required: bool,
    cpus: Mapping[str, str],
    executed: Mapping[str, str],
    problems: list[str],
) -> list[str]:
    valid = budgets["cost"]["valid_compositions"]
    lines = [
        "",
        "### Matrix size and coverage",
        "",
        f"Valid compositions: **{valid}** of {budgets['cost']['raw_candidates']} raw "
        f"candidates ({budgets['cost']['rejected_candidates']} rejected).",
        "",
        "| Sweep | Required | Job | Executed / expected | CPU |",
        "| --- | --- | --- | --- | --- |",
    ]
    for kind, name in sweep_names.items():
        job = by_name.get(name)
        state = (job or {}).get("conclusion") or "missing"
        ran = executed.get(kind, "")
        lines.append(
            f"| {kind} | {'yes' if sweeps_required else 'no (not needed)'} "
            f"| {state} | {ran or '-'} / {valid} | {cpus.get(kind, '-')} |"
        )
        if not sweeps_required:
            continue
        if state != "success":
            problems.append(
                f"the {kind} sweep was required but its job was {state}: a "
                "skipped or missing exhaustive tier is never acceptable"
            )
        elif ran != str(valid):
            problems.append(
                f"the {kind} sweep reports {ran or 'no'} executed compositions, "
                f"expected {valid}"
            )
    return lines


def recent_run_ids(
    workflow: str, branch: str, count: int, exclude: int, runner: Runner
) -> list[int]:
    """The most recent successful runs on `branch`, newest first."""
    text = runner(
        [
            "gh", "run", "list", "--workflow", workflow, "--branch", branch,
            "--status", "success", "--limit", str(count + 3),
            "--json", "databaseId",
        ]
    )  # fmt: skip
    ids = [run["databaseId"] for run in json.loads(text)]
    return [run_id for run_id in ids if run_id != exclude][:count]


# ---------------------------------------------------------------------------
# release-evidence
# ---------------------------------------------------------------------------


def check_release_evidence(
    sha: str, workflow: str, budgets: Mapping[str, Any], runner: Runner
) -> tuple[bool, list[str]]:
    """Whether the release commit's own run proves the exhaustive tier ran."""
    text = runner(
        [
            "gh", "run", "list", "--workflow", workflow, "--commit", sha,
            "--event", "push", "--limit", "10",
            "--json", "databaseId,status,conclusion,createdAt",
        ]
    )  # fmt: skip
    runs = sorted(json.loads(text), key=lambda run: run["createdAt"], reverse=True)
    if not runs:
        return False, [
            f"no `push` run of {workflow} exists for {sha[:7]}: wait for main's "
            "CI to run for this commit; the exhaustive tier cannot be skipped"
        ]
    newest = runs[0]
    if newest["status"] != "completed":
        return False, [
            f"run {newest['databaseId']} for {sha[:7]} is still {newest['status']}: "
            "wait for it to finish, then rerun the release"
        ]
    if newest["conclusion"] != "success":
        return False, [
            f"run {newest['databaseId']} for {sha[:7]} concluded "
            f"{newest['conclusion']}: fix or rerun main's CI, then rerun the release"
        ]
    jobs = {
        normalise(job["name"]): job for job in fetch_jobs(newest["databaseId"], runner)
    }
    lines = [f"run {newest['databaseId']} for {sha[:7]} succeeded"]
    problems: list[str] = []
    for kind, name in sweep_display_names(budgets).items():
        state = (jobs.get(name) or {}).get("conclusion") or "missing"
        lines.append(f"  {kind} sweep ({name}): {state}")
        if state != "success":
            problems.append(
                f"the {kind} sweep job was {state} in run {newest['databaseId']}: a "
                "release requires the exhaustive tier and the independent-client "
                "evidence on its own commit"
            )
    return not problems, lines + problems


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _emit(lines: Sequence[str], env: Mapping[str, str], *, markdown: bool) -> None:
    print("\n".join(lines))
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            body = "\n".join(lines)
            handle.write(body + "\n\n" if markdown else f"```text\n{body}\n```\n\n")


def _pairs(values: Sequence[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values or []:
        key, _, value = item.partition("=")
        result[key] = value
    return result


def _annotate(messages: Sequence[str], env: Mapping[str, str], level: str) -> None:
    if env.get("GITHUB_ACTIONS") == "true":
        for message in messages:
            print(f"::{level}::{message}")


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    environ: Mapping[str, str] | None = None,
    expected: frozenset[str] | None = None,
) -> int:
    """Run one subcommand; the runner, environment and expected set inject."""
    env = environ if environ is not None else os.environ
    run = runner or default_runner
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    verify_cmd = sub.add_parser("verify-sweep", help="expected versus executed")
    verify_cmd.add_argument("--kind", choices=sorted(SWEEP_TESTS), required=True)
    verify_cmd.add_argument("--junit", type=Path, required=True)

    budget_cmd = sub.add_parser("budget", help="thresholds and attribution")
    budget_cmd.add_argument("--run-id", type=int, required=True)
    budget_cmd.add_argument(
        "--sweeps-required", choices=("true", "false"), required=True
    )
    budget_cmd.add_argument("--workflow", default="test-template.yml")
    budget_cmd.add_argument("--branch", default="main")
    budget_cmd.add_argument("--history", type=int, default=2)
    budget_cmd.add_argument("--cpu", action="append", help="KIND=CPU model")
    budget_cmd.add_argument("--executed", action="append", help="KIND=count")
    budget_cmd.add_argument("--budgets", type=Path, default=BUDGETS_FILE)

    release_cmd = sub.add_parser("release-evidence", help="release gate")
    release_cmd.add_argument("--sha", required=True)
    release_cmd.add_argument("--workflow", default="test-template.yml")
    release_cmd.add_argument("--budgets", type=Path, default=BUDGETS_FILE)
    args = parser.parse_args(argv)

    try:
        if args.command == "verify-sweep":
            return _run_verify(args, run, env, expected)
        if args.command == "budget":
            return _run_budget(args, run, env)
        return _run_release(args, run, env)
    except ReportError as exc:
        print(f"ERROR: {exc}")
        _annotate([str(exc)], env, "error")
        return 1


def _run_verify(
    args: argparse.Namespace,
    run: Runner,
    env: Mapping[str, str],
    expected: frozenset[str] | None,
) -> int:
    cases, others = parse_junit(args.junit.read_text(encoding="utf-8"), args.kind)
    evidence = verify(cases, others, expected or expected_slugs(), args.kind)
    lines = evidence_lines(evidence, cpu_model(run))
    _emit(lines, env, markdown=False)
    output = env.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(
                f"expected={evidence.expected}\nexecuted={evidence.executed}\n"
            )
    if not evidence.ok:
        _annotate([lines[-1].strip() + f" ({args.kind} sweep)"], env, "error")
    return 0 if evidence.ok else 1


def _run_budget(args: argparse.Namespace, run: Runner, env: Mapping[str, str]) -> int:
    budgets = load_budgets(args.budgets)
    current = fetch_jobs(args.run_id, run)
    history = [
        fetch_jobs(run_id, run)
        for run_id in recent_run_ids(
            args.workflow, args.branch, args.history, args.run_id, run
        )
    ]
    result = build_budget_report(
        current,
        history,
        budgets,
        sweeps_required=args.sweeps_required == "true",
        cpus=_pairs(args.cpu),
        executed=_pairs(args.executed),
    )
    _emit(result.lines, env, markdown=True)
    _annotate(result.problems, env, "error")
    return 0 if result.ok else 1


def _run_release(args: argparse.Namespace, run: Runner, env: Mapping[str, str]) -> int:
    budgets = load_budgets(args.budgets)
    ok, lines = check_release_evidence(args.sha, args.workflow, budgets, run)
    _emit(["Release evidence", *lines], env, markdown=False)
    if not ok:
        _annotate(lines[-1:], env, "error")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
