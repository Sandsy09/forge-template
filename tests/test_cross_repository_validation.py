"""Cross-repository Data Science compatibility validation (FT-14.02).

``crossrepo``-marked (``uv run poe crossrepo``). Pairs this repository's
working tree with a sibling ``create-forge`` checkout in one isolated virtual
environment -- both installed from local source, never PyPI -- and proves
current ``main`` on both sides works together: installed engine metadata
matches the FT-14.01 handoff table, every one of the ten valid compositions
generates through the real ``create-forge new --engine-preview`` console
script, repeated generation is byte-deterministic, the documented rejections
leave no partial destination, both Data Science compositions pass their own
generated ``poe check`` at the Python window edges, and create-forge's own
canonical ``tests/test_engine_cross_repository.py`` passes against the same
pair. See docs/cross-repository-validation.md and
docs/adr/0057-validate-the-cross-repository-data-science-line.md.

Sibling-gated: the whole module skips (via the session-scoped
``create_forge_root`` fixture in tests/conftest.py) when no ``create-forge``
checkout is found at ``../create-forge`` or ``--create-forge-root``. This is
why the marker stays out of ``.github/workflows/test-template.yml`` -- see
ADR 0057.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from forge_template.schema import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

pytestmark = pytest.mark.crossrepo

# A generation (real `uv lock` resolution) or a generated project's own
# `poe check` (which, for Data Science, executes a live Jupyter kernel) can
# legitimately take a while; this bounds a true hang without flaking on a
# slow machine or cold package cache.
_SUBPROCESS_TIMEOUT = 1800

_ANSWERS: Mapping[str, str] = {
    "project_description": "Cross-repository validation fixture.",
    "license": "mit",
    "author_name": "Cross Repo Validation",
    "author_email": "crossrepo@example.invalid",
}

# The ten valid compositions (composition-architecture-review.md, "Selection
# and ownership"), each given a filesystem-safe slug used as both the
# destination directory name and the parametrize id.
_COMPOSITIONS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("library", (), "library-none"),
    ("library", ("jupyter",), "library-jupyter"),
    ("library", ("scientific-python",), "library-scientific"),
    ("library", ("jupyter", "scientific-python"), "library-both"),
    ("cli", (), "cli-none"),
    ("cli", ("jupyter",), "cli-jupyter"),
    ("cli", ("scientific-python",), "cli-scientific"),
    ("cli", ("jupyter", "scientific-python"), "cli-both"),
    ("data-science", ("jupyter",), "data-science-jupyter"),
    ("data-science", ("jupyter", "scientific-python"), "data-science-both"),
)
_DETERMINISM_SLUGS = ("library-jupyter", "data-science-both")
_DEEP_CHECK_ENDPOINTS = ("3.11", "3.14")


@dataclass(frozen=True)
class PairedEnvironment:
    """One isolated venv with both local working trees installed by path."""

    venv: Path
    python: Path
    create_forge_script: Path


@dataclass(frozen=True)
class GeneratedProject:
    """One project generated through the real console script."""

    dest: Path
    archetype: str
    capabilities: tuple[str, ...]


def _run(
    cmd: Sequence[str],
    cwd: Path,
    *,
    env: Mapping[str, str] | None = None,
    timeout: int = _SUBPROCESS_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _is_windows_venv(venv: Path) -> bool:
    return (venv / "Scripts").is_dir()


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if _is_windows_venv(venv) else "bin/python")


def _venv_console_script(venv: Path, name: str) -> Path:
    if _is_windows_venv(venv):
        return venv / "Scripts" / f"{name}.exe"
    return venv / "bin" / name


@pytest.fixture(scope="session")
def child_env(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Subprocess environment for a real `create-forge` invocation.

    Strips `FORGE_*` (create-forge's own env-config prefix) and points
    `XDG_CONFIG_HOME` at a throwaway directory so no config on this machine
    (an org default, a saved answer) can change what gets generated. Also
    strips the venv-leak variables `uv run` sets for *this* pytest process
    (`VIRTUAL_ENV`, `UV_PROJECT_ENVIRONMENT`, `PYTHONHOME`, `PYTHONPATH`) so
    they cannot redirect the child `uv`/console-script invocations into this
    repository's own environment -- the same shape create-forge's own
    `e2e_child_env` fixture uses.
    """
    config_home = tmp_path_factory.mktemp("crossrepo-config")
    env = {k: v for k, v in os.environ.items() if not k.startswith("FORGE_")}
    for leak in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONHOME", "PYTHONPATH"):
        env.pop(leak, None)
    env["XDG_CONFIG_HOME"] = str(config_home)
    return env


