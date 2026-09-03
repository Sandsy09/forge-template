"""Shared fixtures for the pytest-based validation suites.

The `combos` and `update` markers select the slow suites (each scaffolds a
real project via Copier and runs its full toolchain against it). The default
`poe test` deselects both -- see `[tool.pytest.ini_options] markers` and the
`test`/`combos`/`update` Poe tasks in pyproject.toml.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from forge_template.schema import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--from-git",
        action="store_true",
        default=False,
        help=(
            "Scaffold combos from real git history (vcs_ref=HEAD) instead of a "
            "non-git snapshot. Snapshot mode (the default) picks up uncommitted "
            "edits, matching what scripts/test-combos.sh used to do; --from-git "
            "is what CI passes, since _commit must be recorded."
        ),
    )
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help=(
            "Rewrite the checked-in test fixtures from current output instead "
            "of asserting against them: tests/fixtures/golden/*.json "
            "(tests/test_composition_contract.py) and "
            "tests/fixtures/archetype_regression/digests.json "
            "(tests/test_data_science_composition.py). Review the diff like any "
            "other change -- see docs/composition-fixtures.md."
        ),
    )


@pytest.fixture(scope="session")
def from_git(pytestconfig: pytest.Config) -> bool:
    """Whether combos/update scenarios should scaffold from committed git
    history (--from-git) or an uncommitted snapshot (the default).
    """
    return bool(pytestconfig.getoption("--from-git"))


@pytest.fixture(scope="session")
def update_goldens(pytestconfig: pytest.Config) -> bool:
    """Whether fixture-backed tests should rewrite their checked-in
    expectations (--update-goldens) instead of asserting against them --
    the composition-contract goldens and the archetype regression digests.
    """
    return bool(pytestconfig.getoption("--update-goldens"))


@pytest.fixture(scope="session", autouse=True)
def _git_identity() -> None:
    """Ensure git has *some* identity before any `_tasks` commit runs.

    Missing git identity on the CI runner was one of three bugs that sat
    undetected on `main` for days (CLAUDE.md, "Validation") because the local
    suite never reproduced it -- the author's own machine already has an
    identity configured.

    `GIT_AUTHOR_NAME`/etc env vars were tried first here and did not work:
    Copier's `_tasks` execution goes through `plumbum`, which snapshots
    `os.environ` when `copier` is first imported -- during pytest collection,
    before this session-scoped fixture's body ever runs -- so mutating
    `os.environ` here was invisible to it. `git config --global` writes to
    the actual gitconfig file, which every subprocess reads fresh regardless
    of when it started, so it isn't subject to that ordering. Safe here
    specifically because it only fires when no identity exists at all: on the
    author's own machine that never triggers, and on a CI runner the git
    config is thrown away with the VM.

    Under ``pytest-xdist`` (``poe archetype -n 4``, ``poe combos -n 4``) every
    worker is a separate process running this session fixture, so the
    ``git config --global`` writes race on ``~/.gitconfig.lock``. The retry
    loop tolerates that: a lock failure just means a peer is writing the same
    identity, so re-check and return once it lands.
    """

    def _has_identity() -> bool:
        got = subprocess.run(
            ["git", "config", "--get", "user.email"], capture_output=True, text=True
        )
        return got.returncode == 0 and bool(got.stdout.strip())

    if _has_identity():
        return
    for attempt in range(20):
        name = subprocess.run(
            ["git", "config", "--global", "user.name", "pytest"], capture_output=True
        )
        email = subprocess.run(
            ["git", "config", "--global", "user.email", "pytest@example.invalid"],
            capture_output=True,
        )
        if name.returncode == 0 and email.returncode == 0:
            return
        if _has_identity():  # a peer worker won the race
            return
        time.sleep(0.1 * (attempt + 1))
    msg = "could not configure a git identity (gitconfig lock contention)"
    raise RuntimeError(msg)


@pytest.fixture(scope="session")
def template_snapshot(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A non-git copy of this repo, so uncommitted template/ edits are
    picked up -- the same trick `test-combos.sh` used (`rm -rf .git`).
    """
    dst = tmp_path_factory.mktemp("template-snapshot")
    shutil.copytree(
        REPO_ROOT,
        dst,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc"),
    )
    return dst


@pytest.fixture(scope="session")
def combos_workdir() -> Path:
    """Fixed, well-known output directory -- `${TMPDIR:-/tmp}/copier-combos`,
    matching what `scripts/test-combos.sh` used to produce, so
    `scripts/verify-ci.sh` can still find combo outputs to push after a
    `poe combos` run.

    Deliberately not `tmp_path` (pytest's per-test random directory): each
    pytest-xdist worker is a separate process with its own instance of this
    session fixture, so cleanup happens per-combo in the test itself rather
    than here, to avoid one worker wiping a directory another is using.
    """
    base = Path(tempfile.gettempdir()) / "copier-combos"
    base.mkdir(parents=True, exist_ok=True)
    return base


def resolve_src(
    from_git: bool,
    request: pytest.FixtureRequest,
) -> tuple[str, str | None]:
    """(src_path, vcs_ref) for `run_copy`/`run_update`, matching `from_git`.

    Uses `request.getfixturevalue` so the (session-scoped, but not free)
    `template_snapshot` copy is only made when actually needed.
    """
    if from_git:
        return str(REPO_ROOT), "HEAD"
    snapshot: Path = request.getfixturevalue("template_snapshot")
    return str(snapshot), None


def latest_tag(repo: Path) -> str | None:
    """The newest `v*` tag in `repo`, or None if there isn't one yet."""
    result = subprocess.run(
        ["git", "tag", "-l", "v*", "--sort=-v:refname"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    tags = [line for line in result.stdout.splitlines() if line.strip()]
    return tags[0] if tags else None


def run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a subprocess inside a scaffolded project, without the parent
    repo's own `.venv` bleeding in via `VIRTUAL_ENV`.
    """
    env: Mapping[str, str] = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=dict(env))
