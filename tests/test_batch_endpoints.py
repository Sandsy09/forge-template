"""Slow endpoint sweep for the batch generated project.

FT-28.02 / ADR 0083. ``archetype``-marked (``uv run poe archetype``, run with
``-n 4`` so each cell lands on its own worker). It is the executable half of
the acceptance matrix in ``docs/batch-compatibility-and-acceptance.md``: each
of the four accepted selections is locked, restored from that committed lock
in a clean copy (and shown to fail on drift), passes its own ``poe check``
under the project bound, runs the generated job twice (idempotent) and against
a malformed record (fail-fast, no output), builds a wheel and sdist, and
installs in isolation at Python 3.11 and 3.14. A further test audits the built
artefacts. See docs/batch-validation.md.

The fast proofs -- composition, determinism, rejections, and the harness's own
bound -- live in ``tests/test_batch_contract.py``, ``tests/test_batch_gates.py``
and ``tests/test_batch_harness.py``.
"""

from __future__ import annotations

import json
import tarfile
import zipfile
from typing import TYPE_CHECKING

import pytest

from tests.batch_harness import (
    ENDPOINTS,
    EXPECTED_OUTPUT,
    PACKAGE_NAME,
    PROJECT_CHECK_TIMEOUT_SECONDS,
    REPOSITORY_NAME,
    STEP_TIMEOUT_SECONDS,
    VERSION,
    bounded,
    clean_copy,
    forge_free_probe,
    selection_params,
    spec,
    stage,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.archetype

_SECRET_MARKER = b"PLANTED-BATCH-SECRET-DO-NOT-PACKAGE"
_SDIST_METADATA = {"PKG-INFO", "pyproject.toml", "pyproject.toml.orig"}
_SDIST_ROOT_FILES = _SDIST_METADATA | {"LICENSE", "README.md", "src", ""}


def _step(cmd: list[str], cwd: Path, *, timeout: float = STEP_TIMEOUT_SECONDS) -> str:
    result = bounded(cmd, cwd, timeout=timeout)
    assert result.returncode == 0, f"{' '.join(cmd)}\n{result.stdout}\n{result.stderr}"
    return result.stdout


def _venv_python(venv: Path) -> Path:
    scripts = venv / "Scripts"
    return scripts / "python.exe" if scripts.is_dir() else venv / "bin" / "python"


@pytest.mark.parametrize("capabilities", selection_params())
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_batch_project_restores_checks_builds_and_installs_at_endpoint(
    capabilities: tuple[str, ...], endpoint: str, tmp_path: Path
) -> None:
    """Acceptance rows for one selection at one window edge.

    1. ``uv lock`` produces the committed lock;
    2. a clean copy, with no virtual environment, restores from it with
       ``uv sync --all-groups --locked`` -- and a copy whose dependency
       declarations drifted from the lock is refused;
    3. the restored project passes ``uv run --locked poe check`` inside the
       600-second project bound;
    4. the generated console script and ``python -m <package>`` both run the
       job against the tracked sample input, produce the expected output, are
       idempotent on a rerun, and fail fast with no output on a malformed
       record;
    5. it builds a wheel and an sdist, the wheel installs into an isolated
       environment, ``<package>`` and ``<package>.job`` import, and the
       version, ``Requires-Python`` and ``py.typed`` are reported; and
    6. neither the lock nor the installed environment names a Forge package.
    """
    project = tmp_path / "project"
    stage(spec(capabilities, endpoint), project)

    _step(["uv", "lock", "--python", endpoint], project)
    assert (project / "uv.lock").is_file()

    restored = clean_copy(project, tmp_path / "restored")
    assert not (restored / ".venv").exists()
    _step(["uv", "sync", "--all-groups", "--locked"], restored)

    drifted = clean_copy(project, tmp_path / "drifted")
    pyproject = drifted / "pyproject.toml"
    opening = "\ndependencies = ["
    text = pyproject.read_text(encoding="utf-8")
    assert text.count(opening) == 1
    pyproject.write_text(
        text.replace(opening, opening + '\n    "tomli-w>=1",'),
        encoding="utf-8",
    )
    refusal = bounded(
        ["uv", "sync", "--all-groups", "--locked"],
        drifted,
        timeout=STEP_TIMEOUT_SECONDS,
    )
    assert refusal.returncode != 0, "a drifted declaration must not restore"

    check = bounded(
        ["uv", "run", "--locked", "poe", "check"],
        restored,
        timeout=PROJECT_CHECK_TIMEOUT_SECONDS,
    )
    assert check.returncode == 0, check.stdout + check.stderr

    # The console script and `python -m <package>` both run the job; a
    # rerun is byte-for-byte idempotent.
    _step(["uv", "run", "--locked", REPOSITORY_NAME], restored)
    console_output = (restored / "data" / "output.json").read_bytes()
    _step(["uv", "run", "--locked", REPOSITORY_NAME], restored)
    assert (restored / "data" / "output.json").read_bytes() == console_output
    assert json.loads(console_output) == EXPECTED_OUTPUT

    (restored / "data" / "output.json").unlink()
    _step(["uv", "run", "--locked", "python", "-m", PACKAGE_NAME], restored)
    module_output = json.loads(
        (restored / "data" / "output.json").read_text(encoding="utf-8")
    )
    assert module_output == EXPECTED_OUTPUT

    # A malformed record fails fast and writes no output.
    malformed = clean_copy(restored, tmp_path / "malformed")
    (malformed / "data" / "sample_input.json").write_text(
        json.dumps([{"not_id": "x"}]), encoding="utf-8"
    )
    (malformed / "data" / "output.json").unlink(missing_ok=True)
    failure = bounded(
        ["uv", "run", "--locked", "python", "-m", PACKAGE_NAME],
        malformed,
        timeout=PROJECT_CHECK_TIMEOUT_SECONDS,
    )
    assert failure.returncode == 1, failure.stdout + failure.stderr
    assert not (malformed / "data" / "output.json").exists()

    _step(["uv", "build"], restored)
    wheels = list((restored / "dist").glob("*.whl"))
    sdists = list((restored / "dist").glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1, (wheels, sdists)
    assert wheels[0].name.startswith(f"{PACKAGE_NAME}-{VERSION}")

    venv = tmp_path / "install-check"
    _step(["uv", "venv", "--python", endpoint, str(venv)], restored)
    _step(["uv", "pip", "install", "--python", str(venv), str(wheels[0])], restored)

    python = _venv_python(venv)
    inspect = (
        f"import {PACKAGE_NAME} as m, {PACKAGE_NAME}.job as j\n"
        "import importlib.util as u\n"
        "from importlib.metadata import metadata\n"
        "from pathlib import Path\n"
        "print(m.__version__)\n"
        f"print(metadata('{REPOSITORY_NAME}')['Requires-Python'])\n"
        f"root = u.find_spec('{PACKAGE_NAME}').submodule_search_locations[0]\n"
        "print((Path(root) / 'py.typed').is_file())\n"
        "print(callable(j.main))\n"
    )
    reported = _step([str(python), "-c", inspect], restored).split()
    assert reported == [VERSION, ">=3.11", "True", "True"]

    locked = (project / "uv.lock").read_text(encoding="utf-8")
    assert "forge-template" not in locked
    assert "create-forge" not in locked
    probe = _step([str(python), "-c", forge_free_probe()], restored)
    assert probe.strip() == "forge-free"


def test_built_artefacts_are_the_module_only_and_carry_no_secrets(
    tmp_path: Path,
) -> None:
    """The sample input and ``tests/`` are source-tree files, not distribution
    content (docs/batch-compatibility-and-acceptance.md, "Package build and
    install requirements"). A planted secret file is the worst case: it must
    reach neither artefact."""
    project = tmp_path / "project"
    stage(spec(()), project)
    secret = project / "data" / "secret.json"
    secret.write_bytes(b'{"token": "' + _SECRET_MARKER + b'"}\n')

    _step(["uv", "build"], project)
    wheel = next((project / "dist").glob("*.whl"))
    sdist = next((project / "dist").glob("*.tar.gz"))

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        wheel_blob = b"".join(archive.read(name) for name in wheel_names)
    with tarfile.open(sdist) as archive:
        sdist_names = archive.getnames()
        sdist_blob = b"".join(
            extracted.read()
            for member in archive.getmembers()
            if member.isfile() and (extracted := archive.extractfile(member))
        )

    dist_info = f"{PACKAGE_NAME}-{VERSION}.dist-info/"
    assert {
        "demo_job/__init__.py",
        "demo_job/__main__.py",
        "demo_job/job.py",
        "demo_job/py.typed",
    } <= set(wheel_names)
    for name in wheel_names:
        assert name.startswith((f"{PACKAGE_NAME}/", dist_info)), name

    # An sdist member is `<name>-<version>/<path>`; its root is the empty path.
    relative = [name.partition("/")[2] for name in sdist_names]
    assert {
        f"src/{PACKAGE_NAME}/__init__.py",
        f"src/{PACKAGE_NAME}/__main__.py",
        f"src/{PACKAGE_NAME}/job.py",
        f"src/{PACKAGE_NAME}/py.typed",
    } <= set(relative)
    for path in relative:
        assert path in _SDIST_ROOT_FILES or path.startswith(f"src/{PACKAGE_NAME}"), path

    for name in (*wheel_names, *relative):
        assert "data" not in name, name
        assert "secret" not in name, name
        assert not name.startswith("tests"), name
    assert _SECRET_MARKER not in wheel_blob
    assert _SECRET_MARKER not in sdist_blob
