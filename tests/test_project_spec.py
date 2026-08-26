"""Tests for the canonical ProjectSpec protocol v1 models."""

from __future__ import annotations

import json
from typing import cast

import pytest
from pydantic import JsonValue, ValidationError

from forge_template.project_spec import (
    PROJECT_SPEC_PROTOCOL_VERSION,
    SUPPORTED_PYTHON_MINORS,
    Author,
    ComponentSelection,
    ProjectMetadata,
    ProjectSpec,
    PythonSelection,
    SelectionProvenance,
)
from forge_template.schema import load_schema


def _library_payload() -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Credit Risk Utils",
            "package_name": "credit_risk_utils",
            "repository_name": "credit-risk-utils",
            "description": "Shared credit-risk calculations.",
            "licence": "mit",
            "authors": [{"name": "Test User", "email": "test@example.invalid"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": "library",
            "capabilities": ["documentation", "changelog"],
            "platforms": ["github"],
        },
        "provenance": {
            "profile": "maintainer",
            "policies": ["security-baseline"],
        },
        "component_options": {
            "library": {"build_backend": "uv_build"},
            "documentation": {"site_name": "Credit Risk Utils"},
            "github": {"organisation": "example-org"},
        },
    }


def _validate_payload(payload: dict[str, object]) -> ProjectSpec:
    return ProjectSpec.model_validate_json(json.dumps(payload))


def test_library_spec_round_trips_as_strict_json() -> None:
    spec = _validate_payload(_library_payload())

    assert spec.protocol_version == PROJECT_SPEC_PROTOCOL_VERSION
    assert spec.python.tested_versions == ("3.11", "3.12", "3.13")
    assert spec.components.capabilities == ("changelog", "documentation")

    encoded = spec.model_dump_json()
    assert "tested_versions" not in encoded
    assert ProjectSpec.model_validate_json(encoded) == spec


def test_neutral_spec_supports_multiple_platforms() -> None:
    payload = _library_payload()
    payload["components"] = {
        "archetype": "project-shape",
        "capabilities": [],
        "platforms": ["runtime-target", "repository-host"],
    }
    payload["provenance"] = {"profile": None, "policies": []}
    payload["component_options"] = {}

    spec = _validate_payload(payload)

    assert spec.components.platforms == ("repository-host", "runtime-target")


def test_json_schema_describes_protocol_and_forbids_extra_fields() -> None:
    schema = ProjectSpec.model_json_schema()

    assert "protocol_version" in schema["required"]
    assert schema["properties"]["protocol_version"]["const"] == 1
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize("protocol", [None, 2, "1"])
def test_missing_or_unsupported_protocol_is_rejected(protocol: object) -> None:
    payload = _library_payload()
    if protocol is None:
        del payload["protocol_version"]
    else:
        payload["protocol_version"] = protocol

    with pytest.raises(ValidationError):
        _validate_payload(payload)


def test_unknown_fields_and_type_coercion_are_rejected() -> None:
    payload = _library_payload()
    project = payload["project"]
    assert isinstance(project, dict)
    project["unexpected"] = True
    project["description"] = 42

    with pytest.raises(ValidationError) as exc_info:
        _validate_payload(payload)

    error_types = {error["type"] for error in exc_info.value.errors()}
    assert "extra_forbidden" in error_types
    assert "string_type" in error_types


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("package_name", "Credit-Risk"),
        ("repository_name", "bad repository"),
        ("licence", "   "),
    ],
)
def test_invalid_project_metadata_is_rejected(field: str, value: str) -> None:
    payload = _library_payload()
    project = payload["project"]
    assert isinstance(project, dict)
    project[field] = value

    with pytest.raises(ValidationError):
        _validate_payload(payload)


def test_invalid_author_email_is_rejected() -> None:
    with pytest.raises(ValidationError, match="valid address"):
        Author(name="Test User", email="not-an-email")


@pytest.mark.parametrize(
    ("minimum", "development"),
    [("3.10", "3.13"), ("3.11", "3.15"), ("3.14", "3.13")],
)
def test_invalid_python_selection_is_rejected(minimum: str, development: str) -> None:
    with pytest.raises(ValidationError):
        PythonSelection(minimum=minimum, development=development)


def test_python_offerings_match_copier_schema() -> None:
    schema = load_schema()
    rendered_choices = json.loads(schema["python_all"]["default"])

    assert tuple(rendered_choices) == SUPPORTED_PYTHON_MINORS
    assert tuple(schema["python_min_version"]["choices"]) == SUPPORTED_PYTHON_MINORS
    assert tuple(schema["python_version"]["choices"]) == SUPPORTED_PYTHON_MINORS


def test_selection_identifiers_are_sorted_and_unique() -> None:
    selection = ComponentSelection(
        archetype="library",
        capabilities=("documentation", "changelog"),
        platforms=("runtime-target", "repository-host"),
    )
    provenance = SelectionProvenance(
        profile="maintainer",
        policies=("team-policy", "organisation-policy"),
    )

    assert selection.capabilities == ("changelog", "documentation")
    assert selection.platforms == ("repository-host", "runtime-target")
    assert provenance.policies == ("organisation-policy", "team-policy")

    with pytest.raises(ValidationError, match="duplicate"):
        ComponentSelection(
            archetype="library",
            capabilities=("documentation", "documentation"),
        )


@pytest.mark.parametrize("identifier", ["Library", "bad_id", "-bad", "bad--id"])
def test_invalid_forge_identifier_is_rejected(identifier: str) -> None:
    with pytest.raises(ValidationError):
        ComponentSelection(archetype=identifier)


def test_component_options_require_a_selected_owner() -> None:
    payload = _library_payload()
    options = payload["component_options"]
    assert isinstance(options, dict)
    options["unselected-capability"] = {"enabled": True}

    with pytest.raises(ValidationError, match="unselected-capability"):
        _validate_payload(payload)


def test_component_options_accept_only_json_values_and_snake_case_keys() -> None:
    metadata = ProjectMetadata(
        name="Example",
        package_name="example",
        repository_name="example",
        licence="mit",
    )
    python = PythonSelection(minimum="3.11", development="3.13")
    components = ComponentSelection(archetype="library")

    valid = ProjectSpec(
        protocol_version=1,
        project=metadata,
        python=python,
        components=components,
        component_options={
            "library": {
                "nested_value": {"items": [1, True, None, "value"]},
            }
        },
    )
    assert ProjectSpec.model_validate_json(valid.model_dump_json()) == valid

    with pytest.raises(ValidationError):
        ProjectSpec(
            protocol_version=1,
            project=metadata,
            python=python,
            components=components,
            component_options={"library": {"Bad-Key": "value"}},
        )

    with pytest.raises(ValidationError):
        ProjectSpec(
            protocol_version=1,
            project=metadata,
            python=python,
            components=components,
            component_options={"library": {"bad_value": cast(JsonValue, object())}},
        )


def test_models_are_frozen() -> None:
    spec = _validate_payload(_library_payload())

    with pytest.raises(ValidationError, match="frozen"):
        spec.project.name = "Changed"
