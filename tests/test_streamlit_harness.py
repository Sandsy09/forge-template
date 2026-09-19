"""Fast proofs of the Streamlit validation harness itself.

FT-20.03 / ADR 0072. The slow sweep in ``tests/test_streamlit_endpoints.py`` is
only evidence if its guard and its bound actually bite, so this module proves
them without a network: a timeout fails and is never retried, the listen guard
trips on a server but lets ordinary asyncio run, and the harness's numbers are
the compatibility contract's own.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from typing import TYPE_CHECKING

import pytest

from forge_template import render_project
from tests.streamlit_harness import (
    ENDPOINTS,
    LISTEN_GUARD_SOURCE,
    PROJECT_CHECK_TIMEOUT_SECONDS,
    SELECTIONS,
    SMOKE_RUN_TIMEOUT_SECONDS,
    BoundExceededError,
    bounded,
    clean_copy,
    spec,
    stage,
    write_listen_guard,
)
from tests.test_streamlit_gates import _constants

if TYPE_CHECKING:
    from pathlib import Path


def test_the_bounds_and_endpoints_are_the_contracts_own() -> None:
    constants = _constants()

    assert str(SMOKE_RUN_TIMEOUT_SECONDS) == constants["SMOKE_RUN_TIMEOUT_SECONDS"]
    assert (
        str(PROJECT_CHECK_TIMEOUT_SECONDS)
        == (constants["PROJECT_CHECK_TIMEOUT_SECONDS"])
    )
    assert ", ".join(ENDPOINTS) == constants["PYTHON_ENDPOINTS"]
    assert len(SELECTIONS) == 4


def test_a_bound_is_a_failure_and_the_command_runs_exactly_once(
    tmp_path: Path,
) -> None:
    """A timeout is never retried (docs/streamlit-compatibility-and-acceptance.md,
    "Time-bounded, non-serving smoke"): the command leaves one mark and no more."""
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


def test_the_listen_guard_source_is_valid_python() -> None:
    ast.parse(LISTEN_GUARD_SOURCE)


def test_the_listen_guard_trips_on_a_server(tmp_path: Path) -> None:
    """The guard must not rot into a no-op: a plain ``listen`` raises."""
    env = write_listen_guard(tmp_path / "guard")

    result = bounded(
        [sys.executable, "-c", "import socket; socket.socket().listen()"],
        tmp_path,
        timeout=60,
        env=env,
    )

    assert result.returncode != 0
    assert "a check must not serve" in result.stderr


def test_the_listen_guard_trips_on_an_asyncio_server(tmp_path: Path) -> None:
    """The way Streamlit's stack would serve: ``asyncio.start_server``."""
    env = write_listen_guard(tmp_path / "guard")
    script = (
        "import asyncio\n"
        "async def main():\n"
        "    server = await asyncio.start_server(lambda r, w: None, '127.0.0.1', 0)\n"
        "    server.close()\n"
        "asyncio.run(main())\n"
    )

    result = bounded([sys.executable, "-c", script], tmp_path, timeout=60, env=env)

    assert result.returncode != 0
    assert "a check must not serve" in result.stderr


def test_the_listen_guard_trips_on_socket_create_server(tmp_path: Path) -> None:
    """``socket.create_server`` calls ``listen`` from inside ``socket.py``, so a
    guard that trusted every ``socket.py`` caller would let it through; only the
    socketpair helper may listen."""
    env = write_listen_guard(tmp_path / "guard")
    script = "import socket; socket.create_server(('127.0.0.1', 0))"

    result = bounded([sys.executable, "-c", script], tmp_path, timeout=60, env=env)

    assert result.returncode != 0
    assert "a check must not serve" in result.stderr


def test_the_listen_guard_lets_asyncio_run_on_every_platform(tmp_path: Path) -> None:
    """Windows' proactor loop builds its self-pipe with a loopback ``listen``;
    the guard allows that one caller so ``poe`` and Jupyter still run."""
    env = write_listen_guard(tmp_path / "guard")
    script = "import asyncio\nasyncio.run(asyncio.sleep(0))\nprint('ran')\n"

    result = bounded([sys.executable, "-c", script], tmp_path, timeout=60, env=env)

    assert (result.returncode, result.stdout.strip()) == (0, "ran"), result.stderr


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
    """The check the harness runs is the terminating one: no server task."""
    for capabilities in SELECTIONS:
        files = {
            item.target: item.content
            for item in render_project(spec(capabilities)).files
        }
        tasks = tomllib.loads(files["pyproject.toml"].decode())["tool"]["poe"]["tasks"]
        assert "run" not in tasks["check"], capabilities
