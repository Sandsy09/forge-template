"""Fast production-catalogue checks for the Scientific Python capability."""

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
    Path(__file__).parents[1]
    / "src"
    / "forge_template"
    / "components"
    / "scientific-python"
)
_DEPENDENCIES = [
    "numpy>=2.4,<2.5",
    "pandas>=3.0,<4",
    "matplotlib>=3.11,<4",
    "scikit-learn>=1.9,<2",
]


def _payload(
    archetype: str,
    *,
    capabilities: tuple[str, ...] = ("scientific-python",),
) -> dict[str, object]:
    options: dict[str, object] = {}
    if archetype == "library":
        options["library"] = {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        }
    return {
        "protocol_version": 1,
        "project": {
            "name": "Scientific Project",
            "package_name": "scientific_project",
            "repository_name": "scientific-project",
            "description": "Scientific Python capability fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": list(capabilities),
            "platforms": [],
        },
        "component_options": options,
    }


def _render(
    archetype: str,
    *,
    capabilities: tuple[str, ...] = ("scientific-python",),
) -> dict[str, bytes]:
    spec = parse_project_spec(_payload(archetype, capabilities=capabilities))
    return {item.target: item.content for item in render_project(spec).files}


def test_discovery_exposes_path_free_immutable_scientific_descriptor() -> None:
    descriptors = discover_components()

    assert [descriptor.id for descriptor in descriptors] == [
        "cli",
        "jupyter",
        "library",
        "scientific-python",
    ]
    scientific = descriptors[-1]
    assert scientific.name == "Scientific Python"
    assert scientific.description == (
        "A core numerical, tabular, plotting, and machine-learning stack."
    )
    assert scientific.kind == "capability"
    assert scientific.version == "1.0.0"
    assert scientific.projectspec_protocols == (1,)
    assert scientific.requires_python == ">=3.11"
    assert scientific.requires == ()
    assert scientific.conflicts == ()
    assert scientific.options == ()
    assert "content_root" not in scientific.model_dump_json()
    assert "resource" not in scientific.model_dump_json()

    with pytest.raises(ValidationError):
        scientific.name = "Changed"


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_scientific_plan_owns_only_its_test_and_extensions(archetype: str) -> None:
    spec = parse_project_spec(_payload(archetype))
    plan = plan_generation(spec)

    assert plan.component_order == (archetype, "scientific-python")
    by_target = {item.target: item for item in plan.files}
    assert by_target["tests/test_scientific_python.py"].owner == ComponentOwner(
        id="scientific-python"
    )
    assert by_target["pyproject.toml"].owner == FoundationOwner()
    assert by_target["README.md"].owner == FoundationOwner()

    scientific_extensions = {
        extension.extension_point
        for item in plan.files
        for extension in item.extensions
        if extension.component_id == "scientific-python"
    }
    assert scientific_extensions == {
        "pyproject-runtime-dependencies",
        "readme-project-shape",
    }


@pytest.mark.parametrize("archetype", ["library", "cli"])
@pytest.mark.parametrize(
    "capabilities",
    [
        ("scientific-python",),
        ("jupyter", "scientific-python"),
    ],
)
def test_scientific_dependencies_and_test_are_independent_of_jupyter(
    archetype: str, capabilities: tuple[str, ...]
) -> None:
    files = _render(archetype, capabilities=capabilities)
    pyproject = tomllib.loads(files["pyproject.toml"].decode())
    expected = [] if archetype == "library" else ["typer>=0.27,<1"]

    assert pyproject["project"]["dependencies"] == [*expected, *_DEPENDENCIES]
    test = files["tests/test_scientific_python.py"].decode()
    for import_name in ("matplotlib", "numpy", "pandas", "sklearn"):
        assert f"import {import_name}" in test
        assert f"{import_name}.__version__" in test
    assert b"## Scientific Python" in files["README.md"]


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_omitting_scientific_python_preserves_existing_output(archetype: str) -> None:
    files = _render(archetype, capabilities=())
    pyproject = tomllib.loads(files["pyproject.toml"].decode())

    assert pyproject["project"]["dependencies"] == (
        [] if archetype == "library" else ["typer>=0.27,<1"]
    )
    assert "tests/test_scientific_python.py" not in files
    assert b"## Scientific Python" not in files["README.md"]


def test_scientific_python_rejects_component_options() -> None:
    payload = _payload("library")
    payload["component_options"] = {
        "library": {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        },
        "scientific-python": {"stack": "full"},
    }
    spec = parse_project_spec(payload)

    with pytest.raises(ForgeEngineError) as error:
        plan_generation(spec)

    assert error.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS


def test_scientific_component_owns_only_its_import_test() -> None:
    content = _COMPONENT / "content"
    assert [
        path.relative_to(content).as_posix()
        for path in content.rglob("*")
        if path.is_file()
    ] == ["tests/test_scientific_python.py"]
