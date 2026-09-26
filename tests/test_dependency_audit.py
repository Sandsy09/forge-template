"""The dependency-vulnerability audit (FT-24.02, ADR 0075), executably.

`scripts/audit_dependencies.py` wraps the preview `uv audit`. Every test drives
its `main()` through an injected runner, so none needs the network or a real
`uv`. The JSON fixtures under `tests/fixtures/dependency_audit/` are real
`uv audit` 0.12.0 output (a clean run of this repository, and a probe project
pinned to vulnerable `jinja2` and `urllib3`), with the vulnerability list cut
to two entries and long advisory descriptions truncated -- so a change to uv's
JSON shape shows up here rather than in production.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = ROOT / "tests" / "fixtures" / "dependency_audit"
_TODAY = date(2026, 9, 26)


def _load_script() -> Any:
    path = ROOT / "scripts" / "audit_dependencies.py"
    spec = importlib.util.spec_from_file_location("audit_dependencies", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["audit_dependencies"] = module
    spec.loader.exec_module(module)
    return module


audit = _load_script()

CLEAN = json.loads((_FIXTURES / "clean.json").read_text(encoding="utf-8"))
VULNERABLE = json.loads((_FIXTURES / "vulnerable.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _report(base: dict[str, Any], audited: int) -> dict[str, Any]:
    document = copy.deepcopy(base)
    document["summary"]["audited_packages"] = audited
    return document


CLEAN3 = _report(CLEAN, 3)  # matches the Fake's default expected scope size


def _completed(code: int, document: Any = None, stderr: str = "") -> Any:
    stdout = "" if document is None else json.dumps(document)
    return audit.Completed(code, stdout, stderr)


def _pins(count: int) -> str:
    lines = [f"pkg{i}==1.0.{i} ; sys_platform == 'linux'" for i in range(count)]
    return "# comment\n" + "\n".join(lines) + "\n    # via something\n"


class Fake:
    """A scripted `uv`: answers `--version`, `export` and `audit` per scope."""

    def __init__(
        self,
        *,
        runtime: Any,
        full: Any,
        runtime_count: int = 3,
        full_count: int = 3,
        export_error: bool = False,
    ) -> None:
        self.runtime, self.full = runtime, full
        self.counts = {"runtime": runtime_count, "full": full_count}
        self.export_error = export_error
        self.commands: list[list[str]] = []

    def __call__(self, command: Sequence[str], cwd: Path) -> Any:
        command = list(command)
        self.commands.append(command)
        if command[1] == "--version":
            return audit.Completed(0, "uv 0.12.0 (test build)\n", "")
        scope = "runtime" if "--no-group" in command else "full"
        if command[1] == "export":
            if self.export_error:
                return audit.Completed(2, "", "error: could not export")
            return audit.Completed(0, _pins(self.counts[scope]), "")
        assert command[1] == "audit", command
        return self.runtime if scope == "runtime" else self.full

    def audits(self) -> list[list[str]]:
        return [c for c in self.commands if c[1] == "audit"]

    def exports(self) -> list[list[str]]:
        return [c for c in self.commands if c[1] == "export"]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'x'\nversion = '0'\n\n"
        "[dependency-groups]\nlint = []\ntest = []\ndev = []\n",
        encoding="utf-8",
    )
    return tmp_path


def _run(
    project: Path,
    fake: Fake,
    *args: str,
    exceptions: str | None = None,
    environ: dict[str, str] | None = None,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str]:
    path = project / "exceptions.toml"
    if exceptions is not None:
        path.write_text(exceptions, encoding="utf-8")
    code = audit.main(
        ["--project", str(project), "--exceptions", str(path), *args],
        runner=fake,
        today=_TODAY,
        environ=environ or {},
    )
    return code, capsys.readouterr().out


def _exception(**overrides: str) -> str:
    fields = {
        "id": "GHSA-cpwx-vrp4-4pq7",
        "package": "jinja2",
        "rationale": "'no untrusted templates are rendered'",
        "owner": "'maintainer'",
        "added": "2026-09-20",
        "expires": "2026-10-20",
    }
    fields.update(overrides)
    rows = [
        f"{key} = '{value}'"
        if key in ("id", "package") and not value.startswith("'")
        else f"{key} = {value}"
        for key, value in fields.items()
    ]
    return "[[exception]]\n" + "\n".join(rows) + "\n"


def _clean_fake() -> Fake:
    return Fake(runtime=_completed(0, CLEAN3), full=_completed(0, CLEAN3))


def _vulnerable_fake() -> Fake:
    return Fake(runtime=_completed(1, VULNERABLE), full=_completed(1, VULNERABLE))


_OUTAGE = (
    "error: Request failed after 3 retries\n"
    "  Caused by: error sending request for url (https://osv.example/v1)\n"
)


# ---------------------------------------------------------------------------
# Clean, vulnerable, exceptions
# ---------------------------------------------------------------------------


def test_clean_run_passes_and_records_versions(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = Fake(
        runtime=_completed(0, _report(CLEAN, 3)),
        full=_completed(0, _report(CLEAN, 5)),
        full_count=5,
    )
    code, out = _run(project, fake, capsys=capsys)
    assert code == 0, out
    assert "scanner:  uv 0.12.0 (test build)" in out
    assert "service:  uv default (OSV)" in out
    assert "queried:  20" in out
    assert "[runtime] 3 packages audited: clean" in out
    assert "[full] 5 packages audited: clean" in out
    assert "not a claim that the dependencies are secure" in out


def test_audit_scope_flags_are_derived_from_the_declared_groups(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = _clean_fake()
    _run(project, fake, capsys=capsys)
    runtime, full = fake.audits()
    for command in (runtime, full):
        assert command[:3] == ["uv", "audit", "--locked"]
        assert "--preview-features" in command
    # Sorted, one --no-group per declared group; --no-default-groups is never
    # used because uv 0.12 silently ignores it.
    assert "--no-group dev --no-group lint --no-group test" in " ".join(runtime)
    assert "--no-group" not in full
    assert "--no-default-groups" not in runtime + full
    runtime_export, full_export = fake.exports()
    assert "--no-group" in runtime_export and "--all-groups" not in runtime_export
    assert "--all-groups" in full_export


def test_a_new_group_narrows_the_runtime_audit_automatically(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / "pyproject.toml").write_text(
        "[project]\nname = 'x'\nversion = '0'\n\n"
        "[dependency-groups]\ndocs = []\nlint = []\n",
        encoding="utf-8",
    )
    fake = _clean_fake()
    _run(project, fake, capsys=capsys)
    assert "--no-group docs --no-group lint" in " ".join(fake.audits()[0])


def test_vulnerable_run_fails_actionably(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(project, _vulnerable_fake(), capsys=capsys)
    assert code == 1
    assert "FINDING GHSA-cpwx-vrp4-4pq7 in jinja2 3.1.2 [runtime]" in out
    assert "aliases: CVE-2025-27516, PYSEC-2026-1471" in out
    assert "fixed in 3.1.6: `uv lock --upgrade-package jinja2`" in out
    assert "declared floor in pyproject.toml" in out  # lower-bound review, runtime
    assert "urllib3 1.26.4" in out
    # A real entry with a null summary and two fix versions (1.26.x and 2.x).
    assert "(no summary published)" in out
    assert "fixed in 2.0.6, 1.26.17" in out
    assert "RESULT: FAILED" in out


def test_findings_are_listed_once_across_scopes(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, out = _run(project, _vulnerable_fake(), capsys=capsys)
    assert out.count("FINDING GHSA-cpwx-vrp4-4pq7") == 1
    assert out.count("FINDING PYSEC-2023-192") == 1


def test_a_development_only_finding_is_labelled_and_has_no_floor_hint(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = Fake(
        runtime=_completed(0, _report(CLEAN, 3)),
        full=_completed(1, VULNERABLE),
    )
    code, out = _run(project, fake, capsys=capsys)
    assert code == 1
    assert "jinja2 3.1.2 [full]" in out
    assert "declared floor" not in out


def test_a_finding_with_no_fixed_version_still_fails_with_a_clear_message(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    unfixed = copy.deepcopy(VULNERABLE)
    for entry in unfixed["vulnerabilities"]:
        entry["fix_versions"] = []
    fake = Fake(runtime=_completed(1, unfixed), full=_completed(1, unfixed))
    code, out = _run(project, fake, capsys=capsys)
    assert code == 1
    assert "no fixed version is published" in out
    assert ".github/audit-exceptions.toml" in out


def test_reviewed_exceptions_suppress_by_id_or_alias(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The second is suppressed through an alias (`CVE-2023-43804`), not its ID.
    exceptions = _exception() + _exception(id="CVE-2023-43804", package="urllib3")
    # The alias form: a CVE listed among the finding's aliases.
    code, out = _run(project, _vulnerable_fake(), exceptions=exceptions, capsys=capsys)
    assert code == 0, out
    assert "suppressed GHSA-cpwx-vrp4-4pq7 in jinja2 3.1.2" in out
    assert "owned by maintainer" in out
    assert "no untrusted templates are rendered" in out
    assert "FINDING" not in out


def test_an_exception_for_another_package_does_not_suppress(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(
        project,
        _vulnerable_fake(),
        exceptions=_exception(package="requests"),
        capsys=capsys,
    )
    assert code == 1
    assert "FINDING GHSA-cpwx-vrp4-4pq7" in out


def test_an_expired_exception_stops_suppressing_and_says_so(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    expired = _exception(added="2026-06-01", expires="2026-08-30")
    code, out = _run(project, _vulnerable_fake(), exceptions=expired, capsys=capsys)
    assert code == 1
    assert "FINDING GHSA-cpwx-vrp4-4pq7" in out
    assert "EXPIRED on 2026-08-30" in out


def test_expiry_is_the_last_day_the_exception_applies(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    only_jinja = copy.deepcopy(VULNERABLE)
    only_jinja["vulnerabilities"] = only_jinja["vulnerabilities"][:1]
    only_jinja["summary"]["vulnerabilities"] = 1
    fake = Fake(runtime=_completed(1, only_jinja), full=_completed(1, only_jinja))
    last_day = _exception(added="2026-08-01", expires="2026-09-26")
    code, out = _run(project, fake, exceptions=last_day, capsys=capsys)
    assert code == 0, out


def test_a_stale_exception_warns_but_does_not_fail(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(
        project,
        _clean_fake(),
        exceptions=_exception(),
        environ={"GITHUB_ACTIONS": "true"},
        capsys=capsys,
    )
    assert code == 0
    assert "stale exception (warning): GHSA-cpwx-vrp4-4pq7" in out
    assert "::warning::stale audit exception" in out


def test_an_absent_exceptions_file_means_no_exceptions(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(project, _clean_fake(), capsys=capsys)
    assert code == 0, out


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (
            _exception().replace("owner = 'maintainer'", "colour = 'red'"),
            "unknown keys",
        ),
        (_exception().replace("owner = 'maintainer'\n", ""), "missing keys"),
        (_exception(expires="2027-06-01"), "exceeds the 90-day maximum"),
        (_exception(added="2026-09-20", expires="2026-09-01"), "before `added`"),
        (_exception(added="2026-10-01", expires="2026-10-20"), "in the future"),
        (_exception(id="GHSA-*"), "no wildcards"),
        (_exception(package="jinja*"), "no wildcards"),
        (_exception(rationale="'  '"), "non-empty string"),
        (_exception(expires="'2026-10-20'"), "must be a TOML date"),
        ("[[exception]\n", "invalid TOML"),
        ("surprise = 1\n", "unknown top-level keys"),
    ],
)
def test_an_invalid_exceptions_file_fails_closed(
    project: Path,
    capsys: pytest.CaptureFixture[str],
    document: str,
    message: str,
) -> None:
    code, out = _run(project, _clean_fake(), exceptions=document, capsys=capsys)
    assert code == 1
    assert message in out


# ---------------------------------------------------------------------------
# Advisory-service outage vs tool errors
# ---------------------------------------------------------------------------


def test_an_outage_under_warn_is_loud_and_not_a_clean_result(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = Fake(runtime=_completed(2, stderr=_OUTAGE), full=_completed(0, CLEAN3))
    code, out = _run(
        project,
        fake,
        "--on-outage",
        "warn",
        environ={"GITHUB_ACTIONS": "true"},
        capsys=capsys,
    )
    assert code == 0
    assert "NOT A CLEAN RESULT" in out
    assert "RESULT: NOT CLEAN" in out
    assert "no unsuppressed known vulnerabilities" not in out
    assert "::warning::" in out and "did NOT run" in out
    assert len(fake.audits()) == 1, "a down service is not queried twice"


def test_an_outage_under_fail_fails(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = Fake(runtime=_completed(2, stderr=_OUTAGE), full=_completed(0, CLEAN3))
    code, out = _run(
        project,
        fake,
        "--on-outage",
        "fail",
        environ={"GITHUB_ACTIONS": "true"},
        capsys=capsys,
    )
    assert code == 1
    assert "::error::" in out and "--on-outage fail" in out


def test_outage_handling_defaults_to_fail(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = Fake(runtime=_completed(2, stderr=_OUTAGE), full=_completed(0, CLEAN3))
    code, _ = _run(project, fake, capsys=capsys)
    assert code == 1


@pytest.mark.parametrize(
    "stderr",
    [
        "error: The lockfile at `uv.lock` needs to be updated, but `--locked`"
        " was provided.\n",
        "error: something uv has not said before\n",
        "",
    ],
)
def test_any_other_failure_is_a_tool_error_even_under_warn(
    project: Path, capsys: pytest.CaptureFixture[str], stderr: str
) -> None:
    fake = Fake(runtime=_completed(2, stderr=stderr), full=_completed(0, CLEAN3))
    code, out = _run(project, fake, "--on-outage", "warn", capsys=capsys)
    assert code == 1
    assert "ERROR: uv audit exited 2" in out
    assert "NOT CLEAN" not in out


def test_an_unexpected_exit_code_is_a_tool_error(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = Fake(runtime=_completed(101, stderr="panic"), full=_completed(0, CLEAN3))
    code, out = _run(project, fake, "--on-outage", "warn", capsys=capsys)
    assert code == 1
    assert "uv audit exited 101" in out


def test_a_failing_export_cross_check_is_a_tool_error(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = _clean_fake()
    fake.export_error = True
    code, out = _run(project, fake, capsys=capsys)
    assert code == 1
    assert "uv export failed" in out


# ---------------------------------------------------------------------------
# Fail-closed on interface and scope drift
# ---------------------------------------------------------------------------


def _drifted(mutate: Any) -> dict[str, Any]:
    document = _report(CLEAN, 3)
    mutate(document)
    return document


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["schema"].update(version="v2"),
        lambda d: d.pop("summary"),
        lambda d: d["summary"].pop("audited_packages"),
        lambda d: d.pop("vulnerabilities"),
        lambda d: d.pop("adverse_statuses"),
        lambda d: d["summary"].update(vulnerabilities=4),
        lambda d: d.update(schema=[]),
    ],
)
def test_schema_drift_fails_closed(
    project: Path, capsys: pytest.CaptureFixture[str], mutate: Any
) -> None:
    fake = Fake(runtime=_completed(0, _drifted(mutate)), full=_completed(0, CLEAN3))
    code, out = _run(project, fake, capsys=capsys)
    assert code == 1
    assert "uv audit output changed" in out
    assert "refusing to trust it" in out


def test_a_vulnerability_entry_missing_a_key_fails_closed(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = copy.deepcopy(VULNERABLE)
    del broken["vulnerabilities"][0]["fix_versions"]
    fake = Fake(runtime=_completed(1, broken), full=_completed(1, broken))
    code, out = _run(project, fake, capsys=capsys)
    assert code == 1
    assert "fix_versions" in out


def test_malformed_json_fails_closed(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = Fake(
        runtime=audit.Completed(0, "Found no known vulnerabilities", ""),
        full=_completed(0, CLEAN3),
    )
    code, out = _run(project, fake, capsys=capsys)
    assert code == 1
    assert "not valid JSON" in out


def test_exit_code_and_report_must_agree(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for code_, document in ((0, VULNERABLE), (1, _report(CLEAN, 3))):
        fake = Fake(runtime=_completed(code_, document), full=_completed(0, CLEAN3))
        code, out = _run(project, fake, capsys=capsys)
        assert code == 1
        assert "uv audit output changed" in out


def test_scope_drift_fails_closed(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The failure `--no-default-groups` would cause: a 'runtime' audit that
    silently covered the whole lock (79 packages, not 8)."""
    fake = Fake(
        runtime=_completed(0, _report(CLEAN, 79)),
        full=_completed(0, _report(CLEAN, 79)),
        runtime_count=8,
        full_count=79,
    )
    code, out = _run(project, fake, capsys=capsys)
    assert code == 1
    assert "audit scope drift" in out
    assert "runtime audit covered 79 packages but the lock has 8" in out


