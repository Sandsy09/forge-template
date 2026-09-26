"""Audits this repository's locked dependencies for known vulnerabilities.

Wraps `uv audit` (preview; queries OSV) with the policy `uv audit` does not
have: a derived and cross-checked audit scope, fail-closed handling of a
changed tool interface, a clear split between a *clean* result, *findings*, an
*advisory-service outage* and a *tool error*, and reviewed, scoped, expiring
advisory exceptions. See docs/dependency-audit.md and ADR 0075.

Two audits run and are reported separately: the **runtime** graph (what the
published wheel depends on, so provider-actionable) and the **full** graph
(runtime plus every dependency group, CI-only additions).

Exit codes:
    0  clean, or an outage tolerated by `--on-outage warn` (NOT a clean result)
    1  unsuppressed findings, a tool error, scope or schema drift, an invalid
       exceptions file, or an outage under `--on-outage fail`

Usage:
    uv run poe audit
    uv run python scripts/audit_dependencies.py --on-outage warn
    uv run python scripts/audit_dependencies.py --project ../other-project
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCEPTIONS_FILE = REPO_ROOT / ".github" / "audit-exceptions.toml"

# `uv audit` is a preview command: both its interface and its JSON schema may
# change. Anything other than this exact schema version fails closed.
SCHEMA_VERSION = "preview"
_PREVIEW_FEATURES = "audit-command,json-output"

MAX_EXCEPTION_DAYS = 90
_EXCEPTION_KEYS = frozenset({"id", "package", "rationale", "owner", "added", "expires"})
_ADVISORY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# The only stderr text allowed to downgrade a failed run to a service outage.
# Every other failure is a tool error and always fails.
_OUTAGE_MARKERS = ("Request failed after", "error sending request")

_CREDENTIALS = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")


class AuditToolError(Exception):
    """The audit could not produce a trustworthy result (fails closed)."""


class ExceptionsError(AuditToolError):
    """`.github/audit-exceptions.toml` is invalid."""


@dataclass(frozen=True)
class Completed:
    """What a command run returned; the injected runner produces these."""

    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str], Path], Completed]


def subprocess_runner(command: Sequence[str], cwd: Path) -> Completed:
    """Run a command in `cwd`; the command is built here, never from input."""
    try:
        result = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise AuditToolError(f"cannot run {command[0]!r}: {exc}") from exc
    return Completed(result.returncode, result.stdout, result.stderr)


# ---------------------------------------------------------------------------
# Redaction and small helpers
# ---------------------------------------------------------------------------


def redact(text: str) -> str:
    """Strip `scheme://user:password@` credentials from any text we print."""
    return _CREDENTIALS.sub(r"\1***@", text)


def describe_service(url: str | None) -> str:
    """The advisory service as a host only: no userinfo, path or query."""
    if not url:
        return "uv default (OSV)"
    host = urlsplit(url).hostname
    return host or "custom endpoint"


def normalise(name: str) -> str:
    """PEP 503 name normalisation, so `Jinja2` and `jinja2` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _excerpt(text: str, lines: int = 4) -> str:
    kept = [redact(line.strip())[:300] for line in text.splitlines() if line.strip()]
    return " | ".join(kept[:lines])


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def read_groups(project: Path) -> list[str]:
    """Every dependency-group name declared in the project's pyproject."""
    document = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    groups = document.get("dependency-groups", {})
    if not isinstance(groups, dict):
        raise AuditToolError("[dependency-groups] in pyproject.toml is not a table")
    return sorted(groups)


def _scope_flags(excluded_groups: Sequence[str]) -> list[str]:
    # `uv audit --no-default-groups` and `--only-dev` do NOT narrow the audit
    # (uv 0.12.0 and 0.12.5 audit the whole lock regardless); only an explicit
    # `--no-group <name>` per group does. Hence the derived list, and the
    # cross-check against `uv export` below.
    return [flag for group in excluded_groups for flag in ("--no-group", group)]


