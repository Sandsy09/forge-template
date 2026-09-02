"""Slow generated-project checks for the Scientific Python capability."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

from forge_template import ProjectSpec, parse_project_spec, render_project

pytestmark = pytest.mark.archetype

_DEPENDENCY_NAMES = {"matplotlib", "numpy", "pandas", "scikit-learn"}


def _spec(archetype: str, development: str = "3.13") -> ProjectSpec:
    options: dict[str, object] = {}
    if archetype == "library":
        options["library"] = {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        }
    return parse_project_spec(
        {
            "protocol_version": 1,
            "project": {
                "name": "Scientific Build Fixture",
                "package_name": "scientific_build_fixture",
                "repository_name": "scientific-build-fixture",
                "description": "Generated Scientific Python fixture.",
                "licence": "mit",
                "authors": [{"name": "Test User"}],
            },
            "python": {"minimum": development, "development": development},
            "components": {
                "archetype": archetype,
                "capabilities": ["scientific-python"],
                "platforms": [],
            },
            "component_options": options,
        }
    )


def _stage(spec: ProjectSpec, root: Path) -> None:
    for item in render_project(spec).files:
        target = root / item.target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.content)


def _run(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=root, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_generated_archetype_imports_scientific_stack_from_locked_environment(
    archetype: str, tmp_path: Path
) -> None:
    root = tmp_path / archetype
    root.mkdir()
    _stage(_spec(archetype), root)

    lock = _run(["uv", "lock"], root)
    assert lock.returncode == 0, lock.stdout + lock.stderr
    check = _run(
        [
            "uv",
            "run",
            "--locked",
            "pytest",
            "tests/test_scientific_python.py",
        ],
        root,
    )
    assert check.returncode == 0, check.stdout + check.stderr

    locked = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked_names = {package["name"] for package in locked["package"]}
    assert locked_names >= _DEPENDENCY_NAMES


@pytest.mark.parametrize("python", ["3.11", "3.14"])
def test_scientific_dependencies_resolve_at_python_endpoints(
    python: str, tmp_path: Path
) -> None:
    root = tmp_path / python
    root.mkdir()
    _stage(_spec("library", development=python), root)

    lock = _run(["uv", "lock", "--python", python], root)

    assert lock.returncode == 0, lock.stdout + lock.stderr
    assert (root / "uv.lock").is_file()
