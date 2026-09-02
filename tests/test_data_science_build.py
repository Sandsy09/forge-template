"""Real ``uv build`` proof for the production Data Science archetype.

Slow (``archetype``-marked, ``uv run poe archetype``): the archetype is
rendered with its required ``jupyter`` capability to a real temporary
directory, built with ``uv build``, and its wheel, sdist, installed metadata,
import, ``__version__``, and typing marker are checked for real, then the
generated project passes its own locked ``poe check``. The fast render-level
assertions live in ``tests/test_data_science_archetype.py`` instead -- see
docs/data-science-archetype.md.
"""

from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

from forge_template import ProjectSpec, parse_project_spec, render_project

pytestmark = pytest.mark.archetype

_PACKAGE_NAME = "churn_model"
_REPOSITORY_NAME = "churn-model"
_VERSION = "0.1.0"


def _spec() -> ProjectSpec:
    return parse_project_spec(
        {
            "protocol_version": 1,
            "project": {
                "name": "Churn Model",
                "package_name": _PACKAGE_NAME,
                "repository_name": _REPOSITORY_NAME,
                "description": "Churn prediction work.",
                "licence": "mit",
                "authors": [{"name": "Test User", "email": "test@example.invalid"}],
            },
            "python": {"minimum": "3.11", "development": "3.13"},
            "components": {
                "archetype": "data-science",
                "capabilities": ["jupyter"],
                "platforms": [],
            },
            "component_options": {},
        }
    )


def _stage(root: Path) -> None:
    for item in render_project(_spec()).files:
        path = root / item.target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.content)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _is_windows_venv(venv: Path) -> bool:
    return (venv / "Scripts").is_dir()


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if _is_windows_venv(venv) else "bin/python")


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    return root


def test_data_science_builds_wheel_and_sdist(project_root: Path) -> None:
    _stage(project_root)

    build = _run(["uv", "build"], project_root)
    assert build.returncode == 0, build.stderr

    dist = project_root / "dist"
    wheels = list(dist.glob("*.whl"))
    sdists = list(dist.glob("*.tar.gz"))
    assert len(wheels) == 1, list(dist.iterdir())
    assert len(sdists) == 1, list(dist.iterdir())

    wheel = wheels[0]
    assert wheel.name.startswith(f"{_PACKAGE_NAME}-{_VERSION}")

    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    assert any(name.endswith(f"{_PACKAGE_NAME}/__init__.py") for name in names)
    assert any(name.endswith(f"{_PACKAGE_NAME}/py.typed") for name in names)

    with tarfile.open(sdists[0]) as archive:
        sdist_names = archive.getnames()
    assert any(f"{_PACKAGE_NAME}/__init__.py" in name for name in sdist_names)


@pytest.fixture
def installed_venv(project_root: Path) -> Path:
    """Build the archetype, install its wheel into an isolated venv."""
    _stage(project_root)
    assert _run(["uv", "build"], project_root).returncode == 0
    wheel = next((project_root / "dist").glob("*.whl"))

    venv = project_root / ".venv-install-check"
    assert _run(["uv", "venv", str(venv)], project_root).returncode == 0

    install = _run(
        ["uv", "pip", "install", "--python", str(venv), str(wheel)], project_root
    )
    assert install.returncode == 0, install.stderr
    return venv


def test_installed_distribution_metadata_matches_the_contract(
    installed_venv: Path, project_root: Path
) -> None:
    python = _venv_python(installed_venv)
    inspect = (
        "from importlib.metadata import metadata as md\n"
        f"d = md('{_REPOSITORY_NAME}')\n"
        "print(d['Name']); print(d['Version']); print(d['Requires-Python'])\n"
    )
    metadata = _run([str(python), "-c", inspect], project_root)
    assert metadata.returncode == 0, metadata.stderr
    lines = metadata.stdout.strip().splitlines()
    assert lines[0] == _REPOSITORY_NAME
    assert lines[1] == _VERSION
    assert lines[2] == ">=3.11"


def test_installed_package_imports_and_reports_its_version(
    installed_venv: Path, project_root: Path
) -> None:
    python = _venv_python(installed_venv)
    inspect = f"import {_PACKAGE_NAME}; print({_PACKAGE_NAME}.__version__)"
    result = _run([str(python), "-c", inspect], project_root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == _VERSION


def test_installed_distribution_ships_the_typing_marker(
    installed_venv: Path, project_root: Path
) -> None:
    python = _venv_python(installed_venv)
    inspect = (
        "import importlib.util as u\n"
        f"spec = u.find_spec('{_PACKAGE_NAME}')\n"
        "root = spec.submodule_search_locations[0]\n"
        "from pathlib import Path\n"
        "print((Path(root) / 'py.typed').is_file())\n"
    )
    result = _run([str(python), "-c", inspect], project_root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


def test_generated_data_science_project_passes_its_own_check(
    project_root: Path,
) -> None:
    """The generated package, smoke test, and Jupyter tooling clear
    Foundation's own quality gate (lock:check, Ruff, mypy --strict, pytest,
    notebook:check over an empty notebook set) from committed lock state."""
    _stage(project_root)

    lock = _run(["uv", "lock"], project_root)
    assert lock.returncode == 0, lock.stderr
    assert (project_root / "uv.lock").is_file()

    sync = _run(["uv", "sync", "--all-groups", "--locked"], project_root)
    assert sync.returncode == 0, sync.stderr

    check = _run(["uv", "run", "--locked", "poe", "check"], project_root)
    assert check.returncode == 0, check.stdout + check.stderr
