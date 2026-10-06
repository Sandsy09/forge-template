"""Shared harness for the batch generated-project validation.

FT-28.02 / ADR 0083. The slow endpoint sweep (``tests/test_batch_endpoints.py``)
and the fast proofs of the harness itself (``tests/test_batch_harness.py``)
share this module, so the bounds they enforce are one constant, checked against
the compatibility contract, rather than a number repeated in two places. It
mirrors ``tests/streamlit_harness.py`` (FT-20.03 / ADR 0072); the one
substantive difference is that batch starts no server, so there is no listen
guard -- the smoke instead runs the generated job itself and checks its output.

**A timeout is a failure and is never retried.** ``bounded`` runs each command
exactly once under a hard ``subprocess`` bound and raises on expiry; nothing in
the harness raises a bound to make a run pass.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from forge_template import parse_project_spec, render_project

if TYPE_CHECKING:
    from pathlib import Path

    from forge_template import ProjectSpec

#: The contract's ``JOB_RUN_TIMEOUT_SECONDS`` and
#: ``PROJECT_CHECK_TIMEOUT_SECONDS``; ``tests/test_batch_harness.py`` pins both
#: against the constants table in
#: ``docs/batch-compatibility-and-acceptance.md``.
JOB_RUN_TIMEOUT_SECONDS = 5
PROJECT_CHECK_TIMEOUT_SECONDS = 600
#: A generous ceiling for the network-bound steps (lock, sync, build, install),
#: which the contract does not bound. It exists so a hung step fails instead of
#: hanging the suite.
STEP_TIMEOUT_SECONDS = 1200

PACKAGE_NAME = "demo_job"
REPOSITORY_NAME = "demo-job"
VERSION = "0.1.0"
ENDPOINTS = ("3.11", "3.14")

#: The four accepted capability selections, in the contract's order -- the
#: same tuples Streamlit accepts, since batch declares no ``requires`` or
#: ``conflicts`` of its own.
SELECTIONS: tuple[tuple[str, ...], ...] = (
    (),
    ("jupyter",),
    ("scientific-python",),
    ("jupyter", "scientific-python"),
)

#: The deterministic output ``docs/batch-archetype.md``'s sample input
#: transforms to: every ``id`` normalised and upper-cased.
EXPECTED_OUTPUT: list[dict[str, str]] = [
    {"id": "A1", "name": "Widget"},
    {"id": "B2", "name": "Gadget"},
    {"id": "C3", "name": "Gizmo"},
]


def selection_id(capabilities: tuple[str, ...]) -> str:
    """A readable pytest id: ``alone`` or ``jupyter+scientific-python``."""
    return "+".join(capabilities) or "alone"


def selection_params() -> list[object]:
    return [pytest.param(caps, id=selection_id(caps)) for caps in SELECTIONS]


def spec(capabilities: tuple[str, ...], endpoint: str = "3.13") -> ProjectSpec:
    """A batch ProjectSpec whose development interpreter is ``endpoint``.

    The floor stays the archetype's ``>=3.11``; the endpoint is the interpreter
    the project actually locks, builds and runs on.
    """
    return parse_project_spec(
        {
            "protocol_version": 1,
            "project": {
                "name": "Demo Job",
                "package_name": PACKAGE_NAME,
                "repository_name": REPOSITORY_NAME,
                "description": "A demonstration.",
                "licence": "mit",
                "authors": [{"name": "Test User", "email": "test@example.invalid"}],
            },
            "python": {"minimum": "3.11", "development": endpoint},
            "components": {
                "archetype": "batch",
                "capabilities": list(capabilities),
                "platforms": [],
            },
            "component_options": {},
        }
    )


def stage(project_spec: ProjectSpec, root: Path) -> None:
    """Write the rendered project under ``root``."""
    root.mkdir(parents=True, exist_ok=True)
    for item in render_project(project_spec).files:
        path = root / item.target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.content)


def clean_copy(project: Path, destination: Path) -> Path:
    """Copy ``project`` without any environment or build output.

    This is what a committed checkout looks like: the sources and ``uv.lock``,
    no ``.venv`` and no ``dist``.
    """
    shutil.copytree(
        project, destination, ignore=shutil.ignore_patterns(".venv", "dist")
    )
    return destination


class BoundExceededError(AssertionError):
    """A command outlived its bound. Never retried, never raised to pass."""


def bounded(
    cmd: list[str],
    cwd: Path,
    *,
    timeout: float,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``cmd`` once, without the parent repository's ``VIRTUAL_ENV``.

    Raises :class:`BoundExceededError` if it outlives ``timeout``. There is no
    retry: the caller sees the first and only outcome.
    """
    environment = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    environment.update(env or {})
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=environment,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"{' '.join(cmd)!r} exceeded its {timeout:g}s bound"
        raise BoundExceededError(msg) from exc


def forge_free_probe() -> str:
    """A snippet for the installed venv: importable, and Forge-free."""
    return (
        f"import {PACKAGE_NAME}\n"
        "from importlib.metadata import distributions\n"
        "names = {d.metadata['Name'].lower() for d in distributions()}\n"
        "assert 'forge-template' not in names, names\n"
        "assert 'create-forge' not in names, names\n"
        "try:\n"
        "    import forge_template\n"
        "    raise SystemExit('forge_template importable in the generated venv')\n"
        "except ModuleNotFoundError:\n"
        "    print('forge-free')\n"
    )