def expected_package_count(
    project: Path, runner: Runner, excluded_groups: Sequence[str] | None
) -> int:
    """An independent, lock-only count of the packages an audit should cover.

    `uv export` narrows correctly where `uv audit`'s group flags do not, so it
    is an independent check that the audit's scope is what we asked for.
    `excluded_groups=None` means every group (the full graph).
    """
    command = [
        "uv",
        "export",
        "--locked",
        "--no-emit-project",
        "--no-hashes",
        "--format",
        "requirements-txt",
    ]
    command += (
        ["--all-groups"] if excluded_groups is None else _scope_flags(excluded_groups)
    )
    result = runner(command, project)
    if result.returncode != 0:
        raise AuditToolError(
            f"uv export failed (exit {result.returncode}): {_excerpt(result.stderr)}"
        )
    pinned = {
        line.split(";")[0].strip()
        for line in result.stdout.splitlines()
        if re.match(r"^[A-Za-z0-9]", line)
    }
    return len(pinned)


# ---------------------------------------------------------------------------
# Parsing `uv audit --output-format json`
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One vulnerability `uv audit` reported for a locked package."""

    id: str
    display_id: str
    aliases: tuple[str, ...]
    package: str
    version: str
    fix_versions: tuple[str, ...]
    summary: str
    link: str
    modified: str

    def identifiers(self) -> set[str]:
        """Every ID this advisory is known by (its own plus aliases)."""
        return {self.id, self.display_id, *self.aliases}

    def key(self) -> tuple[str, str, str]:
        """A stable identity, for matching a finding across two scopes."""
        return (normalise(self.package), self.version, self.id)


@dataclass(frozen=True)
class Report:
    """A validated `uv audit` JSON report."""

    audited_packages: int
    findings: tuple[Finding, ...]
    adverse_statuses: tuple[str, ...]


def _drift(message: str) -> AuditToolError:
    return AuditToolError(
        f"uv audit output changed ({message}); refusing to trust it. The audit "
        "fails closed on any interface drift (docs/dependency-audit.md)"
    )


def _require(mapping: Mapping[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in mapping or not isinstance(mapping[key], kind):
        raise _drift(f"{where} has no {kind.__name__} {key!r}")
    return mapping[key]


def _describe(mapping: Mapping[str, Any], key: str, where: str) -> str:
    """A descriptive field: always present, but OSV may leave it null."""
    if key not in mapping or not isinstance(mapping[key], str | None):
        raise _drift(f"{where} has no string-or-null {key!r}")
    return mapping[key] or ""


def parse_report(stdout: str) -> Report:
    """Parse and strictly validate `uv audit --output-format json` output."""
    try:
        document = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise _drift(f"not valid JSON: {exc.msg}") from exc
    if not isinstance(document, dict):
        raise _drift("top level is not an object")

    schema = _require(document, "schema", dict, "report")
    if schema.get("version") != SCHEMA_VERSION:
        raise _drift(f"schema version {schema.get('version')!r}, expected 'preview'")

    summary = _require(document, "summary", dict, "report")
    audited = _require(summary, "audited_packages", int, "summary")
    counted = _require(summary, "vulnerabilities", int, "summary")
    _require(summary, "adverse_statuses", int, "summary")

    raw_findings = _require(document, "vulnerabilities", list, "report")
    raw_adverse = _require(document, "adverse_statuses", list, "report")
    if counted != len(raw_findings):
        raise _drift("summary count differs from the listed vulnerabilities")

    findings: list[Finding] = []
    for entry in raw_findings:
        if not isinstance(entry, dict):
            raise _drift("a vulnerability entry is not an object")
        dependency = _require(entry, "dependency", dict, "vulnerability")
        aliases = _require(entry, "aliases", list, "vulnerability")
        fixes = _require(entry, "fix_versions", list, "vulnerability")
        findings.append(
            Finding(
                id=_require(entry, "id", str, "vulnerability"),
                display_id=_require(entry, "display_id", str, "vulnerability"),
                aliases=tuple(str(alias) for alias in aliases),
                package=_require(dependency, "name", str, "dependency"),
                version=_require(dependency, "version", str, "dependency"),
                fix_versions=tuple(str(fix) for fix in fixes),
                summary=_describe(entry, "summary", "vulnerability")
                or "(no summary published)",
                link=_describe(entry, "link", "vulnerability"),
                modified=_describe(entry, "modified", "vulnerability"),
            )
        )
    # adverse_statuses entries have no observed schema: keep them opaque.
    adverse = tuple(json.dumps(item, sort_keys=True)[:300] for item in raw_adverse)
    return Report(audited, tuple(findings), adverse)


def classify_failure(returncode: int, stderr: str) -> str:
    """`outage` only for recognised connection text, else `tool` (fail-closed)."""
    if returncode == 2 and any(marker in stderr for marker in _OUTAGE_MARKERS):
        return "outage"
    return "tool"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditException:
    """A reviewed, scoped, expiring advisory exception."""

    id: str
    package: str
    rationale: str
    owner: str
    added: date
    expires: date

    def matches(self, finding: Finding) -> bool:
        """Whether this exception is for this finding: same package and ID."""
        return self.package == normalise(finding.package) and (
            self.id in finding.identifiers()
        )

    def expired(self, today: date) -> bool:
        """Whether `today` is past the last day the exception applies."""
        # `expires` is the last day the exception applies.
        return today > self.expires


def load_exceptions(path: Path, today: date) -> list[AuditException]:
    """Load and strictly validate the reviewed-exceptions file (fail closed)."""
    if not path.is_file():
        return []
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ExceptionsError(f"{path.name}: invalid TOML: {exc}") from exc

    unknown_top = set(document) - {"exception"}
    if unknown_top:
        raise ExceptionsError(
            f"{path.name}: unknown top-level keys {sorted(unknown_top)}"
        )
    entries = document.get("exception", [])
    if not isinstance(entries, list):
        raise ExceptionsError(f"{path.name}: `exception` must be an array of tables")

    loaded: list[AuditException] = []
    for index, entry in enumerate(entries, start=1):
        where = f"{path.name}: exception #{index}"
        if not isinstance(entry, dict):
            raise ExceptionsError(f"{where} is not a table")
        unknown = set(entry) - _EXCEPTION_KEYS
        missing = _EXCEPTION_KEYS - set(entry)
        if unknown or missing:
            raise ExceptionsError(
                f"{where}: unknown keys {sorted(unknown)}, "
                f"missing keys {sorted(missing)}"
            )
        for key in ("id", "package", "rationale", "owner"):
            if not isinstance(entry[key], str) or not entry[key].strip():
                raise ExceptionsError(f"{where}: `{key}` must be a non-empty string")
        for key in ("added", "expires"):
            if not isinstance(entry[key], date) or isinstance(entry[key], datetime):
                raise ExceptionsError(f"{where}: `{key}` must be a TOML date")

        if not _ADVISORY_ID.match(entry["id"]):
            raise ExceptionsError(
                f"{where}: `id` must be one literal advisory ID or alias, no wildcards"
            )
        if any(char in entry["package"] for char in "*?[]<>=, "):
            raise ExceptionsError(
                f"{where}: `package` must be one literal package name, no wildcards"
            )
        added, expires = entry["added"], entry["expires"]
        if added > today:
            raise ExceptionsError(f"{where}: `added` is in the future")
        if expires < added:
            raise ExceptionsError(f"{where}: `expires` is before `added`")
        if (expires - added).days > MAX_EXCEPTION_DAYS:
            raise ExceptionsError(
                f"{where}: lifetime {(expires - added).days} days exceeds the "
                f"{MAX_EXCEPTION_DAYS}-day maximum; re-review and renew instead"
            )
        loaded.append(
            AuditException(
                id=entry["id"],
                package=normalise(entry["package"]),
                rationale=entry["rationale"].strip(),
                owner=entry["owner"].strip(),
                added=added,
                expires=expires,
            )
        )
    return loaded


@dataclass
class Applied:
    """The result of applying exceptions to one scope's findings."""

    unsuppressed: list[Finding] = field(default_factory=list)
    suppressed: list[tuple[Finding, AuditException]] = field(default_factory=list)
    expired: list[tuple[Finding, AuditException]] = field(default_factory=list)


