"""Render-level validation for the Streamlit capability compositions.

FT-20.02 / ADR 0071. Covers the matrix rows that
``docs/streamlit-compatibility-and-acceptance.md`` assigns to FT-20.02: the four
accepted selections plan and render deterministically, contributions compose in
archetype-then-capability order, invalid selections fail closed before
rendering, and the secret and non-serving safeguards hold. The real ``uv lock``
runs live in the ``archetype``-marked ``tests/test_streamlit_resolution.py``;
build, install and the generated ``poe check`` belong to FT-20.03.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

import forge_template.engine as engine_module
from forge_template import (
    ComponentOwner,
    EngineErrorCode,
    ForgeEngineError,
    FoundationOwner,
    parse_project_spec,
    plan_generation,
    render_project,
)

_COMPONENTS = Path(__file__).parents[1] / "src" / "forge_template" / "components"

_FOUR_SELECTIONS = [
    pytest.param((), id="alone"),
    pytest.param(("jupyter",), id="jupyter"),
    pytest.param(("scientific-python",), id="scientific-python"),
    pytest.param(("jupyter", "scientific-python"), id="jupyter+scientific-python"),
]
_SECRET_IGNORE = "/.streamlit/secrets.toml"

# Everything the exclusions forbid a generated Streamlit project from declaring:
# deployment, containers, authentication, databases, any API framework, and a
# Forge runtime package.
_FORBIDDEN_DEPENDENCIES = {
    "fastapi",
    "flask",
    "django",
    "uvicorn",
    "gunicorn",
    "docker",
    "kubernetes",
    "sqlalchemy",
    "psycopg",
    "pymongo",
    "redis",
    "authlib",
    "streamlit-authenticator",
    "forge-template",
    "create-forge",
}


def _payload(
    *,
    archetype: str = "streamlit",
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
    component_options: dict[str, Any] | None = None,
) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Demo App",
            "package_name": "demo_app",
            "repository_name": "demo-app",
            "description": "A demonstration.",
            "licence": "mit",
            "authors": [{"name": "Test User", "email": "test@example.invalid"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": list(capabilities),
            "platforms": list(platforms),
        },
        "component_options": component_options or {},
    }


def _render_map(payload: dict[str, object]) -> dict[str, bytes]:
    spec = parse_project_spec(payload)
    return {item.target: item.content for item in render_project(spec).files}


def _text(capabilities: tuple[str, ...], target: str) -> str:
    return _render_map(_payload(capabilities=capabilities))[target].decode()


def _tasks(capabilities: tuple[str, ...]) -> dict[str, Any]:
    pyproject = tomllib.loads(_text(capabilities, "pyproject.toml"))
    tasks: dict[str, Any] = pyproject["tool"]["poe"]["tasks"]
    return tasks


# --- The four accepted selections plan and render ---------------------------


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_accepted_selection_plans_with_selected_owners_only(
    capabilities: tuple[str, ...],
) -> None:
    plan = plan_generation(parse_project_spec(_payload(capabilities=capabilities)))

    assert plan.component_order == ("streamlit", *sorted(capabilities))

    selected = {"streamlit", *capabilities}
    for item in plan.files:
        assert isinstance(item.owner, FoundationOwner) or (
            isinstance(item.owner, ComponentOwner) and item.owner.id in selected
        ), item.target

    by_target = {item.target: item for item in plan.files}
    assert by_target[".streamlit/config.toml"].owner == ComponentOwner(id="streamlit")
    assert by_target["app.py"].owner == ComponentOwner(id="streamlit")

    files = _render_map(_payload(capabilities=capabilities))
    assert ("scripts/check_notebooks.py" in files) is ("jupyter" in capabilities)
    assert ("tests/test_scientific_python.py" in files) is (
        "scientific-python" in capabilities
    )


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_the_configuration_is_the_one_deterministic_safeguard(
    capabilities: tuple[str, ...],
) -> None:
    files = _render_map(_payload(capabilities=capabilities))
    config = files[".streamlit/config.toml"].decode()

    assert tomllib.loads(config) == {"browser": {"gatherUsageStats": False}}
    # No other setting is preselected, and no example secrets file exists.
    assert config.count("=") == 1
    assert ".streamlit/secrets.toml.example" not in files


# --- Composition order: archetype tier first, then capabilities lexically ---


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_run_is_a_task_that_never_enters_the_aggregate_check(
    capabilities: tuple[str, ...],
) -> None:
    tasks = _tasks(capabilities)

    assert tasks["run"] == "streamlit run app.py"
    check = tasks["check"]
    assert "run" not in check
    assert ("notebook:check" in check) is ("jupyter" in capabilities)
    # `check` keeps Foundation's five steps in order, plus only what the
    # selected capability adds -- nothing from the archetype.
    assert check[:5] == ["lock:check", "format:check", "lint", "typecheck", "test"]
    assert len(check) == 5 + ("jupyter" in capabilities)


def test_run_precedes_the_notebook_tasks() -> None:
    order = list(_tasks(("jupyter",)))

    assert order.index("run") < order.index("notebook") < order.index("notebook:check")


def test_streamlit_precedes_the_scientific_runtime_dependencies() -> None:
    pyproject = tomllib.loads(_text(("scientific-python",), "pyproject.toml"))
    dependencies = pyproject["project"]["dependencies"]

    assert dependencies[0] == "streamlit>=1.63,<2"
    assert len(dependencies) > 1


def test_the_secret_ignore_entry_precedes_the_notebook_checkpoints() -> None:
    lines = _text(("jupyter",), ".gitignore").splitlines()

    assert lines.index(_SECRET_IGNORE) < lines.index(".ipynb_checkpoints/")


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_the_readme_documents_run_structure_pages_and_secrets(
    capabilities: tuple[str, ...],
) -> None:
    readme = _text(capabilities, "README.md")

    assert "uv run poe run" in readme
    assert "streamlit run app.py" in readme
    assert ".streamlit/config.toml" in readme
    assert "pages/" in readme
    assert ".streamlit/secrets.toml" in readme
    assert ".streamlit/secrets.toml.example" not in readme
    assert readme.index("## Usage") < readme.index("## Project structure")


# --- Determinism ------------------------------------------------------------


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_render_is_invariant_to_repetition_and_capability_order(
    capabilities: tuple[str, ...],
) -> None:
    first = _render_map(_payload(capabilities=capabilities))
    again = _render_map(_payload(capabilities=capabilities))
    reversed_order = _render_map(_payload(capabilities=tuple(reversed(capabilities))))

    assert first == again == reversed_order


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_render_is_invariant_to_catalogue_filesystem_layout(
    capabilities: tuple[str, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The engine sorts ``component.toml`` paths before loading them, so a fresh
    copy of the production catalogue -- a different on-disk order -- must render
    byte-identical output. Only the private test seam moves."""
    installed = _render_map(_payload(capabilities=capabilities))

    overlay = tmp_path / "components"
    shutil.copytree(_COMPONENTS, overlay)
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", overlay)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", None)

    assert _render_map(_payload(capabilities=capabilities)) == installed


