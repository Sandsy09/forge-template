"""Canonical ProjectSpec protocol models.

This module defines the serialisable request consumed by Forge's future
composition engine.  It deliberately does not expose discovery, rendering,
filesystem orchestration, or a stable top-level engine facade; those remain
later Stage 06 work.
"""

from __future__ import annotations

import re
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

PROJECT_SPEC_PROTOCOL_VERSION = 1
"""The only ProjectSpec wire protocol understood by this engine line."""

SUPPORTED_PYTHON_MINORS = ("3.11", "3.12", "3.13", "3.14")
"""CPython minors currently offered by Forge-generated projects."""

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_ForgeIdentifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"),
]
_PackageName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]*$"),
]
_RepositoryName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9._-]*$"),
]
_OptionName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]*$"),
]
_PythonMinor = Annotated[str, StringConstraints(pattern=r"^3\.\d+$")]


class _ProtocolModel(BaseModel):
    """Shared strict and immutable behaviour for protocol objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Author(_ProtocolModel):
    """Provider-neutral project author or maintainer metadata."""

    name: _NonEmptyString
    email: str | None = None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        if value is not None and not _EMAIL_RE.fullmatch(value):
            msg = "email must be a valid address or null"
            raise ValueError(msg)
        return value


class ProjectMetadata(_ProtocolModel):
    """Provider-neutral identity and handoff metadata for a project."""

    name: _NonEmptyString
    package_name: _PackageName
    repository_name: _RepositoryName
    description: str = ""
    licence: _NonEmptyString
    authors: tuple[Author, ...] = ()


class PythonSelection(_ProtocolModel):
    """Generated-project compatibility floor and development interpreter."""

    minimum: _PythonMinor
    development: _PythonMinor

    @model_validator(mode="after")
    def _validate_supported_range(self) -> Self:
        unsupported = sorted(
            {self.minimum, self.development} - set(SUPPORTED_PYTHON_MINORS)
        )
        if unsupported:
            supported = ", ".join(SUPPORTED_PYTHON_MINORS)
            msg = (
                f"unsupported CPython minor(s): {', '.join(unsupported)}; "
                f"supported values are {supported}"
            )
            raise ValueError(msg)

        minimum_index = SUPPORTED_PYTHON_MINORS.index(self.minimum)
        development_index = SUPPORTED_PYTHON_MINORS.index(self.development)
        if minimum_index > development_index:
            msg = "minimum Python version cannot be newer than development"
            raise ValueError(msg)
        return self

    @property
    def tested_versions(self) -> tuple[str, ...]:
        """Return the contiguous supported range without adding a wire field."""
        minimum_index = SUPPORTED_PYTHON_MINORS.index(self.minimum)
        development_index = SUPPORTED_PYTHON_MINORS.index(self.development)
        return SUPPORTED_PYTHON_MINORS[minimum_index : development_index + 1]


class ComponentSelection(_ProtocolModel):
    """The effective archetype, capability, and platform selection."""

    archetype: _ForgeIdentifier
    capabilities: tuple[_ForgeIdentifier, ...] = ()
    platforms: tuple[_ForgeIdentifier, ...] = ()

    @field_validator("capabilities", "platforms")
    @classmethod
    def _canonicalise_unique_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "component selections must not contain duplicate identifiers"
            raise ValueError(msg)
        return tuple(sorted(value))


class SelectionProvenance(_ProtocolModel):
    """Non-enforcing provenance for defaults and constraints already applied."""

    profile: _ForgeIdentifier | None = None
    policies: tuple[_ForgeIdentifier, ...] = ()

    @field_validator("policies")
    @classmethod
    def _canonicalise_unique_policies(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "policy provenance must not contain duplicate identifiers"
            raise ValueError(msg)
        return tuple(sorted(value))


class ProjectSpec(_ProtocolModel):
    """A strict, serialisable, effective Forge generation request."""

    protocol_version: Literal[1]
    project: ProjectMetadata
    python: PythonSelection
    components: ComponentSelection
    provenance: SelectionProvenance = Field(default_factory=SelectionProvenance)
    component_options: dict[
        _ForgeIdentifier,
        dict[_OptionName, JsonValue],
    ] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _options_belong_to_selected_components(self) -> Self:
        selected = {
            self.components.archetype,
            *self.components.capabilities,
            *self.components.platforms,
        }
        unselected = sorted(set(self.component_options) - selected)
        if unselected:
            msg = "component options reference unselected component(s): " + ", ".join(
                unselected
            )
            raise ValueError(msg)
        return self
