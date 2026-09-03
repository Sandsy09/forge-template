"""Slow endpoint sweep for the Data Science generated project.

FT-12.03 / ADR 0055. ``archetype``-marked (``uv run poe archetype``, run with
``-n 4`` so each cell lands on its own worker). Proves that both valid
compositions build, install into an isolated environment, import, and pass
their own locked ``poe check`` -- including ``notebook:check`` over the real
starter notebook and a live kernel -- at Python 3.11 and at 3.14, that built
artefacts carry no ignored working-tree content, and that a generated project
needs neither Forge repository. See docs/data-science-validation.md.
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
_ENDPOINTS = ["3.11", "3.14"]
_COMPOSITIONS = [
    pytest.param(["jupyter"], id="jupyter"),
    pytest.param(["jupyter", "scientific-python"], id="jupyter+scientific-python"),
]
_IGNORED_WORKING_TREES = (
    "data/raw",
    "data/interim",
    "data/processed",
    "models",
    "artifacts",
)
_WORKING_TREE_MARKER = b"IGNORED-WORKING-TREE-PAYLOAD-DO-NOT-PACKAGE"


def _spec(capabilities: list[str], endpoint: str = "3.13") -> ProjectSpec:
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
            # `data-science`'s floor is `>=3.11`; the endpoint under test is the
            # development interpreter the project actually locks, builds, and
            # runs its notebook on -- 3.11 and 3.14, the window edges.
            "python": {"minimum": "3.11", "development": endpoint},
            "components": {
                "archetype": "data-science",
                "capabilities": capabilities,
                "platforms": [],
            },
            "component_options": {},
        }
    )


def _stage(spec: ProjectSpec, root: Path) -> None:
    for item in render_project(spec).files:
        path = root / item.target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.content)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _is_windows_venv(venv: Path) -> bool:
    return (venv / "Scripts").is_dir()


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if _is_windows_venv(venv) else "bin/python")


@pytest.mark.parametrize("capabilities", _COMPOSITIONS)
@pytest.mark.parametrize("endpoint", _ENDPOINTS)
def test_data_science_project_builds_installs_and_checks_at_endpoint(
    capabilities: list[str], endpoint: str, tmp_path: Path
) -> None:
    """The full endpoint sweep: lock, sync, build, isolated install, import,
    version, typing marker, and the generated project's own locked
    ``poe check`` (which ends in ``notebook:check`` over a live kernel)."""
    project = tmp_path / "project"
    project.mkdir()
    _stage(_spec(capabilities, endpoint=endpoint), project)

    lock = _run(["uv", "lock", "--python", endpoint], project)
    assert lock.returncode == 0, lock.stdout + lock.stderr
    assert (project / "uv.lock").is_file()

    sync = _run(["uv", "sync", "--all-groups", "--locked"], project)
    assert sync.returncode == 0, sync.stdout + sync.stderr

    build = _run(["uv", "build"], project)
    assert build.returncode == 0, build.stderr
    wheel = next((project / "dist").glob("*.whl"))
    assert wheel.name.startswith(f"{_PACKAGE_NAME}-{_VERSION}")

    # The install venv lives outside the project: ruff excludes `.venv`, not an
    # arbitrarily named one, and `poe check` below runs over the project tree.
    venv = tmp_path / "install-check"
    assert (
        _run(["uv", "venv", "--python", endpoint, str(venv)], project).returncode == 0
    )
    install = _run(["uv", "pip", "install", "--python", str(venv), str(wheel)], project)
    assert install.returncode == 0, install.stderr

    python = _venv_python(venv)
    inspect = (
        f"import {_PACKAGE_NAME} as m, importlib.util as u\n"
        "from pathlib import Path\n"
        "from importlib.metadata import metadata\n"
        "print(m.__version__)\n"
        f"print(metadata('{_REPOSITORY_NAME}')['Requires-Python'])\n"
        f"root = u.find_spec('{_PACKAGE_NAME}').submodule_search_locations[0]\n"
        "print((Path(root) / 'py.typed').is_file())\n"
    )
    reported = _run([str(python), "-c", inspect], project)
    assert reported.returncode == 0, reported.stderr
    version, requires_python, typed = reported.stdout.split()
    assert version == _VERSION
    assert requires_python == ">=3.11"
    assert typed == "True"

    check = _run(["uv", "run", "--locked", "poe", "check"], project)
    assert check.returncode == 0, check.stdout + check.stderr


def test_built_artefacts_carry_no_ignored_working_tree_content(
    tmp_path: Path,
) -> None:
    """The five ignored working trees are never created by the project, so
    they are created here and their content is proven absent from the wheel
    and the sdist -- docs/notebook-data-and-model-safeguards.md."""
    project = tmp_path / "project"
    project.mkdir()
    _stage(_spec(["jupyter"]), project)

    for tree in _IGNORED_WORKING_TREES:
        planted = project / tree / "planted.bin"
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_bytes(_WORKING_TREE_MARKER)

    build = _run(["uv", "build"], project)
    assert build.returncode == 0, build.stderr

    wheel = next((project / "dist").glob("*.whl"))
    sdist = next((project / "dist").glob("*.tar.gz"))

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        wheel_blob = b"".join(archive.read(name) for name in wheel_names)
    with tarfile.open(sdist) as archive:
        sdist_names = archive.getnames()
        sdist_blob = b"".join(
            archive.extractfile(member).read()  # type: ignore[union-attr]
            for member in archive.getmembers()
            if member.isfile()
        )

    for name in (*wheel_names, *sdist_names):
        stripped = name.split("/", 1)[-1] if name.count("/") else name
        assert not stripped.startswith(_IGNORED_WORKING_TREES), name
        assert "planted.bin" not in name, name
    assert _WORKING_TREE_MARKER not in wheel_blob
    assert _WORKING_TREE_MARKER not in sdist_blob


def test_generated_project_needs_no_forge_repository(tmp_path: Path) -> None:
    """No Forge distribution in the lock, and the installed package imports
    with neither ``forge_template`` nor its distribution present."""
    project = tmp_path / "project"
    project.mkdir()
    _stage(_spec(["jupyter", "scientific-python"]), project)

    lock = _run(["uv", "lock"], project)
    assert lock.returncode == 0, lock.stdout + lock.stderr
    locked = (project / "uv.lock").read_text(encoding="utf-8")
    assert "forge-template" not in locked
    assert "create-forge" not in locked

    assert _run(["uv", "build"], project).returncode == 0
    wheel = next((project / "dist").glob("*.whl"))
    venv = tmp_path / "forge-free"
    assert _run(["uv", "venv", str(venv)], project).returncode == 0
    assert (
        _run(
            ["uv", "pip", "install", "--python", str(venv), str(wheel)], project
        ).returncode
        == 0
    )

    python = _venv_python(venv)
    probe = (
        f"import {_PACKAGE_NAME}\n"
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
    result = _run([str(python), "-c", probe], project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "forge-free"
