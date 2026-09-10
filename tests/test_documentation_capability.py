"""Fast production-catalogue checks for the documentation capability (FT-17.03).

``documentation`` requires ``library``, publishes ``api-reference`` on its own
reference page, and declares a real ``docs`` dependency group through the two
``[dependency-groups]`` Foundation points.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

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
from forge_template.component_manifest import load_component_manifest
from forge_template.github_actions import check_action_pins

_COMPONENT = (
    Path(__file__).parents[1]
    / "src"
    / "forge_template"
    / "components"
    / "documentation"
)


def _payload(
    *,
    archetype: str = "library",
    capabilities: tuple[str, ...] = ("documentation",),
    platforms: tuple[str, ...] = (),
    documentation_options: dict[str, object] | None = None,
) -> dict[str, object]:
    options: dict[str, object] = {}
    if archetype == "library":
        options["library"] = {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        }
    if "github" in platforms:
        options["github"] = {"organisation": "reference-org"}
    if "documentation" in capabilities and documentation_options is not None:
        options["documentation"] = documentation_options
    return {
        "protocol_version": 1,
        "project": {
            "name": "Documented Project",
            "package_name": "documented_project",
            "repository_name": "documented-project",
            "description": "documentation capability fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": list(capabilities),
            "platforms": list(platforms),
        },
        "component_options": options,
    }


def _render(**kwargs: object) -> dict[str, bytes]:
    spec = parse_project_spec(_payload(**kwargs))  # type: ignore[arg-type]
    return {item.target: item.content for item in render_project(spec).files}


def test_discovery_requires_library_and_has_a_site_name_option() -> None:
    documentation = next(d for d in discover_components() if d.id == "documentation")
    assert documentation.kind == "capability"
    assert documentation.version == "1.0.0"
    assert [(r.id, str(r.version)) for r in documentation.requires] == [
        ("library", "<2,>=1")
    ]
    assert [option.name for option in documentation.options] == ["site_name"]
    assert documentation.options[0].required is False


def test_publishes_api_reference_on_its_own_content() -> None:
    manifest = load_component_manifest(_COMPONENT / "component.toml")
    assert [point.id for point in manifest.extension_points] == ["api-reference"]
    assert manifest.extension_points[0].content == "content/docs/reference.md.jinja"


def test_owns_the_site_tree_and_declares_a_docs_group() -> None:
    plan = plan_generation(parse_project_spec(_payload()))
    by_target = {item.target: item for item in plan.files}
    for target in (
        "mkdocs.yml",
        "docs/index.md",
        "docs/reference.md",
        "docs/adr/README.md",
        "docs/adr/0001-record-architecture-decisions.md",
    ):
        assert by_target[target].owner == ComponentOwner(id="documentation")
    assert isinstance(by_target["pyproject.toml"].owner, FoundationOwner)

    pyproject = tomllib.loads(_render()["pyproject.toml"].decode())
    groups = pyproject["dependency-groups"]
    assert groups["docs"] == [
        "mkdocs>=1.6,<2",
        "mkdocs-material>=9.5,<10",
        "mkdocstrings[python]>=0.27,<1",
    ]
    assert {"include-group": "docs"} in groups["dev"]
    tasks = pyproject["tool"]["poe"]["tasks"]
    assert tasks["docs"] == "mkdocs serve"
    assert tasks["docs:build"] == "mkdocs build --strict"


def test_site_name_option_falls_back_to_the_project_name() -> None:
    default = yaml.safe_load(_render()["mkdocs.yml"].decode())
    assert default["site_name"] == "Documented Project"

    custom = yaml.safe_load(
        _render(documentation_options={"site_name": "Custom Docs"})[
            "mkdocs.yml"
        ].decode()
    )
    assert custom["site_name"] == "Custom Docs"


def test_reference_page_targets_the_package_and_leaves_the_marker_empty() -> None:
    reference = _render()["docs/reference.md"].decode()
    assert "::: documented_project" in reference
    assert "forge:extension" not in reference


def test_docs_job_reaches_ci_and_is_pinned(tmp_path: Path) -> None:
    ci = _render(platforms=("github",))[".github/workflows/ci.yml"]
    document = yaml.safe_load(ci.decode())
    assert "docs" in document["jobs"]
    steps = " ".join(s.get("run", "") for s in document["jobs"]["docs"]["steps"])
    assert "uv run poe docs:build" in steps

    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_bytes(ci)
    assert check_action_pins(workflows) == []


def test_mkdocs_repo_url_only_appears_with_github() -> None:
    without = yaml.safe_load(_render()["mkdocs.yml"].decode())
    assert "repo_url" not in without

    with_github = yaml.safe_load(_render(platforms=("github",))["mkdocs.yml"].decode())
    assert with_github["repo_url"] == (
        "https://github.com/reference-org/documented-project"
    )


def test_documentation_without_library_rejects_as_validate() -> None:
    spec = parse_project_spec(_payload(archetype="cli"))
    for call in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as caught:
            call(spec)
        assert caught.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
        assert caught.value.operation == "validate"


def test_omitting_documentation_leaves_no_trace() -> None:
    files = _render(capabilities=())
    assert not [t for t in files if t.startswith("docs/") or t == "mkdocs.yml"]
    pyproject = tomllib.loads(files["pyproject.toml"].decode())
    assert "docs" not in pyproject["dependency-groups"]
    assert "docs" not in pyproject["tool"]["poe"]["tasks"]