@pytest.mark.parametrize("floor", ["3.11", "3.14"])
@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_rendered_python_content_is_ruff_clean_at_every_floor(
    capabilities: tuple[str, ...], floor: str, tmp_path: Path
) -> None:
    """Invariant 1 for every accepted selection, whatever supported floor the
    owner picks. 3.14 flips ``target-version`` to ``py314``, which changes how
    ruff formats ``except`` groups (PEP 758); generated content must stay clean
    at that target too. FT-20.03 / ADR 0072."""
    payload = _payload(capabilities=capabilities)
    payload["python"] = {"minimum": floor, "development": floor}
    for target, content in _render_map(payload).items():
        path = tmp_path / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    for arguments in (["format", "--check", "."], ["check", "."]):
        result = subprocess.run(
            [sys.executable, "-m", "ruff", *arguments],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_render_is_invariant_to_pythonhashseed() -> None:
    """docs/composition-order.md names PYTHONHASHSEED explicitly. A single
    pytest process has one fixed seed, so vary it across subprocesses that each
    render the richest selection and hash the file map. FT-20.03 / ADR 0072."""
    script = (
        "import hashlib, json;"
        "from forge_template import parse_project_spec, render_project;"
        "spec = parse_project_spec({"
        "'protocol_version': 1,"
        "'project': {'name': 'Demo App', 'package_name': 'demo_app',"
        " 'repository_name': 'demo-app', 'description': 'x', 'licence': 'mit',"
        " 'authors': [{'name': 'Test User'}]},"
        "'python': {'minimum': '3.11', 'development': '3.13'},"
        "'components': {'archetype': 'streamlit',"
        " 'capabilities': ['jupyter', 'scientific-python'], 'platforms': []},"
        "'component_options': {}});"
        "files = {i.target: i.content.hex() for i in render_project(spec).files};"
        "print(hashlib.sha256("
        "json.dumps(files, sort_keys=True).encode()).hexdigest())"
    )
    hashes = set()
    for seed in ("0", "1", "42", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=_COMPONENTS.parents[2],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        )
        hashes.add(result.stdout.strip())

    assert len(hashes) == 1, hashes


# --- Rejections fail closed before rendering --------------------------------

_REJECTIONS: list[tuple[str, dict[str, Any], EngineErrorCode, str]] = [
    (
        "documentation-requires-library",
        {"capabilities": ("documentation",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "dependabot-without-github",
        {"capabilities": ("dependabot",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "dependabot-with-renovate",
        {"capabilities": ("dependabot", "renovate"), "platforms": ("github",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "second-archetype-as-capability",
        {"capabilities": ("jupyter", "library")},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "streamlit-given-as-a-capability",
        {"archetype": "library", "capabilities": ("streamlit",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "capability-given-as-the-archetype",
        {"archetype": "jupyter"},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "unknown-component-alongside-jupyter",
        {"capabilities": ("jupyter", "does-not-exist")},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "jupyter-listed-twice",
        {"capabilities": ("jupyter", "jupyter")},
        EngineErrorCode.INVALID_PROJECT_SPEC,
        "parse",
    ),
    (
        "options-for-optionless-streamlit",
        {"component_options": {"streamlit": {"anything": "x"}}},
        EngineErrorCode.INVALID_COMPONENT_OPTIONS,
        "validate",
    ),
]


@pytest.mark.parametrize(
    ("_name", "kwargs", "code", "operation"),
    _REJECTIONS,
    ids=[row[0] for row in _REJECTIONS],
)
def test_documented_rejection_fails_closed_before_rendering(
    _name: str,
    kwargs: dict[str, Any],
    code: EngineErrorCode,
    operation: str,
) -> None:
    for sink in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as exc_info:
            sink(parse_project_spec(_payload(**kwargs)))
        error = exc_info.value
        assert error.code is code
        assert error.operation == operation
        assert error.operation != "render"
        assert error.details
        json.dumps(error.as_dict())


def test_optional_tooling_and_the_platform_compose_with_streamlit() -> None:
    """The remaining catalogue components need no Streamlit-specific edge."""
    files = _render_map(
        _payload(
            capabilities=("coverage", "dotenv-example", "jupyter", "pyright"),
            platforms=("github",),
            component_options={"github": {"organisation": "forge-example"}},
        )
    )

    assert "app.py" in files
    assert ".streamlit/config.toml" in files
    tomllib.loads(files["pyproject.toml"].decode())


# --- The secret safeguard ---------------------------------------------------


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_the_secrets_file_is_ignored_and_shadows_no_tracked_path(
    capabilities: tuple[str, ...],
) -> None:
    files = _render_map(_payload(capabilities=capabilities))
    ignore_lines = files[".gitignore"].decode().splitlines()

    assert ignore_lines.count(_SECRET_IGNORE) == 1
    # Root-anchored and naming the file, not the directory: it can shadow
    # nothing but that one path, and that path is never a generated target, so
    # `.streamlit/config.toml` stays trackable beside it.
    assert _SECRET_IGNORE.lstrip("/") not in files
    assert not any(target.endswith("secrets.toml") for target in files)
    assert ".streamlit/" not in ignore_lines
    assert ".streamlit" not in ignore_lines
    assert "/.streamlit/" not in ignore_lines
    for line in ignore_lines:
        if not line.strip() or line.startswith(("#", "!")) or line == _SECRET_IGNORE:
            continue
        pattern = re.escape(line.strip("/")).replace(r"\*", "[^/]*")
        for tracked in (".streamlit/config.toml", "app.py"):
            assert not re.fullmatch(pattern, tracked), (line, tracked)


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_no_generated_file_carries_a_secret(capabilities: tuple[str, ...]) -> None:
    for target, content in _render_map(_payload(capabilities=capabilities)).items():
        text = content.decode(errors="ignore").lower()
        for marker in ("api_key", "password", "secret_key", "private key", "token ="):
            assert marker not in text, (target, marker)


# --- The exclusions and the no-Forge-runtime rule ---------------------------


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_no_deployment_auth_database_or_forge_dependency_is_declared(
    capabilities: tuple[str, ...],
) -> None:
    pyproject = tomllib.loads(_text(capabilities, "pyproject.toml"))
    declared = [
        *pyproject["project"].get("dependencies", []),
        *(
            requirement
            for group in pyproject.get("dependency-groups", {}).values()
            for requirement in group
            if isinstance(requirement, str)
        ),
    ]

    for requirement in declared:
        name = re.split(r"[<>=!~;\[ ]", requirement, maxsplit=1)[0].lower()
        assert name not in _FORBIDDEN_DEPENDENCIES, requirement
    assert "streamlit>=1.63,<2" in declared


@pytest.mark.parametrize("capabilities", _FOUR_SELECTIONS)
def test_no_deployment_container_or_plugin_surface_is_generated(
    capabilities: tuple[str, ...],
) -> None:
    files = _render_map(_payload(capabilities=capabilities))

    for target in files:
        assert not target.startswith(("pages/", ".devcontainer/", ".github/")), target
        assert target not in {
            "Dockerfile",
            "docker-compose.yml",
            "compose.yaml",
            "Procfile",
            "requirements.txt",
        }
    for target, content in files.items():
        if target.endswith((".py", ".ipynb")):
            assert b"forge_template" not in content, target
            assert b"forge-template" not in content, target
            assert b"declare_component" not in content, target
    # `run` starts a local server only when the owner asks; the smoke never does.
    smoke = files["tests/test_app.py"].decode()
    assert "streamlit run" not in smoke
    assert "subprocess" not in smoke


def test_the_manifest_contributes_nine_points_and_never_the_aggregate_check() -> None:
    manifest = tomllib.loads(
        (_COMPONENTS / "streamlit" / "component.toml").read_text(encoding="utf-8")
    )

    contributed = {item["extension_point"] for item in manifest["contributions"]}
    assert len(manifest["contributions"]) == len(contributed) == 9
    assert not contributed & {"pyproject-aggregate-check", "pyproject-entry-points"}
    assert all(
        item["target"] == {"kind": "foundation"} for item in manifest["contributions"]
    )
