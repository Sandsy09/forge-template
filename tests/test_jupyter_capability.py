"""Fast production-catalogue checks for the Jupyter capability."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from forge_template import (
    ComponentOwner,
    EngineErrorCode,
    ForgeEngineError,
    FoundationOwner,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)

_COMPONENT = (
    Path(__file__).parents[1] / "src" / "forge_template" / "components" / "jupyter"
)


def _payload(archetype: str, *, selected: bool = True) -> dict[str, object]:
    options: dict[str, object] = {}
    if archetype == "library":
        options["library"] = {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        }
    return {
        "protocol_version": 1,
        "project": {
            "name": "Notebook Project",
            "package_name": "notebook_project",
            "repository_name": "notebook-project",
            "description": "Jupyter capability fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": ["jupyter"] if selected else [],
            "platforms": [],
        },
        "component_options": options,
    }


def _render(archetype: str, *, selected: bool = True) -> dict[str, bytes]:
    spec = parse_project_spec(_payload(archetype, selected=selected))
    return {item.target: item.content for item in render_project(spec).files}


def test_discovery_exposes_path_free_immutable_jupyter_descriptor() -> None:
    descriptors = discover_components()

    assert [descriptor.id for descriptor in descriptors] == [
        "cli",
        "jupyter",
        "library",
    ]
    jupyter = descriptors[1]
    assert jupyter.name == "Jupyter"
    assert (
        jupyter.description == "Notebook authoring, execution, and validation tooling."
    )
    assert jupyter.kind == "capability"
    assert jupyter.version == "1.0.0"
    assert jupyter.projectspec_protocols == (1,)
    assert jupyter.requires_python == ">=3.11"
    assert jupyter.requires == ()
    assert jupyter.conflicts == ()
    assert jupyter.options == ()
    assert "content_root" not in jupyter.model_dump_json()
    assert "resource" not in jupyter.model_dump_json()

    with pytest.raises(ValidationError):
        jupyter.name = "Changed"


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_jupyter_plan_owns_only_its_script_and_extensions(archetype: str) -> None:
    spec = parse_project_spec(_payload(archetype))
    plan = plan_generation(spec)

    assert plan.component_order == (archetype, "jupyter")
    by_target = {item.target: item for item in plan.files}
    assert by_target["scripts/check_notebooks.py"].owner == ComponentOwner(id="jupyter")

    for target in ("pyproject.toml", "README.md", ".gitignore"):
        assert by_target[target].owner == FoundationOwner()

    jupyter_extensions = {
        extension.extension_point
        for item in plan.files
        for extension in item.extensions
        if extension.component_id == "jupyter"
    }
    assert jupyter_extensions == {
        "gitignore-project-shape",
        "pyproject-aggregate-check",
        "pyproject-development-dependencies",
        "pyproject-task-definitions",
        "readme-project-shape",
    }


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_jupyter_contributes_development_tooling_without_runtime_dependencies(
    archetype: str,
) -> None:
    files = _render(archetype)
    pyproject = tomllib.loads(files["pyproject.toml"].decode())

    assert pyproject["project"]["dependencies"] == (
        [] if archetype == "library" else ["typer>=0.27,<1"]
    )
    assert pyproject["dependency-groups"]["dev"][-4:] == [
        "jupyterlab>=4.6,<5",
        "ipykernel>=7.3,<8",
        "nbclient>=0.11,<1",
        "nbformat>=5.11,<6",
    ]
    tasks = pyproject["tool"]["poe"]["tasks"]
    assert tasks["notebook"] == "jupyter lab"
    assert tasks["notebook:check"] == "python scripts/check_notebooks.py"
    assert tasks["check"][-1] == "notebook:check"
    assert files[".gitignore"].decode().endswith(".ipynb_checkpoints/\n")
    assert b"correctness gate, not a sandbox" in files["README.md"]
    assert "scripts/check_notebooks.py" in files
    assert not any(target.endswith(".ipynb") for target in files)


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_omitting_jupyter_preserves_the_existing_project(archetype: str) -> None:
    files = _render(archetype, selected=False)
    pyproject = tomllib.loads(files["pyproject.toml"].decode())

    assert "scripts/check_notebooks.py" not in files
    assert "notebook" not in pyproject["tool"]["poe"]["tasks"]
    assert "notebook:check" not in pyproject["tool"]["poe"]["tasks"]["check"]
    assert b".ipynb_checkpoints/" not in files[".gitignore"]


def test_jupyter_rejects_component_options() -> None:
    payload = _payload("library")
    payload["component_options"] = {
        "library": {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        },
        "jupyter": {"timeout": 1},
    }
    spec = parse_project_spec(payload)

    with pytest.raises(ForgeEngineError) as error:
        plan_generation(spec)

    assert error.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS


def test_jupyter_component_owns_no_notebook() -> None:
    content = _COMPONENT / "content"
    assert [
        path.relative_to(content).as_posix()
        for path in content.rglob("*")
        if path.is_file()
    ] == ["scripts/check_notebooks.py"]
