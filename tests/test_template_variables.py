"""Tests for the rendered template-variable namespace and option vocabulary."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError

from forge_template.component_manifest import load_component_manifest
from forge_template.composition import composition_plan
from forge_template.project_spec import ComponentSelection, ProjectSpec
from forge_template.template_variables import (
    OPTION_TYPES,
    RESERVED_NAMESPACES,
    TEMPLATE_VARIABLES_PROTOCOL_VERSION,
    OptionDeclaration,
    OptionSchema,
    load_option_schema,
    options_namespace,
    resolve_template_variables,
)

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"


def _project_spec(
    *,
    archetype: str = "library",
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
    component_options: dict[str, dict[str, object]] | None = None,
) -> ProjectSpec:
    return ProjectSpec.model_validate(
        {
            "protocol_version": 1,
            "project": {
                "name": "Example",
                "package_name": "example",
                "repository_name": "example",
                "licence": "mit",
            },
            "python": {"minimum": "3.11", "development": "3.13"},
            "components": {
                "archetype": archetype,
                "capabilities": capabilities,
                "platforms": platforms,
            },
            "component_options": component_options or {},
        }
    )


def _copy_fixture(tmp_path: Path, identifier: str) -> Path:
    destination = tmp_path / identifier
    shutil.copytree(FIXTURES / identifier, destination)
    return destination / "component.toml"


# -----------------------------------------------------------------------------
# OptionDeclaration / OptionSchema validation
# -----------------------------------------------------------------------------


def test_option_declaration_is_strict_and_frozen() -> None:
    declaration = OptionDeclaration(name="build_backend", type="string")

    with pytest.raises(ValidationError, match="frozen"):
        declaration.name = "changed"
    with pytest.raises(ValidationError):
        OptionDeclaration.model_validate(
            {"name": "build_backend", "type": "string", "unexpected": True}
        )


@pytest.mark.parametrize("option_type", OPTION_TYPES)
def test_every_declared_option_type_is_constructible(
    option_type: Literal["string", "integer", "boolean", "string_list"],
) -> None:
    OptionDeclaration(name="value", type=option_type)


def test_required_and_default_are_mutually_exclusive() -> None:
    with pytest.raises(ValidationError, match="required and carry a"):
        OptionDeclaration(
            name="build_backend", type="string", required=True, default="uv_build"
        )


def test_choices_must_be_non_empty_when_declared() -> None:
    with pytest.raises(ValidationError, match="empty choices"):
        OptionDeclaration.model_validate(
            {"name": "build_backend", "type": "string", "choices": []}
        )


def test_choices_are_restricted_to_string_and_integer_types() -> None:
    with pytest.raises(ValidationError, match="only meaningful for"):
        OptionDeclaration(name="flag", type="boolean", choices=(True, False))
    with pytest.raises(ValidationError, match="only meaningful for"):
        OptionDeclaration(name="items", type="string_list", choices=("a", "b"))


def test_choices_must_match_the_declared_type() -> None:
    with pytest.raises(ValidationError, match="not matching"):
        OptionDeclaration(name="count", type="integer", choices=("1", "2"))


def test_default_must_be_among_declared_choices() -> None:
    with pytest.raises(ValidationError, match="is not among"):
        OptionDeclaration(
            name="build_backend",
            type="string",
            choices=("uv_build", "hatchling"),
            default="setuptools",
        )


def test_default_must_match_the_declared_type() -> None:
    with pytest.raises(ValidationError, match="does not match its declared type"):
        OptionDeclaration(name="count", type="integer", default="not-an-int")
    with pytest.raises(ValidationError, match="does not match its declared type"):
        OptionDeclaration(name="flag", type="boolean", default=1)


def test_boolean_default_never_satisfies_a_non_boolean_type() -> None:
    """``bool`` is an ``int`` subclass; ``True``/``False`` must not silently
    satisfy ``"integer"`` just because ``isinstance(True, int)`` is true."""
    with pytest.raises(ValidationError, match="does not match its declared type"):
        OptionDeclaration(name="count", type="integer", default=True)


def test_string_list_default_requires_every_element_to_be_a_string() -> None:
    OptionDeclaration(name="items", type="string_list", default=["a", "b"])

    with pytest.raises(ValidationError, match="does not match its declared type"):
        OptionDeclaration(name="items", type="string_list", default=["a", 1])


def test_option_names_use_the_lower_snake_case_rule() -> None:
    with pytest.raises(ValidationError):
        OptionDeclaration(name="Bad-Name", type="string")


def test_option_schema_rejects_duplicate_names() -> None:
    with pytest.raises(ValidationError, match="duplicate names"):
        OptionSchema(
            schema_version=1,
            options=(
                OptionDeclaration(name="value", type="string"),
                OptionDeclaration(name="value", type="integer"),
            ),
        )


@pytest.mark.parametrize("schema_version", [None, 2, "1"])
def test_unsupported_schema_version_is_rejected(schema_version: object) -> None:
    payload: dict[str, object] = {"options": []}
    if schema_version is not None:
        payload["schema_version"] = schema_version

    with pytest.raises(ValidationError):
        OptionSchema.model_validate(payload)


def test_option_schema_json_schema_forbids_extra_fields() -> None:
    schema = OptionSchema.model_json_schema()
    assert schema["additionalProperties"] is False


# -----------------------------------------------------------------------------
# Component option namespacing
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("component_id", "expected"),
    [
        ("github", "github"),
        ("secret-scanning", "secret_scanning"),
        ("a-b-c", "a_b_c"),
    ],
)
def test_options_namespace_replaces_hyphens_with_underscores(
    component_id: str, expected: str
) -> None:
    assert options_namespace(component_id) == expected


def test_component_identifiers_can_never_contain_an_underscore() -> None:
    """The property ``options_namespace``'s injectivity argument rests on.

    Component identifiers use the same kebab-case grammar as
    ``ComponentSelection``'s archetype/capability/platform fields; asserting
    it here directly, rather than merely assuming it, is what makes the
    kebab-to-snake mapping's uniqueness guarantee more than a comment.
    """
    with pytest.raises(ValidationError):
        ComponentSelection(archetype="bad_id")


def test_options_namespace_rejects_an_id_containing_an_underscore() -> None:
    with pytest.raises(ValueError, match="must not contain an underscore"):
        options_namespace("already_snake")


# -----------------------------------------------------------------------------
# load_option_schema
# -----------------------------------------------------------------------------


def test_load_option_schema_returns_empty_schema_when_undeclared(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_fixture(tmp_path, "coverage")
    manifest = load_component_manifest(manifest_path)

    schema = load_option_schema(manifest_path, manifest)

    assert schema.options == ()
    assert schema.schema_version == TEMPLATE_VARIABLES_PROTOCOL_VERSION


def test_load_option_schema_parses_the_real_library_fixture() -> None:
    manifest_path = FIXTURES / "library" / "component.toml"
    manifest = load_component_manifest(manifest_path)

    schema = load_option_schema(manifest_path, manifest)

    names = {option.name for option in schema.options}
    assert names == {"build_backend", "initial_version"}


def test_load_option_schema_rejects_malformed_json(tmp_path: Path) -> None:
    manifest_path = _copy_fixture(tmp_path, "library")
    (manifest_path.parent / "options.schema.json").write_text(
        "{not valid json", encoding="utf-8"
    )

    with pytest.raises(json.JSONDecodeError):
        load_option_schema(manifest_path, load_component_manifest(manifest_path))


def test_load_option_schema_rejects_a_non_object_document(tmp_path: Path) -> None:
    manifest_path = _copy_fixture(tmp_path, "library")
    (manifest_path.parent / "options.schema.json").write_text("[]", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_option_schema(manifest_path, load_component_manifest(manifest_path))


# -----------------------------------------------------------------------------
# resolve_template_variables
# -----------------------------------------------------------------------------


def test_core_namespace_mirrors_project_spec_values() -> None:
    spec = _project_spec(capabilities=("changelog",))

    variables = resolve_template_variables(spec)

    assert variables.project == spec.project
    assert variables.components == spec.components


def test_python_namespace_adds_derived_values() -> None:
    spec = _project_spec()

    variables = resolve_template_variables(spec)

    assert variables.python.minimum == "3.11"
    assert variables.python.development == "3.13"
    assert variables.python.tested_versions == ("3.11", "3.12", "3.13")
    assert variables.python.requires_python == ">=3.11"


def test_every_selected_component_gets_an_options_entry() -> None:
    spec = _project_spec(capabilities=("changelog",), platforms=("github",))

    variables = resolve_template_variables(spec)

    assert set(variables.options) == {"library", "changelog", "github"}
    assert variables.options["changelog"] == {}


def test_defaults_are_applied_when_an_option_is_not_supplied() -> None:
    schema = OptionSchema(
        schema_version=1,
        options=(
            OptionDeclaration(name="initial_version", type="string", default="0.1.0"),
        ),
    )
    spec = _project_spec()

    variables = resolve_template_variables(spec, {"library": schema})

    assert variables.options["library"] == {"initial_version": "0.1.0"}


def test_unknown_option_is_rejected() -> None:
    spec = _project_spec(component_options={"library": {"unknown_option": "x"}})

    with pytest.raises(ValueError, match="unknown option"):
        resolve_template_variables(spec, {})


def test_missing_required_option_is_rejected() -> None:
    schema = OptionSchema(
        schema_version=1,
        options=(
            OptionDeclaration(name="build_backend", type="string", required=True),
        ),
    )
    spec = _project_spec()

    with pytest.raises(ValueError, match="missing required option"):
        resolve_template_variables(spec, {"library": schema})


def test_option_value_type_mismatch_is_rejected() -> None:
    schema = OptionSchema(
        schema_version=1, options=(OptionDeclaration(name="count", type="integer"),)
    )
    spec = _project_spec(component_options={"library": {"count": "not-an-int"}})

    with pytest.raises(ValueError, match="does not match its declared type"):
        resolve_template_variables(spec, {"library": schema})


def test_option_value_outside_choices_is_rejected() -> None:
    schema = OptionSchema(
        schema_version=1,
        options=(
            OptionDeclaration(
                name="build_backend",
                type="string",
                choices=("uv_build", "hatchling"),
            ),
        ),
    )
    spec = _project_spec(component_options={"library": {"build_backend": "setuptools"}})

    with pytest.raises(ValueError, match="not among its declared choices"):
        resolve_template_variables(spec, {"library": schema})


def test_option_supplied_to_schema_less_component_is_rejected() -> None:
    spec = _project_spec(
        capabilities=("changelog",),
        component_options={"changelog": {"tool": "git-cliff"}},
    )

    with pytest.raises(ValueError, match="unknown option"):
        resolve_template_variables(spec, {})


def test_as_context_returns_a_json_compatible_reserved_namespace() -> None:
    spec = _project_spec(platforms=("github",))

    context = resolve_template_variables(spec).as_context()

    assert set(context) == set(RESERVED_NAMESPACES)
    assert json.loads(json.dumps(context)) == context


def test_resolve_template_variables_end_to_end_with_real_fixtures() -> None:
    manifest_paths = [
        FIXTURES / identifier / "component.toml"
        for identifier in ("library", "coverage", "github")
    ]
    spec = _project_spec(
        capabilities=("coverage",),
        platforms=("github",),
        component_options={
            "library": {"build_backend": "hatchling"},
            "github": {"organisation": "example-org"},
        },
    )
    schemas = {
        manifest.id: load_option_schema(path, manifest)
        for path, manifest in (
            (path, load_component_manifest(path)) for path in manifest_paths
        )
    }
    plan = composition_plan(spec, manifest_paths)
    assert plan  # sanity: the composition plan itself still resolves

    variables = resolve_template_variables(spec, schemas)

    assert variables.options["library"] == {
        "build_backend": "hatchling",
        "initial_version": "0.1.0",
    }
    assert variables.options["github"] == {"organisation": "example-org"}
    assert variables.options["coverage"] == {}
