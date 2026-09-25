"""Validation for immutable GitHub Actions workflow references and runner labels."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_USES_RE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*(?P<value>[^#]+?)(?:\s+#\s*(?P<comment>.*))?$"
)
_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_EXACT_RELEASE_RE = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_WORKFLOW_SUFFIXES = (".yml", ".yaml", ".yml.jinja", ".yaml.jinja")


def _workflow_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        return []
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name.endswith(_WORKFLOW_SUFFIXES)
    ]


def check_action_pins(workflows: Path) -> list[str]:
    """Require immutable, updater-readable references in workflow ``uses``.

    Local actions and reusable workflows are already bound to the calling
    repository commit, so ``./...`` references are exempt. Repository-based
    remote references must use a full SHA and retain an exact release tag in
    a same-line comment so Renovate and Dependabot can update them safely.
    Docker actions are rejected until Forge defines digest maintenance for
    them.
    """
    errors: list[str] = []
    for path in _workflow_files(workflows):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError) as exc:
            errors.append(f"{path}: cannot read workflow: {exc}")
            continue

        for lineno, line in enumerate(lines, start=1):
            match = _USES_RE.match(line)
            if match is None:
                continue

            value = match.group("value").strip().strip("\"'")
            comment = (match.group("comment") or "").strip()
            location = f"{path}:{lineno}"

            if value.startswith("./"):
                continue
            if value.startswith("docker://"):
                errors.append(
                    f"{location}: docker action references are unsupported until "
                    "digest pinning and maintenance are defined"
                )
                continue
            if "@" not in value:
                errors.append(f"{location}: remote action reference has no @ revision")
                continue

            target, revision = value.rsplit("@", maxsplit=1)
            if "/" not in target:
                errors.append(f"{location}: unsupported uses reference: {value}")
                continue
            if _FULL_SHA_RE.fullmatch(revision) is None:
                errors.append(
                    f"{location}: remote action must use a full 40-character "
                    f"commit SHA, found {revision!r}"
                )
            if _EXACT_RELEASE_RE.fullmatch(comment) is None:
                errors.append(
                    f"{location}: pinned action must have a same-line exact "
                    "release comment such as '# v4.4.0'"
                )
    return errors


def _runs_on_labels(runs_on: Any) -> list[str]:
    """Return the literal runner labels a job's ``runs-on`` names.

    ``runs-on`` may be a string, a list of labels, or a mapping with a
    ``labels`` key (string or list). Expressions such as
    ``${{ inputs.runner }}`` are returned as-is: the caller that supplies the
    value is checked separately by :func:`_caller_runner_labels`.
    """
    if isinstance(runs_on, str):
        return [runs_on]
    if isinstance(runs_on, list):
        return [label for label in runs_on if isinstance(label, str)]
    if isinstance(runs_on, dict):
        return _runs_on_labels(runs_on.get("labels"))
    return []


def _caller_runner_labels(job: dict[str, Any]) -> list[str]:
    """Return the ``runner`` input a reusable-workflow caller job passes."""
    with_ = job.get("with")
    if isinstance(with_, dict) and isinstance(with_.get("runner"), str):
        return [with_["runner"]]
    return []


def check_runner_labels(workflows: Path) -> list[str]:
    """Reject the moving ``ubuntu-latest`` alias in repository workflows.

    GitHub repoints ``ubuntu-latest`` on its own schedule, so the effective
    Linux baseline would change without a reviewed commit. Every job must name
    an explicit image, both directly in ``runs-on`` and through the ``runner``
    input a caller hands a reusable workflow (ADR 0074). ``windows-latest``
    is deliberately out of scope; ``docs/ci-runner-baseline.md`` records it as
    a known gap. Only parseable ``.yml``/``.yaml`` files are read, so this
    applies to this repository's workflows and never to the generated-project
    ``*.jinja`` templates, whose runner baseline is a separate compatibility
    decision.
    """
    errors: list[str] = []
    for path in _workflow_files(workflows):
        if path.name.endswith(".jinja"):
            continue
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError, yaml.YAMLError) as exc:
            errors.append(f"{path}: cannot read workflow: {exc}")
            continue

        jobs = document.get("jobs") if isinstance(document, dict) else None
        if not isinstance(jobs, dict):
            continue
        for name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            labels = [*_runs_on_labels(job.get("runs-on")), *_caller_runner_labels(job)]
            if any(label.strip() == "ubuntu-latest" for label in labels):
                errors.append(
                    f"{path.name}: job {name!r} runs on 'ubuntu-latest', a "
                    "moving alias; name an explicit image such as "
                    "'ubuntu-24.04' (docs/ci-runner-baseline.md)"
                )
    return errors