def test_adverse_statuses_warn_but_never_fail(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    deprecated = _report(CLEAN, 3)
    deprecated["adverse_statuses"] = [{"package": "old", "status": "deprecated"}]
    deprecated["summary"]["adverse_statuses"] = 1
    fake = Fake(runtime=_completed(0, deprecated), full=_completed(0, deprecated))
    code, out = _run(project, fake, environ={"GITHUB_ACTIONS": "true"}, capsys=capsys)
    assert code == 0
    assert "adverse status (warning)" in out
    assert "::warning::adverse dependency status" in out


# ---------------------------------------------------------------------------
# No credential-bearing output; step summary
# ---------------------------------------------------------------------------


def test_credentials_never_reach_the_output(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    leaky = "error: bad index https://user:s3cret@example.org/simple\n"
    fake = Fake(runtime=_completed(2, stderr=leaky), full=_completed(0, CLEAN3))
    code, out = _run(
        project,
        fake,
        "--service-url",
        "https://svc-user:hunter2@osv.example/v1?token=abc",
        capsys=capsys,
    )
    assert code == 1
    assert "s3cret" not in out and "hunter2" not in out and "token=abc" not in out
    assert "service:  osv.example" in out
    assert "https://***@example.org" in out


def test_the_service_override_is_passed_to_uv(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = _clean_fake()
    _run(project, fake, "--service-url", "https://osv.example/v1", capsys=capsys)
    for command in fake.audits():
        assert command[-2:] == ["--service-url", "https://osv.example/v1"]


def test_the_report_is_appended_to_the_github_step_summary(
    project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    code, _ = _run(
        project,
        _vulnerable_fake(),
        environ={"GITHUB_STEP_SUMMARY": str(summary)},
        capsys=capsys,
    )
    text = summary.read_text(encoding="utf-8")
    assert code == 1
    assert text.startswith("## Dependency audit")
    assert "FINDING GHSA-cpwx-vrp4-4pq7" in text


def test_a_missing_uv_executable_is_a_tool_error(tmp_path: Path) -> None:
    with pytest.raises(audit.AuditToolError, match="cannot run"):
        audit.subprocess_runner(["definitely-not-an-installed-uv"], tmp_path)


def test_real_uv_output_parses() -> None:
    report = audit.parse_report(json.dumps(CLEAN))
    assert report.audited_packages == 79 and report.findings == ()
    vulnerable = audit.parse_report(json.dumps(VULNERABLE))
    assert [f.package for f in vulnerable.findings] == ["jinja2", "urllib3"]


# ---------------------------------------------------------------------------
# Repository wiring
# ---------------------------------------------------------------------------


def _workflow(name: str) -> dict[Any, Any]:
    text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    assert isinstance(document, dict)
    return document


def _run_steps(job: dict[str, Any]) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


def test_the_committed_exceptions_file_is_valid() -> None:
    assert audit.load_exceptions(audit.EXCEPTIONS_FILE, _TODAY) is not None


def test_ci_audits_on_every_pull_request_and_gates_the_required_check() -> None:
    jobs = _workflow("test-template.yml")["jobs"]
    job = jobs["audit"]
    assert job["runs-on"] == "ubuntu-24.04"
    assert {"linux", "windows", "audit"} <= set(jobs["all-green"]["needs"])
    assert "scripts/audit_dependencies.py" in _run_steps(job)
    assert '--on-outage "$ON_OUTAGE"' in _run_steps(job)


def test_outage_policy_fails_on_schedule_and_dispatch_only() -> None:
    env = _workflow("test-template.yml")["jobs"]["audit"]["env"]["ON_OUTAGE"]
    assert "github.event_name == 'schedule'" in env
    assert "github.event_name == 'workflow_dispatch'" in env
    assert env.endswith("&& 'fail' || 'warn' }}")


def test_the_release_waits_on_a_fail_closed_audit_without_a_bypass() -> None:
    document = _workflow("release.yml")
    jobs = document["jobs"]
    needs = jobs["release"]["needs"]
    assert "audit" in ([needs] if isinstance(needs, str) else needs)
    assert "--on-outage fail" in _run_steps(jobs["audit"])
    assert "warn" not in _run_steps(jobs["audit"])
    assert jobs["audit"]["permissions"] == {"contents": "read"}
    # PyYAML (YAML 1.1) parses a bare `on` key as the boolean True.
    triggers = document.get("on", document.get(True))
    assert isinstance(triggers, dict)
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"dry_run"}, "no input may bypass the audit"


def test_the_audit_task_is_available_through_poe() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'audit = "python scripts/audit_dependencies.py"' in pyproject


def test_a_null_descriptive_field_is_tolerated_but_a_null_identity_is_drift() -> None:
    """Real OSV entries can have a null `summary`; `id` and the dependency
    identity may never be null."""
    tolerated = copy.deepcopy(VULNERABLE)
    tolerated["vulnerabilities"][0]["link"] = None
    assert audit.parse_report(json.dumps(tolerated)).findings[0].link == ""
    for field in ("id", "aliases", "fix_versions"):
        broken = copy.deepcopy(VULNERABLE)
        broken["vulnerabilities"][0][field] = None
        with pytest.raises(audit.AuditToolError, match="uv audit output changed"):
            audit.parse_report(json.dumps(broken))
    nameless = copy.deepcopy(VULNERABLE)
    nameless["vulnerabilities"][0]["dependency"]["name"] = None
    with pytest.raises(audit.AuditToolError, match="uv audit output changed"):
        audit.parse_report(json.dumps(nameless))