def apply_exceptions(
    findings: Sequence[Finding], exceptions: Sequence[AuditException], today: date
) -> Applied:
    """Split findings into unsuppressed, suppressed and expired-exception."""
    applied = Applied()
    for finding in findings:
        matching = [exc for exc in exceptions if exc.matches(finding)]
        active = [exc for exc in matching if not exc.expired(today)]
        if active:
            applied.suppressed.append((finding, active[0]))
            continue
        applied.unsuppressed.append(finding)
        if matching:
            applied.expired.append((finding, matching[0]))
    return applied


def stale_exceptions(
    exceptions: Sequence[AuditException], findings: Sequence[Finding]
) -> list[AuditException]:
    """Exceptions that match no current finding and should be removed."""
    return [
        exc for exc in exceptions if not any(exc.matches(found) for found in findings)
    ]


# ---------------------------------------------------------------------------
# One audit scope
# ---------------------------------------------------------------------------


@dataclass
class ScopeResult:
    """The outcome of auditing one scope (runtime or full)."""

    label: str
    status: str  # clean | findings | outage | tool-error
    message: str = ""
    report: Report | None = None
    expected: int | None = None


def audit_scope(
    label: str,
    project: Path,
    runner: Runner,
    excluded_groups: Sequence[str] | None,
    service_url: str | None,
) -> ScopeResult:
    """Audit one scope and cross-check that it covered what we asked for."""
    result = ScopeResult(label, "tool-error")
    try:
        result.expected = expected_package_count(project, runner, excluded_groups)
        command = [
            "uv",
            "audit",
            "--locked",
            "--preview-features",
            _PREVIEW_FEATURES,
            "--output-format",
            "json",
            *_scope_flags(excluded_groups or []),
        ]
        if service_url:
            command += ["--service-url", service_url]
        run = runner(command, project)

        if run.returncode not in (0, 1):
            kind = classify_failure(run.returncode, run.stderr)
            result.status = "outage" if kind == "outage" else "tool-error"
            result.message = (
                f"advisory service unreachable: {_excerpt(run.stderr)}"
                if kind == "outage"
                else f"uv audit exited {run.returncode}: {_excerpt(run.stderr)}"
            )
            return result

        report = parse_report(run.stdout)
        result.report = report
        if report.audited_packages != result.expected:
            raise AuditToolError(
                f"audit scope drift: the {label} audit covered "
                f"{report.audited_packages} packages but the lock has "
                f"{result.expected} in that scope"
            )
        if run.returncode == 0 and report.findings:
            raise _drift("exit 0 but vulnerabilities were listed")
        if run.returncode == 1 and not report.findings:
            raise _drift("exit 1 but no vulnerabilities were listed")
        result.status = "findings" if report.findings else "clean"
    except AuditToolError as exc:
        result.status = "tool-error"
        result.message = redact(str(exc))
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _remediation(finding: Finding, scope: str) -> str:
    package = normalise(finding.package)
    if not finding.fix_versions:
        return (
            "no fixed version is published: add a reviewed, expiring exception "
            "to .github/audit-exceptions.toml, or replace the dependency"
        )
    fixed = ", ".join(finding.fix_versions)
    text = f"fixed in {fixed}: `uv lock --upgrade-package {package}`"
    if scope == "runtime":
        text += (
            "; then review whether the declared floor in pyproject.toml still "
            "permits a vulnerable version (docs/dependency-audit.md)"
        )
    return text


