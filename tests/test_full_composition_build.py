"""Full-composition build proof -- FT-17.05 / ADR 0066.

No `archetype`-marked test before this one selected the `github` platform or
any of the eight FT-17.03 tooling capabilities -- every existing build module
hardcodes ``"platforms": []`` and uses only ``jupyter`` / ``scientific-python``
(see docs/provider-acceptance-validation.md). So `coverage`'s CI gate,
`pyright`'s type-check task, and a real `pre-commit run --all-files` had never
executed against engine-rendered output at all, and invariant 1 (generated
output is pre-commit clean) had never been checked on the engine path.

Three cells, one per archetype, each with ``github`` and every capability it
can carry (``renovate`` is excluded -- it conflicts with the ``dependabot``
cell here uses; ``documentation`` is ``library``-only, since it ``requires``
``library``). Each cell: lock, sync, build (wheel + sdist), isolated install,
the generated project's own locked ``poe check``, then a real
``git init`` + ``pre-commit run --all-files``, then the Forge-freedom probe
(row G2) at both build time (the lockfile) and install time (the venv).

``archetype``-marked (``uv run poe archetype -n 4``): each cell is a real
network-bound `uv lock`/`uv sync`/`uv build` plus a `pre-commit` run that
clones four remote hook repositories on first use.
"""

from __future__ import annotations

import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from forge_template import parse_project_spec, render_project
from tests.conftest import run_cmd

if TYPE_CHECKING:
    from forge_template import ProjectSpec

pytestmark = pytest.mark.archetype

_VERSION = "0.1.0"

#: Every FT-17.03 capability `library` can carry. `renovate` is left out --
#: it conflicts with `dependabot`, which exercises the `github`-requires edge
#: instead (docs/dependency-updates.md).
_LIBRARY_CAPABILITIES = (
    "changelog",
    "coverage",
    "dependabot",
    "documentation",
    "dotenv-example",
    "jupyter",
    "pre-commit",
    "pyright",
    "scientific-python",
)
#: `documentation` requires `library` (docs/platform-and-tooling-parity.md);
#: every other capability composes with `cli` and `data-science` unchanged.
_NON_LIBRARY_CAPABILITIES = tuple(
    capability for capability in _LIBRARY_CAPABILITIES if capability != "documentation"
)

_CELLS = [
    pytest.param("library", "full_comp_library", _LIBRARY_CAPABILITIES, id="library"),
    pytest.param("cli", "full_comp_cli", _NON_LIBRARY_CAPABILITIES, id="cli"),
    pytest.param(
        "data-science",
        "full_comp_data_science",
        _NON_LIBRARY_CAPABILITIES,
        id="data-science",
    ),
]

# Coverage's gate defaults to disabled (fail_under=0); 80 makes row G1's
# "including the ... coverage ... gate" a real assertion rather than a no-op.
# Measured 100% on every cell's trivial generated smoke test.
_COVERAGE_FAIL_UNDER = 80


def _spec(
    archetype: str, package_name: str, capabilities: tuple[str, ...]
) -> ProjectSpec:
    options: dict[str, dict[str, object]] = {
        "github": {"organisation": "full-comp-org"},
        "coverage": {"fail_under": _COVERAGE_FAIL_UNDER},
    }
    if archetype == "library":
        options["library"] = {
            "packaging_mode": "uv-build-static",
            "initial_version": _VERSION,
        }
        options["documentation"] = {"site_name": "Full Composition"}
    return parse_project_spec(
        {
            "protocol_version": 1,
            "project": {
                "name": f"Full Composition {archetype.title()}",
                "package_name": package_name,
                "repository_name": package_name.replace("_", "-"),
                "description": "FT-17.05 full-composition build fixture.",
                "licence": "mit",
                "authors": [{"name": "Test User", "email": "test@example.invalid"}],
            },
            "python": {"minimum": "3.11", "development": "3.13"},
            "components": {
                "archetype": archetype,
                "capabilities": list(capabilities),
                "platforms": ["github"],
            },
            "component_options": {
                component_id: value
                for component_id, value in options.items()
                if component_id == archetype
                or component_id in capabilities
                or component_id == "github"
            },
        }
    )


