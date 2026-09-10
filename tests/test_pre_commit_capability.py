"""Fast production-catalogue checks for the pre-commit capability (FT-17.03)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

from forge_template import (
    ComponentOwner,
    FoundationOwner,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)

_COMPONENT = (
    Path(__file__).parents[1] / "src" / "forge_template" / "components" / "pre-commit"
)


def _payload(*, capabilities: tuple[str, ...] = ("pre-commit",)) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Hooked Project",
            "package_name": "hooked_project",
            "repository_name": "hooked-project",
            "description": "pre-commit capability fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": "library",
            "capabilities": list(capabilities),
            "platforms": [],
        },
        "component_options": {
            "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"}
        },
    }


def _render(**kwargs: object) -> dict[str, bytes]:
    spec = parse_project_spec(_payload(**kwargs))  # type: ignore[arg-type]
    return {item.target: item.content for item in render_project(spec).files}


def test_discovery_exposes_optionless_pre_commit() -> None:
    pre_commit = next(d for d in discover_components() if d.id == "pre-commit")
    assert pre_commit.kind == "capability"
    assert pre_commit.version == "1.0.0"
    assert pre_commit.options == ()
    assert pre_commit.requires == ()
    assert pre_commit.conflicts == ()


def test_owns_the_config_and_contributes_the_dependency() -> None:
    plan = plan_generation(parse_project_spec(_payload()))
    by_target = {item.target: item for item in plan.files}
    assert by_target[".pre-commit-config.yaml"].owner == ComponentOwner(id="pre-commit")
    assert isinstance(by_target["pyproject.toml"].owner, FoundationOwner)

    pyproject = tomllib.loads(_render()["pyproject.toml"].decode())
    assert "pre-commit>=4,<5" in pyproject["dependency-groups"]["dev"]


def test_config_is_valid_yaml_with_the_expected_hooks() -> None:
    document = yaml.safe_load(_render()[".pre-commit-config.yaml"].decode())
    repos = {repo["repo"] for repo in document["repos"]}
    assert "https://github.com/astral-sh/ruff-pre-commit" in repos
    assert "https://github.com/compilerla/conventional-pre-commit" in repos
    assert document["default_language_version"]["python"] == "python3.13"


def test_omitting_pre_commit_leaves_no_trace() -> None:
    files = _render(capabilities=())
    assert ".pre-commit-config.yaml" not in files
    pyproject = tomllib.loads(files["pyproject.toml"].decode())
    assert not any(
        requirement.startswith("pre-commit")
        for group in pyproject["dependency-groups"].values()
        for requirement in group
        if isinstance(requirement, str)
    )


def test_component_owns_only_its_config() -> None:
    content = _COMPONENT / "content"
    assert [
        path.relative_to(content).as_posix()
        for path in content.rglob("*")
        if path.is_file()
    ] == [".pre-commit-config.yaml.jinja"]
