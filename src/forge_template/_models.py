"""Public engine result models (private module; import from ``forge_template``).

ADR 0079: the facade re-exports every name defined here unchanged. Clients
import them from :mod:`forge_template`; where a class is defined is an
implementation detail.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from forge_template.file_conflicts import Owner
from forge_template.generation_metadata import GenerationMetadata


class _PublicModel(BaseModel):
    """Shared strict and immutable behaviour for public result models."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EngineInfo(_PublicModel):
    """Installed engine package and data-protocol compatibility metadata."""

    package_version: str
    projectspec_protocols: tuple[int, ...]
    component_manifest_protocols: tuple[int, ...]
    metadata_version: int
    """The generation-metadata schema version this engine writes and reads --
    the ninth versioned compatibility axis, negotiated exactly like the
    protocol tuples above. See docs/generation-provenance.md."""


class ComponentRelation(_PublicModel):
    """One component requirement or conflict exposed for client guidance."""

    id: str
    version: str | None = None


class ComponentOption(_PublicModel):
    """One owner-local option declaration exposed during discovery."""

    name: str
    type: Literal["string", "integer", "boolean", "string_list"]
    required: bool
    default: JsonValue
    choices: tuple[JsonValue, ...]
    description: str
    format: Literal["pep440"] | None = None
    """Option-schema protocol 2 only; see ``OPTION_FORMATS``."""


class ComponentDescriptor(_PublicModel):
    """Path-free component metadata suitable for client choice presentation."""

    id: str
    name: str
    description: str
    kind: Literal["archetype", "capability", "platform"]
    version: str
    projectspec_protocols: tuple[int, ...]
    requires_python: str
    requires: tuple[ComponentRelation, ...]
    conflicts: tuple[ComponentRelation, ...]
    options: tuple[ComponentOption, ...]


class PlannedExtension(_PublicModel):
    """One selected component extending an owner-declared point."""

    component_id: str
    extension_point: str


class PlannedFile(_PublicModel):
    """One generated target and its ownership metadata.

    ``owner`` is discriminated on ``kind``: ``FoundationOwner(kind=
    "foundation")`` for the implicit Foundation content source, or
    ``ComponentOwner(kind="component", id=...)`` for a selected component.
    Both types are ``forge_template.file_conflicts``' own -- reused directly,
    not redeclared, so this field can never drift from what
    ``resolve_output_plan`` actually resolved. This replaced
    ``owner_component_id`` in the ``0.3.0`` line (FT-08.02/ADR 0033): a plain
    component-id string could not truthfully represent a Foundation-owned
    file. ``component_order`` still lists selected components only --
    Foundation is never a member of it, whether or not it owns a file here.
    """

    target: str
    owner: Owner = Field(discriminator="kind")
    extensions: tuple[PlannedExtension, ...] = ()
    regeneration: Literal["replace", "skip-if-exists"] = "replace"
    """The owning component's declared regeneration disposition for this
    target (manifest protocol 3 ``[[regeneration]]``). ``"replace"`` unless a
    record names the target ``"skip-if-exists"``; the client applies the
    skip. Foundation-owned targets are always ``"replace"``."""


class GenerationPlan(_PublicModel):
    """Deterministic, path-free preview of a generation request."""

    component_order: tuple[str, ...]
    files: tuple[PlannedFile, ...]


class RenderedFile(_PublicModel):
    """One immutable project-relative target and its rendered bytes."""

    target: str
    content: bytes


class RenderedProject(_PublicModel):
    """A generation plan, its deterministic in-memory file set, and provenance."""

    plan: GenerationPlan
    files: tuple[RenderedFile, ...]
    metadata: GenerationMetadata | None = None
    """The generation-metadata document for this render. ``render_project``
    always populates it; it is ``None`` only on a ``RenderedProject`` a caller
    constructs by hand to pass to ``validate_rendered_project``. A client
    persists ``metadata.to_json()`` and hands it back to reproduce or update
    the project -- see docs/generation-provenance.md."""
