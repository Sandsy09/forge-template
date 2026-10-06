"""Fast proofs of the batch validation harness itself.

FT-28.02 / ADR 0083. The slow sweep in ``tests/test_batch_endpoints.py`` is
only evidence if its bound actually bites, so this module proves it without a
network: a timeout fails and is never retried, a clean copy carries no
environment or build output, and the harness's numbers are the compatibility
contract's own. Mirrors ``tests/test_streamlit_harness.py``; there is no
listen guard here because batch starts no server.
"""

from __future__ import annotations

import sys
import tomllib
from typing import TYPE_CHECKING

import pytest

from forge_template import render_project
from tests.batch_harness import (
    ENDPOINTS,
    JOB_RUN_TIMEOUT_SECONDS,
    PROJECT_CHECK_TIMEOUT_SECONDS,
    SELECTIONS,
    BoundExceededError,
    bounded,
    clean_copy,
    spec,
    stage,
)
from tests.test_batch_gates import _constants

if TYPE_CHECKING:
    from pathlib import Path


def test_the_bounds_and_endpoints_are_the_contracts_own() -> None:
    constants = _constants()

    assert str(JOB_RUN_TIMEOUT_SECONDS) == constants["JOB_RUN_TIMEOUT_SECONDS"]
    assert (
        str(PROJECT_CHECK_TIMEOUT_SECONDS) == constants["PROJECT_CHECK_TIMEOUT_SECONDS"]
    )
    assert ", ".join(ENDPOINTS) == constants["PYTHON_ENDPOINTS"]
    assert len(SELECTIONS) == 4


def test_a_bound_is_a_failure_and_the_command_runs_exactly_once(
    tmp_path: Path,
) -> None:
    """A timeout is never retried (docs/batch-compatibility-and-acceptance.md,
    "Time-bounded, deterministic smoke"): the command leaves one mark and no
    more."""
    counter = tmp_path / "runs.txt"
    script = (
        "import pathlib, time\n"
        f"counter = pathlib.Path({str(counter)!r})\n"
        "counter.write_text(counter.read_text() + 'x' if counter.exists() else 'x')\n"
        "time.sleep(60)\n"
    )

    with pytest.raises(BoundExceededError, match="exceeded its 2s bound"):
        bounded([sys.executable, "-c", script], tmp_path, timeout=2)

    assert counter.read_text() == "x"


def test_a_command_inside_its_bound_returns_its_result(tmp_path: Path) -> None:
    result = bounded(
        [sys.executable, "-c", "print('ok')"],
        tmp_path,
        timeout=PROJECT_CHECK_TIMEOUT_SECONDS,
    )

    assert (result.returncode, result.stdout.strip()) == (0, "ok")


def test_a_clean_copy_carries_no_environment_or_build_output(tmp_path: Path) -> None:
    project = tmp_path / "project"
    stage(spec(()), project)
    for leftover in (".venv/marker", "dist/marker"):
        path = project / leftover
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    copy = clean_copy(project, tmp_path / "copy")

    assert (copy / "pyproject.toml").is_file()
    assert not (copy / ".venv").exists()
    assert not (copy / "dist").exists()


def test_the_rendered_project_never_lists_run_in_its_check() -> None:
    """The check the harness runs is the terminating one: no server or job
    task leaks into the aggregate ``check``."""
    for capabilities in SELECTIONS:
        files = {
            item.target: item.content
            for item in render_project(spec(capabilities)).files
        }
        tasks = tomllib.loads(files["pyproject.toml"].decode())["tool"]["poe"]["tasks"]
        assert "run" not in tasks["check"], capabilities