@pytest.fixture(scope="session")
def paired_environment(
    tmp_path_factory: pytest.TempPathFactory, create_forge_root: Path
) -> PairedEnvironment:
    """One venv with both local working trees installed as path installs.

    `--refresh-package` for both forces a fresh build from current source
    even if uv's cache holds an older archive from a previous session --
    the same stale-local-build caveat create-forge's own
    docs/engine-contract-tests.md documents for `uv run --with <path>`.
    """
    venv = tmp_path_factory.mktemp("crossrepo") / ".venv"
    created = _run(["uv", "venv", "--python", "3.13", str(venv)], REPO_ROOT)
    assert created.returncode == 0, created.stdout + created.stderr

    python = _venv_python(venv)
    install = _run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--refresh-package",
            "forge-template",
            "--refresh-package",
            "create-forge",
            str(REPO_ROOT),
            str(create_forge_root),
        ],
        REPO_ROOT,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    return PairedEnvironment(
        venv=venv,
        python=python,
        create_forge_script=_venv_console_script(venv, "create-forge"),
    )


def _generate(
    env_: PairedEnvironment,
    child_env_: Mapping[str, str],
    *,
    project_name: str,
    archetype: str,
    capabilities: Sequence[str],
    dest: Path,
    extra_data: Mapping[str, str] | None = None,
    extra_args: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    args: list[str] = [
        str(env_.create_forge_script),
        "new",
        project_name,
        "--engine-preview",
        "--archetype",
        archetype,
        "--yes",
        "--path",
        str(dest),
    ]
    for key, value in _ANSWERS.items():
        args += ["--data", f"{key}={value}"]
    for key, value in (extra_data or {}).items():
        args += ["--data", f"{key}={value}"]
    for capability in capabilities:
        args += ["--capability", capability]
    if not capabilities:
        args.append("--no-capabilities")
    args += list(extra_args)
    return _run(args, dest.parent, env=child_env_)


def _assert_project_shape(dest: Path) -> None:
    assert dest.is_dir()
    assert (dest / "pyproject.toml").is_file()
    packages = [p for p in (dest / "src").iterdir() if p.is_dir()]
    assert len(packages) == 1, packages
    package = packages[0]
    assert (package / "__init__.py").is_file()
    assert (package / "py.typed").is_file()
    assert (dest / "tests").is_dir()
    assert (dest / "uv.lock").is_file()
    # The engine path runs no copier.yml _tasks: create-forge adds only the
    # client-finalised lockfile before the atomic rename (ADR 0021).
    assert not (dest / ".git").exists()
    assert not (dest / ".venv").exists()
    # No `.create-forge-*` staging sibling survived finalisation.
    assert list(dest.parent.glob(".create-forge-*")) == []


@pytest.fixture(scope="session")
def generated_projects(
    tmp_path_factory: pytest.TempPathFactory,
    paired_environment: PairedEnvironment,
    child_env: Mapping[str, str],
) -> dict[str, GeneratedProject]:
    """Generate every one of the ten valid compositions exactly once."""
    root = tmp_path_factory.mktemp("crossrepo-generated")
    projects: dict[str, GeneratedProject] = {}
    for archetype, capabilities, slug in _COMPOSITIONS:
        dest = root / slug
        result = _generate(
            paired_environment,
            child_env,
            project_name=f"Crossrepo {slug}",
            archetype=archetype,
            capabilities=capabilities,
            dest=dest,
        )
        if result.returncode != 0:
            pytest.fail(
                f"create-forge new --engine-preview --archetype {archetype} "
                f"(capabilities={capabilities}) failed (exit {result.returncode}):\n"
                f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
            )
        projects[slug] = GeneratedProject(
            dest=dest, archetype=archetype, capabilities=capabilities
        )
    return projects


def _site_packages(python: Path) -> Path:
    result = _run(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return Path(result.stdout.strip())


def _direct_url(site_packages: Path, dist_info_glob: str) -> dict[str, object]:
    matches = sorted(site_packages.glob(dist_info_glob))
    assert len(matches) == 1, (dist_info_glob, matches)
    direct_url = matches[0] / "direct_url.json"
    assert direct_url.is_file(), direct_url
    payload: dict[str, object] = json.loads(direct_url.read_text(encoding="utf-8"))
    return payload


def test_the_paired_environment_installs_both_local_sources(
    paired_environment: PairedEnvironment,
) -> None:
    """Executable form of acceptance criterion 4: no unpublished registry
    dependency. Both distributions must record a `file://` source, never an
    index -- the PEP 610 `direct_url.json` every install writes.
    """
    site_packages = _site_packages(paired_environment.python)
    forge_template_url = _direct_url(site_packages, "forge_template-*.dist-info")
    create_forge_url = _direct_url(site_packages, "create_forge-*.dist-info")

    assert str(forge_template_url["url"]).startswith("file://"), forge_template_url
    assert str(create_forge_url["url"]).startswith("file://"), create_forge_url


_METADATA_PROBE = """
import json
import forge_template as ft
from create_forge import compat

components = sorted(ft.discover_components(), key=lambda d: d.id)
info = ft.get_engine_info()
payload = {
    "package_version": info.package_version,
    "projectspec_protocols": list(info.projectspec_protocols),
    "component_manifest_protocols": list(info.component_manifest_protocols),
    "component_ids": [d.id for d in components],
    "component_versions": {d.id: d.version for d in components},
    "data_science_requires": [
        [requirement.id, str(requirement.version)]
        for d in components
        if d.id == "data-science"
        for requirement in d.requires
    ],
    "supported_engine_range": compat.SUPPORTED_ENGINE_RANGE,
}
print(json.dumps(payload))
"""


def test_installed_engine_metadata_matches_the_reviewed_candidate(
    paired_environment: PairedEnvironment,
) -> None:
    """Pins the FT-14.01 handoff table
    (composition-architecture-review.md#compatibility-and-ft-1402-handoff)
    against the *installed, paired* engine, not the in-tree one
    `tests/test_compatibility_policy.py` already covers.
    """
    result = _run([str(paired_environment.python), "-c", _METADATA_PROBE], REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert payload["package_version"] == "0.4.0"
    assert payload["projectspec_protocols"] == [1]
    assert payload["component_manifest_protocols"] == [1, 2]
    assert payload["component_ids"] == [
        "cli",
        "data-science",
        "jupyter",
        "library",
        "scientific-python",
    ]
    assert payload["component_versions"] == {
        "cli": "1.0.1",
        "data-science": "1.0.0",
        "jupyter": "1.0.0",
        "library": "1.0.1",
        "scientific-python": "1.0.0",
    }
    assert payload["data_science_requires"] == [["jupyter", "<2,>=1"]]

    installed = Version(payload["package_version"])
    assert installed in SpecifierSet(payload["supported_engine_range"])


@pytest.mark.parametrize("slug", [composition[2] for composition in _COMPOSITIONS])
def test_every_valid_composition_generates_through_the_real_console_script(
    generated_projects: dict[str, GeneratedProject],
    child_env: Mapping[str, str],
    slug: str,
) -> None:
    project = generated_projects[slug]
    _assert_project_shape(project.dest)

    lock_check = _run(["uv", "lock", "--check"], project.dest, env=child_env)
    assert lock_check.returncode == 0, lock_check.stdout + lock_check.stderr

    pyproject_text = (project.dest / "pyproject.toml").read_text(encoding="utf-8")
    lock_text = (project.dest / "uv.lock").read_text(encoding="utf-8")
    for forbidden in ("forge-template", "create-forge"):
        assert forbidden not in pyproject_text
        assert forbidden not in lock_text

    if project.archetype == "data-science":
        assert (project.dest / "notebooks" / "getting-started.ipynb").is_file()
        gitignore = (project.dest / ".gitignore").read_text(encoding="utf-8")
        for tree in (
            "/data/raw/",
            "/data/interim/",
            "/data/processed/",
            "/models/",
            "/artifacts/",
        ):
            assert tree in gitignore


@pytest.mark.parametrize("slug", _DETERMINISM_SLUGS)
def test_repeated_generation_is_byte_identical(
    generated_projects: dict[str, GeneratedProject],
    paired_environment: PairedEnvironment,
    child_env: Mapping[str, str],
    tmp_path: Path,
    slug: str,
) -> None:
    """Regenerates one Library and one Data Science composition into a fresh
    destination and compares every rendered byte against the fixture's first
    render. `uv.lock` is excluded -- it is a network-resolved client
    artefact, not a rendered byte the engine controls.
    """
    first = generated_projects[slug]
    archetype, capabilities, _ = next(c for c in _COMPOSITIONS if c[2] == slug)
    second_dest = tmp_path / slug
    result = _generate(
        paired_environment,
        child_env,
        project_name=f"Crossrepo {slug}",
        archetype=archetype,
        capabilities=capabilities,
        dest=second_dest,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    def _rendered_files(root: Path) -> dict[str, Path]:
        return {
            path.relative_to(root).as_posix(): path
            for path in root.rglob("*")
            if path.is_file() and path.name != "uv.lock"
        }

    first_files = _rendered_files(first.dest)
    second_files = _rendered_files(second_dest)
    assert set(first_files) == set(second_files)
    for relative, path in first_files.items():
        assert path.read_bytes() == second_files[relative].read_bytes(), relative


@dataclass(frozen=True)
class RejectionCase:
    """One request the engine or client must reject before any write."""

    archetype: str
    capabilities: tuple[str, ...]
    extra_args: tuple[str, ...]
    expect: tuple[str, ...]


_REJECTIONS = (
    pytest.param(
        RejectionCase(
            "data-science",
            (),
            ("--no-capabilities",),
            (
                "requires selected component(s): jupyter",
                "Add --capability jupyter.",
            ),
        ),
        id="data-science-explicit-no-capabilities",
    ),
    pytest.param(
        RejectionCase(
            "data-science",
            (),
            (),
            (
                "requires selected component(s): jupyter",
                "Add --capability jupyter.",
            ),
        ),
        id="data-science-missing-capability-flag",
    ),
    pytest.param(
        RejectionCase("not-a-real-archetype", (), (), ("Unknown archetype",)),
        id="unknown-archetype",
    ),
    pytest.param(
        RejectionCase(
            "library",
            (),
            (
                "--no-capabilities",
                "--component-option",
                "not-a-real-component.option=value",
            ),
            ("Unknown --component-option component",),
        ),
        id="unknown-component-option-owner",
    ),
)


@pytest.mark.parametrize("case", _REJECTIONS)
def test_expected_failures_leave_no_partial_destination(
    paired_environment: PairedEnvironment,
    child_env: Mapping[str, str],
    tmp_path: Path,
    case: RejectionCase,
) -> None:
    dest = tmp_path / "rejected"
    args = [
        str(paired_environment.create_forge_script),
        "new",
        "Crossrepo Rejected",
        "--engine-preview",
        "--archetype",
        case.archetype,
        "--yes",
        "--path",
        str(dest),
    ]
    for key, value in _ANSWERS.items():
        args += ["--data", f"{key}={value}"]
    for capability in case.capabilities:
        args += ["--capability", capability]
    args += list(case.extra_args)

    result = _run(args, tmp_path, env=child_env)

    assert result.returncode != 0, result.stdout + result.stderr
    assert not dest.exists()
    assert list(tmp_path.glob(".create-forge-*")) == []
    normalised = " ".join((result.stdout + result.stderr).split())
    for expected in case.expect:
        assert expected in normalised


def _sync_and_check(dest: Path, child_env_: Mapping[str, str]) -> None:
    sync = _run(["uv", "sync", "--all-groups", "--locked"], dest, env=child_env_)
    assert sync.returncode == 0, sync.stdout + sync.stderr
    check = _run(["uv", "run", "--locked", "poe", "check"], dest, env=child_env_)
    assert check.returncode == 0, check.stdout + check.stderr


def test_data_science_composition_passes_its_own_checks(
    generated_projects: dict[str, GeneratedProject],
    paired_environment: PairedEnvironment,
    child_env: Mapping[str, str],
) -> None:
    """Both Data Science compositions pass their generated project's own
    locked `poe check` -- including live-kernel `notebook:check` -- at the
    client default; the fuller composition also at the 3.11/3.14 Python
    window edges, proving Python compatibility through the real client
    rather than only the engine (`uv run poe archetype` already covers that).
    """
    _sync_and_check(generated_projects["data-science-jupyter"].dest, child_env)
    _sync_and_check(generated_projects["data-science-both"].dest, child_env)

    with tempfile.TemporaryDirectory() as tmp:
        for endpoint in _DEEP_CHECK_ENDPOINTS:
            dest = Path(tmp) / f"data-science-both-{endpoint}"
            result = _generate(
                paired_environment,
                child_env,
                project_name=f"Crossrepo data-science-both {endpoint}",
                archetype="data-science",
                capabilities=("jupyter", "scientific-python"),
                dest=dest,
                extra_data={"python_version": endpoint},
            )
            assert result.returncode == 0, result.stdout + result.stderr
            _sync_and_check(dest, child_env)


def test_create_forge_cross_repository_contract_passes_against_the_local_engine(
    create_forge_root: Path,
) -> None:
    """Runs create-forge's own canonical
    `tests/test_engine_cross_repository.py` against this working tree,
    using its documented sibling-checkout invocation
    (docs/engine-contract-tests.md in create-forge) with both packages
    forced to rebuild from current source.
    """
    result = _run(
        [
            "uv",
            "run",
            "--no-project",
            "--isolated",
            "--refresh-package",
            "forge-template",
            "--refresh-package",
            "create-forge",
            "--with",
            str(create_forge_root),
            "--with",
            str(REPO_ROOT),
            "--with",
            "pytest",
            "python",
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "tests/test_engine_cross_repository.py",
        ],
        create_forge_root,
    )
    assert result.returncode == 0, result.stdout + result.stderr
