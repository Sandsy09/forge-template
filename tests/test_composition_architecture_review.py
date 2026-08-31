"""Executable findings from the Stage 08 two-archetype review."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from forge_template import (
    ComponentOwner,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)

_COMPONENTS = Path(__file__).parents[1] / "src" / "forge_template" / "components"


def _payload(archetype: str) -> dict[str, object]:
    component_options: dict[str, object] = {}
    if archetype == "library":
        component_options = {
            "library": {
                "packaging_mode": "uv-build-static",
                "initial_version": "0.1.0",
            }
        }
    return {
        "protocol_version": 1,
        "project": {
            "name": "Reference Project",
            "package_name": "reference_project",
            "repository_name": "reference-project",
            "description": "Stage 08 architecture review fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": [],
            "platforms": [],
        },
        "component_options": component_options,
    }


def _rendered_files(archetype: str) -> dict[str, bytes]:
    spec = parse_project_spec(_payload(archetype))
    return {item.target: item.content for item in render_project(spec).files}


def test_independent_archetypes_keep_coincidentally_shared_files_owned() -> None:
    shared_sources = (
        "content/src/{{project.package_name}}/__init__.py.jinja",
        "content/src/{{project.package_name}}/py.typed",
        "content/tests/__init__.py",
    )
    for relative in shared_sources:
        assert (_COMPONENTS / "library" / relative).read_bytes() == (
            _COMPONENTS / "cli" / relative
        ).read_bytes()

    for archetype in ("library", "cli"):
        descriptor = next(d for d in discover_components() if d.id == archetype)
        assert descriptor.requires == ()
        assert descriptor.conflicts == ()

        spec = parse_project_spec(_payload(archetype))
        plan = plan_generation(spec)
        package_targets = (
            "src/reference_project/__init__.py",
            "src/reference_project/py.typed",
            "tests/__init__.py",
        )
        by_target = {item.target: item for item in plan.files}
        assert all(
            by_target[target].owner == ComponentOwner(id=archetype)
            for target in package_targets
        )


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_foundation_quality_configuration_is_layout_neutral(archetype: str) -> None:
    payload = tomllib.loads(_rendered_files(archetype)["pyproject.toml"].decode())

    assert "src" not in payload["tool"]["ruff"]
    assert "files" not in payload["tool"]["mypy"]
    assert "overrides" not in payload["tool"]["mypy"]
    assert "testpaths" not in payload["tool"]["pytest"]["ini_options"]
    assert payload["tool"]["poe"]["tasks"]["typecheck"] == "mypy ."


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_foundation_excludes_optional_coverage_and_pre_commit(
    archetype: str,
) -> None:
    files = _rendered_files(archetype)
    payload = tomllib.loads(files["pyproject.toml"].decode())

    dependency_groups = payload["dependency-groups"]
    assert all(
        not requirement.startswith(("pre-commit", "pytest-cov"))
        for requirements in dependency_groups.values()
        for requirement in requirements
        if isinstance(requirement, str)
    )
    assert "coverage" not in payload["tool"]
    assert not any(
        option.startswith("--cov")
        for option in payload["tool"]["pytest"]["ini_options"]["addopts"]
    )
    assert b"pre-commit install" not in files["README.md"]
    assert b"pre-commit install" not in files["CONTRIBUTING.md"]
    assert (
        b"Foundation does not install a\n`detect-private-key` hook"
        in files["SECURITY.md"]
    )


def test_archetypes_own_their_typed_distribution_classifiers() -> None:
    library = tomllib.loads(_rendered_files("library")["pyproject.toml"].decode())
    cli = tomllib.loads(_rendered_files("cli")["pyproject.toml"].decode())

    assert library["project"]["classifiers"] == ["Typing :: Typed"]
    assert cli["project"]["classifiers"] == [
        "Typing :: Typed",
        "Environment :: Console",
    ]


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_foundation_exposes_the_locked_aggregate_quality_contract(
    archetype: str,
) -> None:
    files = _rendered_files(archetype)
    payload = tomllib.loads(files["pyproject.toml"].decode())
    tasks = payload["tool"]["poe"]["tasks"]

    assert tasks["lock:check"] == "uv lock --check"
    assert tasks["check"][0] == "lock:check"
    assert b"uv sync --all-groups --locked" in files["README.md"]
    assert b"uv run --locked poe check" in files["README.md"]
    assert b"uv run --locked poe check" in files["CONTRIBUTING.md"]
