"""Fast production-catalogue checks for the changelog capability (FT-17.03).

``changelog`` is the first shipped ``manifest_version = 3`` component -- its
``[[regeneration]]`` record marks ``CHANGELOG.md`` skip-if-exists.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from forge_template import (
    ComponentOwner,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)
from forge_template.component_manifest import load_component_manifest

_COMPONENT = (
    Path(__file__).parents[1] / "src" / "forge_template" / "components" / "changelog"
)


def _payload(*, capabilities: tuple[str, ...] = ("changelog",)) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Logged Project",
            "package_name": "logged_project",
            "repository_name": "logged-project",
            "description": "changelog capability fixture.",
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


def test_discovery_exposes_optionless_changelog() -> None:
    changelog = next(d for d in discover_components() if d.id == "changelog")
    assert changelog.kind == "capability"
    assert changelog.version == "1.0.0"
    assert changelog.options == ()


def test_manifest_is_protocol_three_with_a_skip_if_exists_record() -> None:
    manifest = load_component_manifest(_COMPONENT / "component.toml")
    assert manifest.manifest_version == 3
    assert len(manifest.regeneration) == 1
    record = manifest.regeneration[0]
    assert record.target == "CHANGELOG.md"
    assert record.disposition == "skip-if-exists"


def test_changelog_target_is_planned_skip_if_exists() -> None:
    plan = plan_generation(parse_project_spec(_payload()))
    by_target = {item.target: item for item in plan.files}
    changelog = by_target["CHANGELOG.md"]
    assert changelog.owner == ComponentOwner(id="changelog")
    assert changelog.regeneration == "skip-if-exists"
    # A Foundation-owned target stays `replace`.
    assert by_target["pyproject.toml"].regeneration == "replace"


def test_owns_changelog_and_cliff_config_and_contributes_task() -> None:
    files = _render()
    assert files["CHANGELOG.md"].decode().startswith("# Changelog")
    assert b"[git]" in files["cliff.toml"]

    pyproject = tomllib.loads(files["pyproject.toml"].decode())
    assert pyproject["tool"]["poe"]["tasks"]["changelog"] == (
        "git-cliff --output CHANGELOG.md"
    )
    assert "git-cliff>=2.7,<3" in pyproject["dependency-groups"]["dev"]


def test_omitting_changelog_leaves_no_trace() -> None:
    files = _render(capabilities=())
    assert "CHANGELOG.md" not in files
    assert "cliff.toml" not in files
    pyproject = tomllib.loads(files["pyproject.toml"].decode())
    assert "changelog" not in pyproject["tool"]["poe"]["tasks"]


def test_component_owns_changelog_and_cliff_only() -> None:
    content = _COMPONENT / "content"
    assert sorted(
        path.relative_to(content).as_posix()
        for path in content.rglob("*")
        if path.is_file()
    ) == ["CHANGELOG.md.jinja", "cliff.toml"]
