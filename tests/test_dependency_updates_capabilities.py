"""Fast production-catalogue checks for the dependabot / renovate pair (FT-17.03).

These two capabilities carry the first production ``requires`` (``dependabot``
needs ``github``) and ``conflicts`` (each excludes the other) edges.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from forge_template import (
    ComponentOwner,
    EngineErrorCode,
    ForgeEngineError,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)

_COMPONENTS = Path(__file__).parents[1] / "src" / "forge_template" / "components"


def _payload(
    *,
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
) -> dict[str, object]:
    options: dict[str, object] = {
        "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"}
    }
    if "github" in platforms:
        options["github"] = {"organisation": "reference-org"}
    return {
        "protocol_version": 1,
        "project": {
            "name": "Updated Project",
            "package_name": "updated_project",
            "repository_name": "updated-project",
            "description": "dependency-update capability fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": "library",
            "capabilities": list(capabilities),
            "platforms": list(platforms),
        },
        "component_options": options,
    }


def _render(**kwargs: object) -> dict[str, bytes]:
    spec = parse_project_spec(_payload(**kwargs))  # type: ignore[arg-type]
    return {item.target: item.content for item in render_project(spec).files}


def test_discovery_exposes_the_edged_pair() -> None:
    by_id = {d.id: d for d in discover_components()}
    dependabot = by_id["dependabot"]
    renovate = by_id["renovate"]

    assert dependabot.version == renovate.version == "1.0.0"
    assert [(r.id, str(r.version)) for r in dependabot.requires] == [
        ("github", "<2,>=1")
    ]
    assert [r.id for r in dependabot.conflicts] == ["renovate"]
    assert renovate.requires == ()
    assert [r.id for r in renovate.conflicts] == ["dependabot"]


def test_dependabot_renders_the_config_when_github_is_selected() -> None:
    files = _render(capabilities=("dependabot",), platforms=("github",))
    plan = plan_generation(
        parse_project_spec(
            _payload(capabilities=("dependabot",), platforms=("github",))
        )
    )
    by_target = {item.target: item for item in plan.files}
    assert by_target[".github/dependabot.yml"].owner == ComponentOwner(id="dependabot")

    document = yaml.safe_load(files[".github/dependabot.yml"].decode())
    ecosystems = {entry["package-ecosystem"] for entry in document["updates"]}
    assert ecosystems == {"uv", "github-actions"}


def test_renovate_renders_host_agnostic_config() -> None:
    files = _render(capabilities=("renovate",))
    assert ".github/dependabot.yml" not in files
    config = json.loads(files["renovate.json"].decode())
    assert config["$schema"] == "https://docs.renovatebot.com/renovate-schema.json"


def test_dependabot_without_github_rejects_as_validate() -> None:
    spec = parse_project_spec(_payload(capabilities=("dependabot",)))
    for call in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as caught:
            call(spec)
        assert caught.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
        assert caught.value.operation == "validate"


def test_selecting_both_updaters_rejects_as_validate() -> None:
    spec = parse_project_spec(
        _payload(capabilities=("dependabot", "renovate"), platforms=("github",))
    )
    for call in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as caught:
            call(spec)
        assert caught.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
        assert caught.value.operation == "validate"


def test_neither_updater_reproduces_copiers_none_answer() -> None:
    files = _render(platforms=("github",))
    assert ".github/dependabot.yml" not in files
    assert "renovate.json" not in files


def test_components_own_only_their_config_files() -> None:
    assert [
        p.relative_to(_COMPONENTS / "dependabot" / "content").as_posix()
        for p in (_COMPONENTS / "dependabot" / "content").rglob("*")
        if p.is_file()
    ] == [".github/dependabot.yml"]
    assert [
        p.relative_to(_COMPONENTS / "renovate" / "content").as_posix()
        for p in (_COMPONENTS / "renovate" / "content").rglob("*")
        if p.is_file()
    ] == ["renovate.json"]
