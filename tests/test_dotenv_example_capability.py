"""Fast production-catalogue checks for the dotenv-example capability (FT-17.03)."""

from __future__ import annotations

from pathlib import Path

from forge_template import (
    ComponentOwner,
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
    / "dotenv-example"
)


def _payload(
    *, capabilities: tuple[str, ...] = ("dotenv-example",)
) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Env Project",
            "package_name": "env_project",
            "repository_name": "env-project",
            "description": "dotenv-example capability fixture.",
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


def test_discovery_exposes_optionless_dotenv_example() -> None:
    dotenv = next(d for d in discover_components() if d.id == "dotenv-example")
    assert dotenv.kind == "capability"
    assert dotenv.version == "1.0.0"
    assert dotenv.options == ()


def test_owns_env_example_and_contributes_readme_guidance() -> None:
    plan = plan_generation(parse_project_spec(_payload()))
    by_target = {item.target: item for item in plan.files}
    assert by_target[".env.example"].owner == ComponentOwner(id="dotenv-example")

    contributed = {
        extension.extension_point
        for item in plan.files
        for extension in item.extensions
        if extension.component_id == "dotenv-example"
    }
    assert contributed == {"readme-project-shape"}


def test_env_example_is_placeholder_only() -> None:
    files = _render()
    lines = files[".env.example"].decode().splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # A placeholder line ends at the `=`; no value follows.
        assert stripped.endswith("="), line
    assert b"## Environment variables" in files["README.md"]


def test_omitting_dotenv_example_leaves_no_trace() -> None:
    files = _render(capabilities=())
    assert ".env.example" not in files
    assert b"## Environment variables" not in files["README.md"]


def test_component_owns_only_the_example_file() -> None:
    content = _COMPONENT / "content"
    assert [
        path.relative_to(content).as_posix()
        for path in content.rglob("*")
        if path.is_file()
    ] == [".env.example"]