def _stage(spec: ProjectSpec, root: Path) -> None:
    for item in render_project(spec).files:
        path = root / item.target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.content)


def _is_windows_venv(venv: Path) -> bool:
    return (venv / "Scripts").is_dir()


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if _is_windows_venv(venv) else "bin/python")


def _forge_free_probe(package_name: str) -> str:
    return (
        f"import {package_name}\n"
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


@pytest.mark.parametrize(("archetype", "package_name", "capabilities"), _CELLS)
def test_full_composition_builds_installs_checks_and_is_pre_commit_clean(
    archetype: str,
    package_name: str,
    capabilities: tuple[str, ...],
    tmp_path: Path,
) -> None:
    """Row G1 (docs/cutover-compatibility-and-acceptance.md#the-acceptance-matrix):
    a project with `github` and selected capabilities builds, installs, and
    passes its own `poe check` -- including the type-check (`pyright`),
    coverage, and pre-commit gates. Also proves row G2 (Forge-freedom) for
    the first time against a maximal, not minimal, composition.
    """
    project = tmp_path / "project"
    project.mkdir()
    spec = _spec(archetype, package_name, capabilities)
    _stage(spec, project)

    lock = run_cmd(["uv", "lock"], project)
    assert lock.returncode == 0, lock.stdout + lock.stderr

    sync = run_cmd(["uv", "sync", "--all-groups", "--locked"], project)
    assert sync.returncode == 0, sync.stdout + sync.stderr

    build = run_cmd(["uv", "build"], project)
    assert build.returncode == 0, build.stdout + build.stderr
    dist = project / "dist"
    wheels = list(dist.glob("*.whl"))
    sdists = list(dist.glob("*.tar.gz"))
    assert len(wheels) == 1, wheels
    assert len(sdists) == 1, sdists
    wheel = wheels[0]
    with tarfile.open(sdists[0]) as archive:
        sdist_names = archive.getnames()
    assert any(f"{package_name}/__init__.py" in name for name in sdist_names)

    venv = tmp_path / "install-check"
    assert (
        run_cmd(["uv", "venv", "--python", "3.13", str(venv)], project).returncode == 0
    )
    install = run_cmd(
        ["uv", "pip", "install", "--python", str(venv), str(wheel)], project
    )
    assert install.returncode == 0, install.stdout + install.stderr

    python = _venv_python(venv)
    reported = run_cmd(
        [str(python), "-c", f"import {package_name} as m\nprint(m.__version__)\n"],
        project,
    )
    assert reported.returncode == 0, reported.stdout + reported.stderr
    assert reported.stdout.strip() == _VERSION

    # Row G1's full point: coverage, typecheck:pyright, and (jupyter cells)
    # notebook:check all run for the first time via the aggregate `check`.
    check = run_cmd(["uv", "run", "--locked", "poe", "check"], project)
    assert check.returncode == 0, check.stdout + check.stderr

    # Invariant 1, checked on the engine path for the first time: a real
    # `git init` + `pre-commit run --all-files` over the rendered tree.
    assert run_cmd(["git", "init"], project).returncode == 0
    assert run_cmd(["git", "add", "-A"], project).returncode == 0
    precommit = run_cmd(["uv", "run", "pre-commit", "run", "--all-files"], project)
    assert precommit.returncode == 0, precommit.stdout + precommit.stderr

    # Row G2, build-time half: no Forge distribution in the lock.
    locked = (project / "uv.lock").read_text(encoding="utf-8")
    assert "forge-template" not in locked
    assert "create-forge" not in locked

    # Row G2, install-time half: a clean venv imports the package with
    # neither `forge_template` nor its distribution present.
    forge_free_venv = tmp_path / "forge-free"
    assert run_cmd(["uv", "venv", str(forge_free_venv)], project).returncode == 0
    forge_free_install = run_cmd(
        ["uv", "pip", "install", "--python", str(forge_free_venv), str(wheel)], project
    )
    assert forge_free_install.returncode == 0, forge_free_install.stderr
    forge_free_python = _venv_python(forge_free_venv)
    probe = run_cmd(
        [str(forge_free_python), "-c", _forge_free_probe(package_name)], project
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr
    assert probe.stdout.strip() == "forge-free"
