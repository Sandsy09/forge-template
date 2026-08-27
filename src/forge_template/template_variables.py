"""The rendered template-variable namespace and component option vocabulary.

This module defines what a template author types, and what a component may
declare as its own options through ``options_schema``. It deliberately does
not render anything, perform file operations, define the in-file
extension-point marker syntax, or expose a stable engine error surface;
those remain later Stage 06 and FT-06.07 work. See
docs/template-variables.md.

``project`` and ``components`` reuse ``ProjectSpec``'s own models directly
rather than redeclaring parallel ones, so the namespace mirrors ProjectSpec
by construction. ``python`` adds two engine-derived, read-only values on top
of the two wire ones. ``options`` is reserved for component-specific values,
keyed by each selected component's identifier normalised to snake_case, so a
component option can never collide with a core variable or another
component's — the collision is structurally unrepresentable, not merely
forbidden.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from forge_template.component_manifest import ComponentManifest, component_resource_path
from forge_template.project_spec import (
    ComponentSelection,
    ProjectMetadata,
    ProjectSpec,
)

TEMPLATE_VARIABLES_PROTOCOL_VERSION: Literal[1] = 1
"""The only option-schema protocol understood by this engine line."""

RESERVED_NAMESPACES: tuple[str, ...] = ("project", "python", "components", "options")
"""The complete, closed set of top-level template-variable roots."""

OPTION_TYPES: tuple[str, ...] = ("string", "integer", "boolean", "string_list")
"""The complete, closed set of declarable component option value types."""

_TYPES_ADMITTING_CHOICES: tuple[str, ...] = ("string", "integer")
"""Option types for which an enumerated ``choices`` set has one unambiguous
meaning. A ``string_list`` or ``boolean`` enum does not, so declaring
``choices`` on either is rejected rather than left to guess a meaning."""

_OptionName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]*$"),
]

_PYTHON_TYPES: dict[str, type] = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "string_list": list,
}


def _value_matches_declared_type(type_name: str, value: JsonValue) -> bool:
    """Return whether ``value`` matches ``type_name``.

    ``bool`` is an ``int`` subclass in Python, so a boolean is only ever
    accepted for ``"boolean"``; it never silently satisfies ``"integer"``.
    ``"string_list"`` additionally requires every element to be a string.
    """
    expected = _PYTHON_TYPES[type_name]
    if expected is bool:
        return isinstance(value, bool)
    if isinstance(value, bool):
        return False
    if expected is list:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    return isinstance(value, expected)


class _VariableModel(BaseModel):
    """Shared strict and immutable behaviour for template-variable objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class OptionDeclaration(_VariableModel):
    """One component option's name, type, and validation rules."""

    name: _OptionName
    type: Literal["string", "integer", "boolean", "string_list"]
    required: bool = False
    default: JsonValue = None
    choices: tuple[JsonValue, ...] = ()
    description: str = ""

    @field_validator("choices", mode="before")
    @classmethod
    def _normalise_choices(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def _validate_declaration(self) -> Self:
        if self.required and self.default is not None:
            msg = (
                f"option {self.name!r} cannot be both required and carry a "
                f"default: a required option has no fallback value"
            )
            raise ValueError(msg)

        if "choices" in self.model_fields_set and not self.choices:
            msg = (
                f"option {self.name!r} declares an empty choices list; omit "
                f"choices entirely rather than declaring zero of them"
            )
            raise ValueError(msg)

        if self.choices:
            if self.type not in _TYPES_ADMITTING_CHOICES:
                msg = (
                    f"option {self.name!r} declares choices for type "
                    f"{self.type!r}; choices are only meaningful for "
                    f"{', '.join(_TYPES_ADMITTING_CHOICES)}"
                )
                raise ValueError(msg)
            invalid = [
                choice
                for choice in self.choices
                if not _value_matches_declared_type(self.type, choice)
            ]
            if invalid:
                msg = (
                    f"option {self.name!r} declares choice(s) not matching "
                    f"its type {self.type!r}: {invalid!r}"
                )
                raise ValueError(msg)
            if self.default is not None and self.default not in self.choices:
                msg = (
                    f"option {self.name!r} default {self.default!r} is not "
                    f"among its declared choices {self.choices!r}"
                )
                raise ValueError(msg)

        if self.default is not None and not _value_matches_declared_type(
            self.type, self.default
        ):
            msg = (
                f"option {self.name!r} default {self.default!r} does not "
                f"match its declared type {self.type!r}"
            )
            raise ValueError(msg)
        return self


class OptionSchema(_VariableModel):
    """One component's complete, optional declared option vocabulary."""

    schema_version: Literal[1]
    options: tuple[OptionDeclaration, ...] = ()

    @field_validator("options", mode="before")
    @classmethod
    def _normalise_options(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def _validate_unique_names(self) -> Self:
        names = [option.name for option in self.options]
        if len(names) != len(set(names)):
            msg = "option declarations must not contain duplicate names"
            raise ValueError(msg)
        return self


_EMPTY_OPTION_SCHEMA = OptionSchema(schema_version=TEMPLATE_VARIABLES_PROTOCOL_VERSION)
"""The implicit schema of a component that declares no ``options_schema`` at
all: it accepts no options, per decision 5 in the FT-06.05 design."""


class PythonVariables(_VariableModel):
    """The rendered Python compatibility namespace.

    ``minimum`` and ``development`` come from ``PythonSelection`` unchanged.
    ``tested_versions`` and ``requires_python`` are derived by this module so
    every component reads one already-computed matrix and specifier rather
    than each re-deriving its own, potentially drifting, copy.
    """

    minimum: str
    development: str
    tested_versions: tuple[str, ...]
    requires_python: str


class TemplateVariables(_VariableModel):
    """The complete, strict, rendered template-variable namespace."""

    project: ProjectMetadata
    python: PythonVariables
    components: ComponentSelection
    options: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)

    def as_context(self) -> dict[str, JsonValue]:
        """Return this namespace as a plain JSON-compatible rendering context."""
        return self.model_dump(mode="json")


def options_namespace(component_id: str) -> str:
    """Return the ``options`` key for one component identifier.

    Component identifiers are kebab-case
    (``^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$``) and cannot contain an underscore, so
    replacing every hyphen with an underscore is injective: two distinct
    identifiers can never collide on one options key. This is what lets a
    hyphenated identifier still be read with plain dotted Jinja access
    (``options.secret_scanning.tool``) rather than bracket access, which a raw
    hyphen in the key would otherwise force (``{{ options.secret-scanning }}``
    parses as subtraction, not lookup).
    """
    if "_" in component_id:
        msg = f"component identifier must not contain an underscore: {component_id!r}"
        raise ValueError(msg)
    return component_id.replace("-", "_")


def load_option_schema(
    manifest_path: str | Path, manifest: ComponentManifest
) -> OptionSchema:
    """Load and validate one component's ``options_schema``, if declared.

    A component with no ``options_schema`` accepts no options at all: this
    returns the empty schema rather than treating an absent declaration as
    unvalidated passthrough.
    """
    if manifest.options_schema is None:
        return _EMPTY_OPTION_SCHEMA

    resolved_manifest = Path(manifest_path).resolve(strict=True)
    schema_path = component_resource_path(resolved_manifest, manifest.options_schema)
    with schema_path.open("rb") as schema_file:
        payload = json.load(schema_file)
    return OptionSchema.model_validate(payload)


def _derive_python_variables(spec: ProjectSpec) -> PythonVariables:
    """Derive the read-only Python values from the two wire-supplied ones.

    ``tested_versions`` is ``PythonSelection``'s own derived contiguous range;
    ``requires_python`` is the canonical floor specifier every selected
    component's ``compatibility.requires_python`` must already satisfy per
    ``ComponentCompatibility.supports``.
    """
    return PythonVariables(
        minimum=spec.python.minimum,
        development=spec.python.development,
        tested_versions=spec.python.tested_versions,
        requires_python=f">={spec.python.minimum}",
    )


def _resolve_component_options(
    component_id: str,
    schema: OptionSchema,
    supplied: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    declared = {option.name: option for option in schema.options}

    unknown = sorted(set(supplied) - set(declared))
    if unknown:
        msg = (
            f"component {component_id!r} received unknown option(s), not "
            f"declared by its options_schema: {', '.join(unknown)}"
        )
        raise ValueError(msg)

    resolved: dict[str, JsonValue] = {}
    for name, option in declared.items():
        if name in supplied:
            value = supplied[name]
            if not _value_matches_declared_type(option.type, value):
                msg = (
                    f"component {component_id!r} option {name!r} value "
                    f"{value!r} does not match its declared type "
                    f"{option.type!r}"
                )
                raise ValueError(msg)
            if option.choices and value not in option.choices:
                msg = (
                    f"component {component_id!r} option {name!r} value "
                    f"{value!r} is not among its declared choices "
                    f"{option.choices!r}"
                )
                raise ValueError(msg)
            resolved[name] = value
        elif option.required:
            msg = f"component {component_id!r} is missing required option {name!r}"
            raise ValueError(msg)
        elif option.default is not None:
            resolved[name] = option.default
    return resolved


def resolve_template_variables(
    spec: ProjectSpec,
    schemas: dict[str, OptionSchema] | None = None,
) -> TemplateVariables:
    """Return the rendered template-variable namespace for an effective spec.

    ``spec`` is assumed already validated against the selected catalogue
    (``forge_template.component_manifest.validate_manifest_selection``); this
    function only resolves variable and option content, not component
    identity, compatibility, or selection validity.

    ``schemas`` maps each selected component's identifier to its
    ``OptionSchema``; a component absent from the mapping is treated as
    declaring no ``options_schema`` at all, matching ``load_option_schema``'s
    own default. Every selected component receives an ``options`` entry, empty
    when it declares nothing, so a template never has to test whether its own
    namespace exists before reading from it.

    Raises ``ValueError`` naming the component, the option, and the rule
    violated when ``spec.component_options`` supplies an option its component
    does not declare, omits a required option, or supplies a value that fails
    its declared type or ``choices``.
    """
    schema_by_id = schemas or {}
    selected_ids = (
        spec.components.archetype,
        *spec.components.capabilities,
        *spec.components.platforms,
    )

    options: dict[str, dict[str, JsonValue]] = {}
    for component_id in selected_ids:
        schema = schema_by_id.get(component_id, _EMPTY_OPTION_SCHEMA)
        supplied = spec.component_options.get(component_id, {})
        namespace = options_namespace(component_id)
        options[namespace] = _resolve_component_options(component_id, schema, supplied)

    return TemplateVariables(
        project=spec.project,
        python=_derive_python_variables(spec),
        components=spec.components,
        options=options,
    )
