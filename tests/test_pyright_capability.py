"""Fast production-catalogue checks for the pyright capability (FT-17.03)."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import yaml

from forge_template import (
    ComponentOwner,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)
from forge_template.github_actions import check_action_pins

_COMPONENT = (
    Path(__file__).parents[1] / "src" / "forge_template" / "components" / "pyright"
)


def _payload(
    *,
    capabilities: tuple[str, ...] = ("pyright",),
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
            "name": "Typed Project",
            "package_name": "typed_project",
            "repository_name": "typed-project",
            "description": "pyright capability fixture.",
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


def test_discovery_exposes_optionless_pyright() -> None:
    pyright = next(d for d in discover_components() if d.id == "pyright")
    assert pyright.kind == "capability"
    assert pyright.version == "1.0.0"
    assert pyright.options == ()
    assert pyright.requires == ()


def test_owns_pyrightconfig_and_contributes_task_and_check() -> None:
    plan = plan_generation(parse_project_spec(_payload()))
    by_target = {item.target: item for item in plan.files}
    assert by_target["pyrightconfig.json"].owner == ComponentOwner(id="pyright")

    pyproject = tomllib.loads(_render()["pyproject.toml"].decode())
    tasks = pyproject["tool"]["poe"]["tasks"]
    assert tasks["typecheck"] == "mypy ."
    assert tasks["typecheck:pyright"] == "pyright"
    assert tasks["check"][-1] == "typecheck:pyright"
    assert "pyright>=1.1.390,<2" in pyproject["dependency-groups"]["dev"]


def test_pyrightconfig_is_valid_json_at_the_python_floor() -> None:
    config = json.loads(_render()["pyrightconfig.json"].decode())
    assert config["pythonVersion"] == "3.11"
    assert config["typeCheckingMode"] == "basic"
    assert config["include"] == ["src", "tests"]


def test_pyright_ci_job_is_present_and_pinned() -> None:
    ci = _render(platforms=("github",))[".github/workflows/ci.yml"]
    document = yaml.safe_load(ci.decode())
    assert "type-check-pyright" in document["jobs"]
    job = document["jobs"]["type-check-pyright"]
    assert job["runs-on"] == "ubuntu-latest"
    steps = " ".join(s.get("run", "") for s in job["steps"])
    assert "uv run poe typecheck:pyright" in steps


def test_pyright_ci_content_passes_the_action_pin_check(tmp_path: Path) -> None:
    ci = _render(platforms=("github",))[".github/workflows/ci.yml"]
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_bytes(ci)
    assert check_action_pins(workflows) == []


def test_omitting_pyright_leaves_no_trace() -> None:
    files = _render(capabilities=(), platforms=("github",))
    assert "pyrightconfig.json" not in files
    pyproject = tomllib.loads(files["pyproject.toml"].decode())
    assert "typecheck:pyright" not in pyproject["tool"]["poe"]["tasks"]
    document = yaml.safe_load(files[".github/workflows/ci.yml"].decode())
    assert "type-check-pyright" not in document["jobs"]


def test_component_owns_only_its_config() -> None:
    content = _COMPONENT / "content"
    assert [
        path.relative_to(content).as_posix()
        for path in content.rglob("*")
        if path.is_file()
    ] == ["pyrightconfig.json.jinja"]
