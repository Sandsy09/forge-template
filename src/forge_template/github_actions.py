"""Validation for immutable GitHub Actions workflow references."""

from __future__ import annotations

import re
from pathlib import Path

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
