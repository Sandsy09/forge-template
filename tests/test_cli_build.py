"""Real `uv build` proof for the production CLI Application archetype.

Slow (`archetype`-marked, `uv run poe archetype`): the archetype is rendered
to a real temporary directory, built with `uv build`, and its wheel, sdist,
installed metadata, console script, module invocation, and command behavior
are checked for real. The fast render-level assertions live in
``tests/test_cli_archetype.py`` instead -- see docs/cli-application-archetype.md.
"""

from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

from forge_template import ProjectSpec, parse_project_spec, render_project

pytestmark = pytest.mark.archetype

_PACKAGE_NAME = "credit_risk_cli"
_REPOSITORY_NAME = "credit-risk-cli"
_VERSION = "0.1.0"


def _spec() -> ProjectSpec:
    return parse_project_spec(
        {
            "protocol_version": 1,
            "project": {
                "name": "Credit Risk CLI",
                "package_name": _PACKAGE_NAME,
                "repository_name": _REPOSITORY_NAME,
                "description": "A CLI for credit risk stuff.",
                "licence": "mit",
                "authors": [{"name": "Test User", "email": "test@example.invalid"}],
            },
            "python": {"minimum": "3.11", "development": "3.13"},
            "components": {"archetype": "cli", "capabilities": [], "platforms": []},
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


def _venv_console_script(venv: Path) -> Path:
    name = f"{_REPOSITORY_NAME}.exe" if _is_windows_venv(venv) else _REPOSITORY_NAME
    directory = "Scripts" if _is_windows_venv(venv) else "bin"
    return venv / directory / name


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    return root


def test_cli_builds_wheel_and_sdist(project_root: Path) -> None:
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
    assert any(name.endswith(f"{_PACKAGE_NAME}/__main__.py") for name in names)
    assert any(name.endswith(f"{_PACKAGE_NAME}/cli.py") for name in names)
    assert any(name.endswith(f"{_PACKAGE_NAME}/py.typed") for name in names)

    with tarfile.open(sdists[0]) as archive:
        sdist_names = archive.getnames()
    assert any(f"{_PACKAGE_NAME}/cli.py" in name for name in sdist_names)


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


def test_console_script_no_arguments_prints_help(
    installed_venv: Path, project_root: Path
) -> None:
    script = _venv_console_script(installed_venv)
    result = _run([str(script)], project_root)
    assert result.returncode == 0, result.stderr
    assert "Usage" in result.stdout
    assert result.stderr == ""


def test_console_script_help_flag(installed_venv: Path, project_root: Path) -> None:
    script = _venv_console_script(installed_venv)
    result = _run([str(script), "--help"], project_root)
    assert result.returncode == 0, result.stderr
    assert "Usage" in result.stdout


def test_console_script_version_flag(installed_venv: Path, project_root: Path) -> None:
    script = _venv_console_script(installed_venv)
    result = _run([str(script), "--version"], project_root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{_REPOSITORY_NAME} {_VERSION}"


def test_console_script_hello_defaults_to_world(
    installed_venv: Path, project_root: Path
) -> None:
    script = _venv_console_script(installed_venv)
    result = _run([str(script), "hello"], project_root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Hello, World!"


def test_console_script_hello_greets_the_given_name(
    installed_venv: Path, project_root: Path
) -> None:
    script = _venv_console_script(installed_venv)
    result = _run([str(script), "hello", "Ada"], project_root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Hello, Ada!"


def test_console_script_invalid_command_exits_non_zero(
    installed_venv: Path, project_root: Path
) -> None:
    script = _venv_console_script(installed_venv)
    result = _run([str(script), "not-a-real-command"], project_root)
    assert result.returncode != 0


def test_module_invocation_matches_the_console_script(
    installed_venv: Path, project_root: Path
) -> None:
    python = _venv_python(installed_venv)
    result = _run([str(python), "-m", _PACKAGE_NAME, "hello", "Ada"], project_root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Hello, Ada!"


def test_generated_cli_project_passes_its_own_check(project_root: Path) -> None:
    """The generated `cli.py`/`__main__.py`/`test_cli.py` clear Foundation's
    own quality gate (Ruff format/lint, mypy --strict, pytest) -- not just
    that they build and import."""
    _stage(project_root)

    sync = _run(["uv", "sync", "--all-groups"], project_root)
    assert sync.returncode == 0, sync.stderr

    check = _run(["uv", "run", "poe", "check"], project_root)
    assert check.returncode == 0, check.stdout + check.stderr
