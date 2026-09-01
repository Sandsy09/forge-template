"""Executable proof of the no-copy downstream inheritance contract."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Any

import pytest

import forge_template.engine as engine_module
from forge_template import (
    ComponentOwner,
    FoundationOwner,
    GenerationPlan,
    PlannedExtension,
    PlannedFile,
    ProjectSpec,
    RenderedProject,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)
from tests.no_copy_downstream import generate_from_policies
from tests.organisation_policy_contract import ExplicitSelection

COMPONENT_FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"
FOUNDATION_FIXTURE = Path(__file__).parent / "fixtures" / "foundation"
DOWNSTREAM_HARNESS = Path(__file__).parent / "no_copy_downstream.py"
POLICY_FIXTURES = Path(__file__).parent / "fixtures" / "organisation_policies"


def _payload(
    *,
    archetype: str,
    component_options: dict[str, dict[str, Any]],
) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "No-copy Fixture",
            "package_name": "no_copy_fixture",
            "repository_name": "no-copy-fixture",
            "description": "A neutral downstream-generation fixture.",
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


def _direct_generation(
    payload: dict[str, object],
) -> tuple[ProjectSpec, GenerationPlan, RenderedProject]:
    spec = parse_project_spec(payload)
    return spec, plan_generation(spec), render_project(spec)


def _files(project: RenderedProject) -> dict[str, bytes]:
    return {rendered.target: rendered.content for rendered in project.files}


def _planned_files(plan: GenerationPlan) -> dict[str, PlannedFile]:
    return {planned.target: planned for planned in plan.files}


def _assert_no_forge_runtime_dependency(project: RenderedProject) -> None:
    pyproject = tomllib.loads(_files(project)["pyproject.toml"].decode("utf-8"))
    runtime_dependencies = pyproject["project"].get("dependencies", [])
    assert all(
        not dependency.lower().startswith(("forge-template", "create-forge"))
        for dependency in runtime_dependencies
    )


def test_production_policy_and_direct_clients_render_identically() -> None:
    """Policy provenance cannot change output for one effective ProjectSpec."""

    payload = _payload(
        archetype="library",
        component_options={
            "library": {
                "packaging_mode": "uv-build-static",
                "initial_version": "0.1.0",
            }
        },
    )
    direct_spec, direct_plan, direct_project = _direct_generation(payload)
    downstream = generate_from_policies(
        payload,
        policy_names=("example-production-library",),
        explicit=ExplicitSelection(
            archetype="library",
            capabilities=frozenset(),
            platforms=frozenset(),
        ),
    )

    assert downstream.spec.model_dump(exclude={"provenance"}) == direct_spec.model_dump(
        exclude={"provenance"}
    )
    assert downstream.spec.provenance.policies == ("example-production-library",)
    assert direct_spec.provenance.policies == ()
    assert downstream.plan == direct_plan
    assert downstream.project == direct_project
    assert _files(downstream.project) == _files(direct_project)

    planned = _planned_files(downstream.plan)
    assert isinstance(planned["pyproject.toml"].owner, FoundationOwner)
    assert all(
        isinstance(file.owner, FoundationOwner)
        or file.owner == ComponentOwner(id="library")
        for file in downstream.plan.files
    )
    assert any(
        file.owner == ComponentOwner(id="library") for file in downstream.plan.files
    )
    _assert_no_forge_runtime_dependency(downstream.project)


def test_fixture_policy_adds_only_declared_component_contributions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Private fixtures prove additive composition, never a public plugin seam."""

    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", COMPONENT_FIXTURES)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", FOUNDATION_FIXTURE)
    payload = _payload(
        archetype="library-v2",
        component_options={
            "library-v2": {"initial_version": "0.1.0"},
            "github": {"organisation": "example-org"},
        },
    )
    base_payload = _payload(
        archetype="library-v2",
        component_options={"library-v2": {"initial_version": "0.1.0"}},
    )
    _, base_plan, base_project = _direct_generation(base_payload)
    downstream = generate_from_policies(
        payload,
        policy_names=("example-no-copy-inheritance",),
        explicit=ExplicitSelection(),
        catalogue=discover_components(),
    )

    assert downstream.plan.component_order == ("library-v2", "coverage", "github")
    planned = _planned_files(downstream.plan)
    assert planned["pyproject.toml"].owner == FoundationOwner()
    assert planned["pyproject.toml"].extensions == (
        PlannedExtension(
            component_id="library-v2", extension_point="pyproject-build-system"
        ),
    )
    assert planned[".coveragerc"].owner == ComponentOwner(id="coverage")
    assert planned["ci.yml"].owner == ComponentOwner(id="github")
    assert planned["ci.yml"].extensions == (
        PlannedExtension(component_id="coverage", extension_point="ci-steps"),
    )

    base_files = _files(base_project)
    downstream_files = _files(downstream.project)
    assert set(downstream_files) - set(base_files) == {".coveragerc", "ci.yml"}
    assert {target: downstream_files[target] for target in base_files} == base_files
    assert _planned_files(base_plan)["pyproject.toml"].owner == FoundationOwner()
    _assert_no_forge_runtime_dependency(downstream.project)


def test_downstream_harness_uses_only_supported_engine_imports_and_policy_data() -> (
    None
):
    """The conceptual client carries policy, not copied engine content."""

    source = DOWNSTREAM_HARNESS.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert "create_forge" not in imported_modules
    assert "forge_template" in imported_modules
    assert all(
        module == "forge_template" or not module.startswith("forge_template.")
        for module in imported_modules
    )
    assert "_CATALOGUE_ROOT_OVERRIDE" not in source
    assert "_FOUNDATION_ROOT_OVERRIDE" not in source
    assert "component_manifests" not in source
    assert {path.suffix for path in POLICY_FIXTURES.iterdir()} == {".json"}


def test_repeated_downstream_generation_is_deterministic() -> None:
    payload = _payload(
        archetype="library",
        component_options={
            "library": {
                "packaging_mode": "uv-build-static",
                "initial_version": "0.1.0",
            }
        },
    )
    explicit = ExplicitSelection(
        archetype="library",
        capabilities=frozenset(),
        platforms=frozenset(),
    )

    first = generate_from_policies(
        payload,
        policy_names=("example-production-library",),
        explicit=explicit,
    )
    second = generate_from_policies(
        payload,
        policy_names=("example-production-library",),
        explicit=explicit,
    )
    assert first == second
    _assert_no_forge_runtime_dependency(first.project)
