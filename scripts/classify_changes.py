"""Decides whether a change requires the exhaustive composition sweeps.

FT-26.02 / ADR 0077. The sweeps (tiers T2 and T3 of docs/validation-budget.md)
always run on `push`, `schedule` and `workflow_dispatch`. A pull request runs
them only when it changes a composition-sensitive path, as defined by the
`[escalation]` table in `.github/validation-budgets.toml`.

The decision **fails closed**: anything that stops the script proving a pull
request insensitive (an unreadable budgets file, a git failure, an empty diff,
an unrecognised event) requires the sweeps, with the reason recorded.

Usage:
    uv run python scripts/classify_changes.py --event pull_request --base main
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BUDGETS_FILE = REPO_ROOT / ".github" / "validation-budgets.toml"

# Events on which the exhaustive tier is never skipped.
ALWAYS_EVENTS = frozenset({"push", "schedule", "workflow_dispatch"})

Runner = Callable[[Sequence[str]], str]


class ClassifyError(Exception):
    """The change could not be classified; the caller must fail closed."""


@dataclass(frozen=True)
class Decision:
    """Whether the sweeps are required, and why."""

    sweeps: bool
    reason: str


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
        raise ClassifyError(f"cannot run {command[0]!r}: {exc}") from exc
    if result.returncode != 0:
        raise ClassifyError(
            f"{' '.join(command[:3])} failed: {result.stderr.strip()[:300]}"
        )
    return result.stdout


def load_escalation(path: Path) -> dict[str, Any]:
    """The `[escalation]` table of the budgets file, validated."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ClassifyError(f"cannot read {path.name}: {exc}") from exc
    escalation = document.get("escalation")
    if not isinstance(escalation, dict):
        raise ClassifyError(f"{path.name} has no [escalation] table")
    for key in ("sensitive_paths", "excluded_paths"):
        value = escalation.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ClassifyError(f"[escalation].{key} must be a list of strings")
    if not escalation["sensitive_paths"]:
        raise ClassifyError("[escalation].sensitive_paths is empty")
    return escalation


def is_sensitive(path: str, escalation: Mapping[str, Any]) -> bool:
    """Whether a change to `path` requires the exhaustive sweeps."""
    if path in escalation["excluded_paths"]:
        return False
    return any(fnmatch(path, pattern) for pattern in escalation["sensitive_paths"])


def changed_files(base: str, head: str, runner: Runner) -> list[str]:
    """The files a pull request changes relative to its base."""
    output = runner(["git", "diff", "--name-only", f"{base}...{head}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def decide(
    event: str,
    base: str | None,
    head: str | None,
    budgets: Path,
    runner: Runner,
) -> Decision:
    """Whether this event and change require the exhaustive sweeps."""
    if event in ALWAYS_EVENTS:
        return Decision(True, f"a {event} event always runs the exhaustive tier")
    if event != "pull_request":
        return Decision(
            True, f"fail-closed: unrecognised event {event!r} requires the sweeps"
        )
    try:
        if not base or not head:
            raise ClassifyError("a pull request needs --base and --head")
        escalation = load_escalation(budgets)
        files = changed_files(base, head, runner)
        if not files:
            raise ClassifyError(
                "no changed files were found, so insensitivity cannot be proved"
            )
    except ClassifyError as exc:
        return Decision(True, f"fail-closed: {exc}")

    sensitive = [path for path in files if is_sensitive(path, escalation)]
    if sensitive:
        shown = ", ".join(sensitive[:3])
        more = f" (+{len(sensitive) - 3} more)" if len(sensitive) > 3 else ""
        return Decision(
            True,
            f"{len(sensitive)} of {len(files)} changed files are "
            f"composition-sensitive: {shown}{more}",
        )
    return Decision(
        False,
        f"none of the {len(files)} changed files is composition-sensitive; the "
        "sweeps still run on main, weekly, on dispatch and before a release",
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Classify the change, print the decision and publish it to the workflow."""
    env = environ if environ is not None else os.environ
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--event", default=env.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--base", help="the pull request's base commit or ref")
    parser.add_argument("--head", help="the pull request's head commit or ref")
    parser.add_argument("--budgets", type=Path, default=BUDGETS_FILE)
    args = parser.parse_args(argv)

    decision = decide(
        args.event, args.base, args.head, args.budgets, runner or default_runner
    )
    verdict = "REQUIRED" if decision.sweeps else "NOT REQUIRED"
    print(f"exhaustive sweeps: {verdict}\n  event: {args.event}\n  {decision.reason}")

    output = env.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"sweeps={'true' if decision.sweeps else 'false'}\n")
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(
                f"## Change classification\n\nExhaustive sweeps: **{verdict}**"
                f" ({args.event})\n\n{decision.reason}\n"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