@dataclass
class Outcome:
    """The rendered result: exit code, report lines, CI annotations."""

    exit_code: int
    lines: list[str]
    annotations: list[str]


def build_outcome(
    *,
    scanner: str,
    service: str,
    queried: str,
    results: Sequence[ScopeResult],
    exceptions: Sequence[AuditException],
    on_outage: str,
    today: date,
) -> Outcome:
    """Render every scope into one report and decide the exit code."""
    lines = [
        "Dependency audit (docs/dependency-audit.md)",
        f"  scanner:  {scanner}",
        f"  service:  {service}",
        f"  queried:  {queried}",
        "  advisory data: live OSV lookup; no snapshot version exists, so each "
        "finding records its advisory `modified` time",
    ]
    annotations: list[str] = []
    failed = False
    all_findings: list[Finding] = []
    runtime_keys: set[tuple[str, str, str]] = set()

    for result in results:
        counts = (
            f"{result.report.audited_packages} packages"
            if result.report
            else "not completed"
        )
        lines.append("")
        lines.append(f"[{result.label}] {counts} audited: {result.status}")

        if result.status == "tool-error":
            failed = True
            lines.append(f"  ERROR: {result.message}")
            annotations.append(f"::error::[{result.label}] {result.message}")
            continue
        if result.status == "outage":
            lines.append(f"  NOT A CLEAN RESULT: {result.message}")
            if on_outage == "fail":
                failed = True
                annotations.append(
                    f"::error::[{result.label}] advisory service outage: no audit "
                    "result (--on-outage fail)"
                )
            else:
                annotations.append(
                    f"::warning::[{result.label}] advisory service outage: the "
                    "dependency audit did NOT run and is not a clean result "
                    "(--on-outage warn)"
                )
            continue
        assert result.report is not None
        scoped = [
            found
            for found in result.report.findings
            if result.label == "runtime" or found.key() not in runtime_keys
        ]
        if result.label == "runtime":
            runtime_keys = {found.key() for found in result.report.findings}
        all_findings += result.report.findings

        applied = apply_exceptions(scoped, exceptions, today)
        for found, exc in applied.suppressed:
            lines.append(
                f"  suppressed {found.display_id} in {found.package} "
                f"{found.version} by an exception owned by {exc.owner}, "
                f"expires {exc.expires.isoformat()}: {exc.rationale}"
            )
        expired_by_finding = {id(found): exc for found, exc in applied.expired}
        for found in applied.unsuppressed:
            failed = True
            lines.append(
                f"  FINDING {found.display_id} in {found.package} {found.version}"
                f" [{result.label}]: {found.summary}"
            )
            aliases = ", ".join(a for a in found.aliases if a != found.display_id)
            if aliases:
                lines.append(f"    aliases: {aliases}")
            lines.append(f"    {_remediation(found, result.label)}")
            lines.append(f"    advisory: {found.link} (modified {found.modified})")
            lapsed = expired_by_finding.get(id(found))
            if lapsed is not None:
                lines.append(
                    f"    an exception for this finding EXPIRED on "
                    f"{lapsed.expires.isoformat()} and no longer applies: "
                    "re-review it or fix the dependency"
                )
            annotations.append(
                f"::error::{found.display_id} in {found.package} {found.version}: "
                f"{found.summary}"
            )
        for status in result.report.adverse_statuses:
            lines.append(f"  adverse status (warning): {status}")
            annotations.append(f"::warning::adverse dependency status: {status}")

    # Staleness is only knowable when every scope actually completed.
    completed = all(r.status in ("clean", "findings") for r in results)
    for exc in stale_exceptions(exceptions, all_findings) if completed else []:
        lines.append(
            f"  stale exception (warning): {exc.id} for {exc.package} matches no "
            "current finding; remove it"
        )
        annotations.append(
            f"::warning::stale audit exception {exc.id} for {exc.package}"
        )

    lines.append("")
    if failed:
        lines.append("RESULT: FAILED")
    elif any(r.status == "outage" for r in results):
        lines.append("RESULT: NOT CLEAN - advisory service outage tolerated (warn)")
    else:
        lines.append(
            "RESULT: no unsuppressed known vulnerabilities. This is not a claim "
            "that the dependencies are secure."
        )
    return Outcome(1 if failed else 0, lines, annotations)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    today: date | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Run the audit; the runner, date and environment are injectable."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--project", type=Path, default=REPO_ROOT, help="project to audit"
    )
    parser.add_argument(
        "--on-outage",
        choices=("warn", "fail"),
        default="fail",
        help="an unreachable advisory service: warn (exit 0, loudly) or fail",
    )
    parser.add_argument("--service-url", help="advisory service endpoint override")
    parser.add_argument(
        "--exceptions", type=Path, default=EXCEPTIONS_FILE, help="exceptions file"
    )
    args = parser.parse_args(argv)

    run = runner or subprocess_runner
    env = environ if environ is not None else os.environ
    day = today or datetime.now(UTC).date()
    project = args.project.resolve()

    try:
        exceptions = load_exceptions(args.exceptions, day)
        version = run(["uv", "--version"], project)
        scanner = redact(version.stdout.strip() or "uv (version unknown)")
        groups = read_groups(project)
        results = [audit_scope("runtime", project, run, groups, args.service_url)]
        if results[0].status != "outage":
            results.append(audit_scope("full", project, run, None, args.service_url))
        outcome = build_outcome(
            scanner=scanner,
            service=describe_service(args.service_url),
            queried=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            results=results,
            exceptions=exceptions,
            on_outage=args.on_outage,
            today=day,
        )
    except AuditToolError as exc:
        message = redact(str(exc))
        print(f"ERROR: {message}")
        if env.get("GITHUB_ACTIONS") == "true":
            print(f"::error::{message}")
        return 1

    print("\n".join(outcome.lines))
    if env.get("GITHUB_ACTIONS") == "true":
        print("\n".join(outcome.annotations))
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write("## Dependency audit\n\n```text\n")
            handle.write("\n".join(outcome.lines))
            handle.write("\n```\n")
    return outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())
