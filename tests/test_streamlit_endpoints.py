"""Slow endpoint sweep for the Streamlit generated project.

FT-20.03 / ADR 0072. ``archetype``-marked (``uv run poe archetype``, run with
``-n 4`` so each cell lands on its own worker). It is the executable half of the
acceptance matrix in ``docs/streamlit-compatibility-and-acceptance.md``: each of
the four accepted selections is locked, restored from that committed lock in a
clean copy (and shown to fail on drift), passes its own ``poe check`` under the
project bound and a listen guard, builds a wheel and sdist, and installs in
isolation at Python 3.11 and 3.14. Two further tests audit the built artefacts
and the Forge-free installs. See docs/streamlit-validation.md.

The fast proofs -- composition, determinism, rejections, and the harness's own
bound and guard -- live in ``tests/test_streamlit_composition.py`` and
``tests/test_streamlit_harness.py``.
"""

from __future__ import annotations

import tarfile
import zipfile
from typing import TYPE_CHECKING

import pytest

from tests.streamlit_harness import (
    ENDPOINTS,
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
    write_listen_guard,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.archetype

_SECRET_MARKER = b"PLANTED-STREAMLIT-SECRET-DO-NOT-PACKAGE"
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
def test_streamlit_project_restores_checks_builds_and_installs_at_endpoint(
    capabilities: tuple[str, ...], endpoint: str, tmp_path: Path
) -> None:
    """Acceptance rows AC-05 and AC-07 for one selection at one window edge.

    1. ``uv lock`` produces the committed lock;
    2. a clean copy, with no virtual environment, restores from it with
       ``uv sync --all-groups --locked`` -- and a copy whose dependency
       declarations drifted from the lock is refused;
    3. the restored project passes ``uv run --locked poe check`` inside the
       600-second project bound and the listen guard, so a server started
       anywhere in the check fails the cell;
    4. it builds a wheel and an sdist, the wheel installs into an isolated
       environment, ``<package>`` and ``<package>.app`` import, and the version,
       ``Requires-Python`` and ``py.typed`` are reported; and
    5. neither the lock nor the installed environment names a Forge package.
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
    declared = '"streamlit>=1.63,<2",'
    text = pyproject.read_text(encoding="utf-8")
    assert declared in text
    pyproject.write_text(
        text.replace(declared, f'{declared}\n    "tomli-w>=1",'), encoding="utf-8"
    )
    refusal = bounded(
        ["uv", "sync", "--all-groups", "--locked"],
        drifted,
        timeout=STEP_TIMEOUT_SECONDS,
    )
    assert refusal.returncode != 0, "a drifted declaration must not restore"

    guard = write_listen_guard(tmp_path / "listen-guard")
    check = bounded(
        ["uv", "run", "--locked", "poe", "check"],
        restored,
        timeout=PROJECT_CHECK_TIMEOUT_SECONDS,
        env=guard,
    )
    assert check.returncode == 0, check.stdout + check.stderr

    _step(["uv", "build"], restored)
    wheels = list((restored / "dist").glob("*.whl"))
    sdists = list((restored / "dist").glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1, (wheels, sdists)
    assert wheels[0].name.startswith(f"{PACKAGE_NAME}-{VERSION}")

    # The install venv lives outside the project: ruff excludes `.venv`, not an
    # arbitrarily named one.
    venv = tmp_path / "install-check"
    _step(["uv", "venv", "--python", endpoint, str(venv)], restored)
    _step(["uv", "pip", "install", "--python", str(venv), str(wheels[0])], restored)

    python = _venv_python(venv)
    inspect = (
        f"import {PACKAGE_NAME} as m, {PACKAGE_NAME}.app as a\n"
        "import importlib.util as u\n"
        "from importlib.metadata import metadata\n"
        "from pathlib import Path\n"
        "print(m.__version__)\n"
        f"print(metadata('{REPOSITORY_NAME}')['Requires-Python'])\n"
        f"root = u.find_spec('{PACKAGE_NAME}').submodule_search_locations[0]\n"
        "print((Path(root) / 'py.typed').is_file())\n"
        "print(callable(a.main))\n"
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
    """The launcher, ``.streamlit/`` and ``tests/`` are source-tree files, not
    distribution content (docs/streamlit-compatibility-and-acceptance.md,
    "Package build and install requirements"). A planted ``secrets.toml`` is the
    worst case: it must reach neither artefact."""
    project = tmp_path / "project"
    stage(spec(()), project)
    secrets = project / ".streamlit" / "secrets.toml"
    secrets.write_bytes(b"api_token = '" + _SECRET_MARKER + b"'\n")

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
        "demo_app/__init__.py",
        "demo_app/app.py",
        "demo_app/py.typed",
    } <= set(wheel_names)
    for name in wheel_names:
        assert name.startswith((f"{PACKAGE_NAME}/", dist_info)), name

    # An sdist member is `<name>-<version>/<path>`; its root is the empty path.
    relative = [name.partition("/")[2] for name in sdist_names]
    assert {
        f"src/{PACKAGE_NAME}/__init__.py",
        f"src/{PACKAGE_NAME}/app.py",
        f"src/{PACKAGE_NAME}/py.typed",
    } <= set(relative)
    for path in relative:
        assert path in _SDIST_ROOT_FILES or path.startswith(f"src/{PACKAGE_NAME}"), path

    for name in (*wheel_names, *relative):
        assert ".streamlit" not in name, name
        assert "secrets" not in name, name
        assert name != "app.py", name
        assert not name.startswith("tests"), name
    assert _SECRET_MARKER not in wheel_blob
    assert _SECRET_MARKER not in sdist_blob
