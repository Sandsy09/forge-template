"""Real `uv build` proof for the production Library archetype.

Slow (`archetype`-marked, `uv run poe archetype`): each packaging mode is
rendered to a real temporary directory, built with `uv build`, and its wheel,
sdist, installed metadata, import, and ``__version__`` are checked for real.
The fast render-level assertions live in ``tests/test_library_archetype.py``
instead -- see docs/library-archetype.md.
"""

from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

from forge_template import ProjectSpec, parse_project_spec, render_project

pytestmark = pytest.mark.archetype

_PACKAGE_NAME = "credit_risk_utils"
_REPOSITORY_NAME = "credit-risk-utils"
_VERSION = "0.4.2"


def _spec(*, packaging_mode: str) -> ProjectSpec:
    return parse_project_spec(
        {
            "protocol_version": 1,
            "project": {
                "name": "Credit Risk Utils",
                "package_name": _PACKAGE_NAME,
                "repository_name": _REPOSITORY_NAME,
                "description": "Shared credit-risk calculations.",
                "licence": "mit",
                "authors": [{"name": "Test User", "email": "test@example.invalid"}],
            },
            "python": {"minimum": "3.11", "development": "3.13"},
            "components": {"archetype": "library", "capabilities": [], "platforms": []},
            "component_options": {
                "library": {
                    "packaging_mode": packaging_mode,
                    "initial_version": _VERSION,
                }
            },
        }
    )


def _stage(spec: ProjectSpec, root: Path) -> None:
    for item in render_project(spec).files:
        path = root / item.target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.content)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    return root


@pytest.mark.parametrize(
    "packaging_mode", ["uv-build-static", "hatchling-static", "hatchling-vcs"]
)
def test_library_builds_wheel_and_sdist_per_packaging_mode(
    packaging_mode: str, project_root: Path
) -> None:
    _stage(_spec(packaging_mode=packaging_mode), project_root)

    if packaging_mode == "hatchling-vcs":
        # hatch-vcs derives the version from git tags at build time; the
        # rendered project has no git history of its own yet.
        for cmd in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "archetype-test@example.invalid"],
            ["git", "config", "user.name", "archetype-test"],
            ["git", "add", "-A"],
            ["git", "commit", "-q", "-m", "init"],
            ["git", "tag", f"v{_VERSION}"],
        ):
            result = _run(cmd, project_root)
            assert result.returncode == 0, result.stderr

    build = _run(["uv", "build"], project_root)
    assert build.returncode == 0, build.stderr

    dist = project_root / "dist"
    wheels = list(dist.glob("*.whl"))
    sdists = list(dist.glob("*.tar.gz"))
    assert len(wheels) == 1, dist.iterdir()
    assert len(sdists) == 1, dist.iterdir()

    wheel = wheels[0]
    assert wheel.name.startswith(f"{_PACKAGE_NAME}-{_VERSION}")

    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    assert any(name.endswith(f"{_PACKAGE_NAME}/__init__.py") for name in names)
    assert any(name.endswith(f"{_PACKAGE_NAME}/py.typed") for name in names)
    if packaging_mode == "hatchling-vcs":
        assert any(name.endswith(f"{_PACKAGE_NAME}/_version.py") for name in names)

    with tarfile.open(sdists[0]) as archive:
        sdist_names = archive.getnames()
    assert any(f"{_PACKAGE_NAME}/__init__.py" in name for name in sdist_names)


@pytest.mark.parametrize(
    "packaging_mode", ["uv-build-static", "hatchling-static", "hatchling-vcs"]
)
def test_library_wheel_installs_and_reports_its_version(
    packaging_mode: str, project_root: Path
) -> None:
    _stage(_spec(packaging_mode=packaging_mode), project_root)

    if packaging_mode == "hatchling-vcs":
        for cmd in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "archetype-test@example.invalid"],
            ["git", "config", "user.name", "archetype-test"],
            ["git", "add", "-A"],
            ["git", "commit", "-q", "-m", "init"],
            ["git", "tag", f"v{_VERSION}"],
        ):
            assert _run(cmd, project_root).returncode == 0

    assert _run(["uv", "build"], project_root).returncode == 0
    wheel = next((project_root / "dist").glob("*.whl"))

    venv = project_root / ".venv-install-check"
    assert _run(["uv", "venv", str(venv)], project_root).returncode == 0

    install = _run(
        ["uv", "pip", "install", "--python", str(venv), str(wheel)], project_root
    )
    assert install.returncode == 0, install.stderr

    python = venv / ("Scripts/python.exe" if _is_windows_venv(venv) else "bin/python")
    check = _run(
        [
            str(python),
            "-c",
            f"import {_PACKAGE_NAME} as m; print(m.__version__)",
        ],
        project_root,
    )
    assert check.returncode == 0, check.stderr
    assert check.stdout.strip() == _VERSION

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


def test_generated_library_project_passes_its_own_locked_check(
    project_root: Path,
) -> None:
    _stage(_spec(packaging_mode="uv-build-static"), project_root)

    lock = _run(["uv", "lock"], project_root)
    assert lock.returncode == 0, lock.stderr
    assert (project_root / "uv.lock").is_file()

    sync = _run(["uv", "sync", "--all-groups", "--locked"], project_root)
    assert sync.returncode == 0, sync.stderr

    check = _run(["uv", "run", "--locked", "poe", "check"], project_root)
    assert check.returncode == 0, check.stdout + check.stderr


def _is_windows_venv(venv: Path) -> bool:
    return (venv / "Scripts").is_dir()
