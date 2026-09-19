"""Slow dependency-resolution sweep for the Streamlit generated project.

FT-20.02 / ADR 0071. ``archetype``-marked (``uv run poe archetype``, run with
``-n 4`` so each cell lands on its own worker). It discharges the one slow
acceptance row the compatibility contract gives FT-20.02: ``streamlit>=1.63,<2``,
alone and with the Jupyter and Scientific Python lines, resolves at Python 3.11
and 3.14. Resolution only -- the build, isolated install, committed-lock
restoration and the generated ``poe check`` across the four selections are
FT-20.03's. See docs/streamlit-compatibility-and-acceptance.md.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

from forge_template import ProjectSpec, parse_project_spec, render_project

pytestmark = pytest.mark.archetype

_ENDPOINTS = ["3.11", "3.14"]
_SELECTIONS = [
    pytest.param([], id="alone"),
    pytest.param(["jupyter"], id="jupyter"),
    pytest.param(["scientific-python"], id="scientific-python"),
    pytest.param(["jupyter", "scientific-python"], id="jupyter+scientific-python"),
]


def _spec(capabilities: list[str], endpoint: str) -> ProjectSpec:
    return parse_project_spec(
        {
            "protocol_version": 1,
            "project": {
                "name": "Demo App",
                "package_name": "demo_app",
                "repository_name": "demo-app",
                "description": "A demonstration.",
                "licence": "mit",
                "authors": [{"name": "Test User", "email": "test@example.invalid"}],
            },
            # The endpoint is the development interpreter the project locks for;
            # the floor stays the archetype's `>=3.11`.
            "python": {"minimum": "3.11", "development": endpoint},
            "components": {
                "archetype": "streamlit",
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


def _locked_versions(lock: Path, name: str) -> list[tuple[int, ...]]:
    packages = tomllib.loads(lock.read_text(encoding="utf-8"))["package"]
    return [
        tuple(int(part) for part in package["version"].split(".")[:3])
        for package in packages
        if package["name"] == name
    ]


@pytest.mark.parametrize("capabilities", _SELECTIONS)
@pytest.mark.parametrize("endpoint", _ENDPOINTS)
def test_streamlit_selection_resolves_at_endpoint(
    capabilities: list[str], endpoint: str, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _stage(_spec(capabilities, endpoint), project)

    lock = _run(["uv", "lock", "--python", endpoint], project)
    assert lock.returncode == 0, lock.stdout + lock.stderr
    lockfile = project / "uv.lock"
    assert lockfile.is_file()

    # The declared line holds: Streamlit locks inside `>=1.63,<2`.
    streamlit = _locked_versions(lockfile, "streamlit")
    assert streamlit, "streamlit is not in the lock"
    assert all((1, 63) <= version < (2,) for version in streamlit), streamlit

    # The development-only cap (ADR 0070) reaches every resolution, so no
    # selection can lock the NumPy line whose stubs Foundation's mypy cannot parse.
    numpy = _locked_versions(lockfile, "numpy")
    assert numpy, "numpy is not in the lock"
    assert all(version < (2, 5) for version in numpy), numpy

    # The lock is self-consistent, which is what `poe check` begins with.
    check = _run(["uv", "lock", "--check", "--python", endpoint], project)
    assert check.returncode == 0, check.stdout + check.stderr
