"""Fast production-catalogue checks for the coverage capability (FT-17.03)."""

from __future__ import annotations

from pathlib import Path

import pytest

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
    Path(__file__).parents[1] / "src" / "forge_template" / "components" / "coverage"
)


def _payload(
    *,
    capabilities: tuple[str, ...] = ("coverage",),
    platforms: tuple[str, ...] = (),
    coverage_options: dict[str, object] | None = None,
) -> dict[str, object]:
    options: dict[str, object] = {
        "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"}
    }
    if "coverage" in capabilities and coverage_options is not None:
        options["coverage"] = coverage_options
    if "github" in platforms:
        options["github"] = {"organisation": "reference-org"}
    return {
        "protocol_version": 1,
        "project": {
            "name": "Coverage Project",
            "package_name": "coverage_project",
            "repository_name": "coverage-project",
            "description": "Coverage capability fixture.",
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


def test_discovery_exposes_coverage_with_one_option() -> None:
    coverage = next(d for d in discover_components() if d.id == "coverage")
    assert coverage.kind == "capability"
    assert coverage.version == "1.0.0"
    assert coverage.requires == ()
    assert coverage.conflicts == ()
    assert [option.name for option in coverage.options] == ["fail_under"]
    assert coverage.options[0].required is False
    assert "content_root" not in coverage.model_dump_json()


def test_coverage_owns_only_its_coveragerc() -> None:
    content = _COMPONENT / "content"
    assert [
        path.relative_to(content).as_posix()
        for path in content.rglob("*")
        if path.is_file()
    ] == [".coveragerc.jinja"]


def test_plan_owns_coveragerc_and_contributes_tooling() -> None:
    plan = plan_generation(parse_project_spec(_payload()))
    by_target = {item.target: item for item in plan.files}
    assert by_target[".coveragerc"].owner == ComponentOwner(id="coverage")
    assert isinstance(by_target["pyproject.toml"].owner, FoundationOwner)

    contributed = {
        extension.extension_point
        for item in plan.files
        for extension in item.extensions
        if extension.component_id == "coverage"
    }
    assert contributed == {
        "pyproject-development-dependencies",
        "pyproject-task-definitions",
        "pyproject-aggregate-check",
    }


def test_omitting_coverage_leaves_no_trace() -> None:
    files = _render(capabilities=())
    assert ".coveragerc" not in files
    import tomllib

    pyproject = tomllib.loads(files["pyproject.toml"].decode())
    assert "coverage" not in pyproject["tool"]["poe"]["tasks"]


def test_fail_under_option_drives_the_threshold() -> None:
    without = _render()[".coveragerc"].decode()
    assert "fail_under =" not in without
    assert "No threshold enforced" in without

    with_gate = _render(coverage_options={"fail_under": 85})[".coveragerc"].decode()
    assert "fail_under = 85" in with_gate


def test_coverage_task_and_check_entry_are_added() -> None:
    import tomllib

    pyproject = tomllib.loads(_render()["pyproject.toml"].decode())
    tasks = pyproject["tool"]["poe"]["tasks"]
    assert tasks["coverage"] == "pytest --cov --cov-report=term-missing"
    assert tasks["check"][-1] == "coverage"
    assert pyproject["dependency-groups"]["dev"][-1] == "pytest-cov>=6,<8"


def test_coverage_step_reaches_the_github_test_job() -> None:
    import yaml

    ci = _render(platforms=("github",))[".github/workflows/ci.yml"].decode()
    document = yaml.safe_load(ci)
    step_names = [s.get("name", "") for s in document["jobs"]["test"]["steps"]]
    assert "Coverage" in step_names
    assert "Upload coverage" in step_names


def test_bad_fail_under_type_rejects_as_validate() -> None:
    spec = parse_project_spec(_payload(coverage_options={"fail_under": "eighty"}))
    for call in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as caught:
            call(spec)
        assert caught.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS
        assert caught.value.operation == "validate"
