"""Fast render-level tests for the production CLI Application archetype.

Real `uv build`/wheel/install/console-script checks live in the slow
``archetype``-marked ``tests/test_cli_build.py`` instead -- see
docs/cli-application-archetype.md.
"""

from __future__ import annotations

import tomllib

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


def _payload(
    *, component_options: dict[str, object] | None = None
) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Credit Risk CLI",
            "package_name": "credit_risk_cli",
            "repository_name": "credit-risk-cli",
            "description": "A CLI for credit risk stuff.",
            "licence": "mit",
            "authors": [{"name": "Test User", "email": "test@example.invalid"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {"archetype": "cli", "capabilities": [], "platforms": []},
        "component_options": component_options or {},
    }


def test_discovery_exposes_cli_with_library_and_capabilities() -> None:
    descriptors = discover_components()

    assert [descriptor.id for descriptor in descriptors] == [
        "cli",
        "jupyter",
        "library",
        "scientific-python",
    ]

    cli = descriptors[0]
    assert cli.kind == "archetype"
    assert cli.version == "1.0.1"
    assert cli.requires == ()
    assert cli.conflicts == ()
    assert cli.options == ()


def test_plan_identifies_foundation_and_component_owners() -> None:
    spec = parse_project_spec(_payload())

    plan = plan_generation(spec)

    assert plan.component_order == ("cli",)
    by_target = {item.target: item for item in plan.files}

    assert by_target["pyproject.toml"].owner == FoundationOwner()
    assert by_target["README.md"].owner == FoundationOwner()
    assert by_target["LICENSE"].owner == FoundationOwner()
    assert by_target["CONTRIBUTING.md"].owner == FoundationOwner()
    assert by_target["SECURITY.md"].owner == FoundationOwner()
    assert by_target[".gitignore"].owner == FoundationOwner()
    assert by_target[".gitattributes"].owner == FoundationOwner()
    assert by_target[".editorconfig"].owner == FoundationOwner()
    assert by_target[".python-version"].owner == FoundationOwner()

    assert by_target["src/credit_risk_cli/__init__.py"].owner == ComponentOwner(
        id="cli"
    )
    assert by_target["src/credit_risk_cli/__main__.py"].owner == ComponentOwner(
        id="cli"
    )
    assert by_target["src/credit_risk_cli/cli.py"].owner == ComponentOwner(id="cli")
    assert by_target["src/credit_risk_cli/py.typed"].owner == ComponentOwner(id="cli")
    assert by_target["tests/__init__.py"].owner == ComponentOwner(id="cli")
    assert by_target["tests/test_cli.py"].owner == ComponentOwner(id="cli")

    extensions = by_target["pyproject.toml"].extensions
    assert {e.extension_point for e in extensions} == {
        "pyproject-build-system",
        "pyproject-archetype-metadata",
        "pyproject-build-configuration",
        "pyproject-runtime-dependencies",
        "pyproject-classifiers",
        "pyproject-entry-points",
    }
    assert all(e.component_id == "cli" for e in extensions)


def test_rendered_pyproject_matches_the_cli_contract() -> None:
    spec = parse_project_spec(_payload())

    rendered = render_project(spec)
    files = {item.target: item.content for item in rendered.files}

    payload = tomllib.loads(files["pyproject.toml"].decode())
    assert payload["project"]["name"] == "credit-risk-cli"
    assert payload["project"]["version"] == "0.1.0"
    assert payload["project"]["requires-python"] == ">=3.11"
    assert payload["project"]["license"] == "MIT"
    assert payload["project"]["dependencies"] == ["typer>=0.27,<1"]
    assert "Environment :: Console" in payload["project"]["classifiers"]
    assert "Typing :: Typed" in payload["project"]["classifiers"]
    assert payload["project"]["scripts"] == {
        "credit-risk-cli": "credit_risk_cli.cli:app"
    }
    assert payload["build-system"]["build-backend"] == "uv_build"
    assert payload["build-system"]["requires"] == ["uv_build>=0.12,<0.13"]
    assert payload["tool"]["uv"]["build-backend"]["module-name"] == "credit_risk_cli"


def test_composed_file_set_matches_the_expected_project_shape() -> None:
    spec = parse_project_spec(_payload())

    rendered = render_project(spec)
    targets = {item.target for item in rendered.files}

    assert targets == {
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
        ".python-version",
        "src/credit_risk_cli/__init__.py",
        "src/credit_risk_cli/__main__.py",
        "src/credit_risk_cli/cli.py",
        "src/credit_risk_cli/py.typed",
        "tests/__init__.py",
        "tests/test_cli.py",
    }


def test_generated_cli_source_defines_the_documented_module_entry_point() -> None:
    spec = parse_project_spec(_payload())

    rendered = render_project(spec)
    files = {item.target: item.content.decode() for item in rendered.files}

    assert (
        "from credit_risk_cli.cli import app"
        in files["src/credit_risk_cli/__main__.py"]
    )
    assert "app = typer.Typer" in files["src/credit_risk_cli/cli.py"]
    assert "def hello(" in files["src/credit_risk_cli/cli.py"]


def test_cli_has_no_option_schema_and_rejects_supplied_options() -> None:
    spec = parse_project_spec(_payload(component_options={"cli": {"anything": "x"}}))

    with pytest.raises(ForgeEngineError) as exc_info:
        plan_generation(spec)

    assert exc_info.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS
