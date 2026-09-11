"""The generation-metadata document: the engine's reproduce-or-update hand-off.

``render_project`` attaches a :class:`GenerationMetadata` to every
:class:`~forge_template.engine.RenderedProject`. A client persists its
canonical JSON (see :data:`DEFAULT_GENERATION_METADATA_TARGET`) into the
generated project and hands it back to the engine to reproduce or update the
project later. The document records *what was produced* -- the effective spec,
the exact provider release, the protocol integers in force, the selected
component versions, and a digest and ownership entry per rendered file. It
records no timestamp, no absolute path, and no environment value.

This module owns only the document's shape and its serialisation. Building one
from a render and validating one a client hands back both live in
``forge_template.engine`` -- they need the catalogue and the renderer, and
their failures are the two ``EngineErrorCode`` values
``invalid-generation-metadata`` and ``unsupported-generation-metadata``. See
docs/generation-provenance.md (FT-15.02 / ADR 0059) and
docs/cutover-compatibility-and-acceptance.md (FT-15.04 / ADR 0061); the field
names here are FT-17.01 / ADR 0062.

:class:`UpdatePlan` and its ``AppliedRename`` / ``UpdateTarget`` members are
the reproducible-render hand-off FT-17.04 / ADR 0065 added: the data
``forge_template.engine.plan_update`` returns from an old/new render pair, so
a client can apply an engine-native update without the provider ever touching
a working tree. See docs/generation-provenance.md#update-inputs.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

GENERATION_METADATA_VERSION = 1
"""The schema version this engine line writes and the only one it reads.

The ninth versioned compatibility axis
(docs/compatibility-policy.md#current-compatibility-state), published through
``forge_template.get_engine_info().metadata_version`` and negotiated exactly
like the ProjectSpec and component-manifest protocol tuples. An out-of-range
value fails closed as ``unsupported-generation-metadata``.
"""

DEFAULT_GENERATION_METADATA_TARGET = ".forge/generation.json"
"""The one documented default path a client persists the document at.

ADR 0059 reserved "one documented default target" for FT-17.01 to name;
create-forge ADR 0041 asks the provider to adopt ``.forge/generation.json``
so both repositories name one path. The client still owns writing, reading,
and committing the file; this is the agreed default, not an engine-performed
filesystem operation.
"""

_Sha256Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
_NonEmptyString = Annotated[str, Field(min_length=1)]


class _MetadataModel(BaseModel):
    """Shared strict, immutable, closed-world behaviour for document objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ProviderIdentity(_MetadataModel):
    """The exact installable that produced a render."""

    distribution: Literal["forge-template"]
    version: _NonEmptyString


class MetadataProtocols(_MetadataModel):
    """The protocol integers in force for a render."""

    projectspec: int
    component_manifest: tuple[int, ...]

    @field_validator("component_manifest", mode="before")
    @classmethod
    def _normalise_protocol_array(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("component_manifest")
    @classmethod
    def _require_non_empty(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if not value:
            msg = "component_manifest must record at least one protocol integer"
            raise ValueError(msg)
        return value


class SelectedComponent(_MetadataModel):
    """One selected component and the version that rendered."""

    id: _NonEmptyString
    version: _NonEmptyString


class OutputRecord(_MetadataModel):
    """One rendered file: its target, owner, content digest and disposition."""

    target: _NonEmptyString
    owner: _NonEmptyString
    """``"foundation"`` or ``"component:<id>"`` -- ``PlannedFile.owner``
    restated as a string."""
    digest: _Sha256Digest
    regeneration: Literal["replace", "skip-if-exists"]


class ReproductionRecord(_MetadataModel):
    """Whether the merge base for the next update is intact."""

    mode: Literal["exact", "degraded"]
    reason: str = ""


class GenerationMetadata(_MetadataModel):
    """One generated project's complete provenance document.

    Field order here is the documented order
    (docs/generation-provenance.md#the-generation-metadata-document);
    :meth:`to_json` sorts keys for a canonical on-disk form.
    """

    metadata_version: int
    provider: ProviderIdentity
    protocols: MetadataProtocols
    spec: dict[str, JsonValue]
    """The effective :class:`~forge_template.project_spec.ProjectSpec`,
    verbatim, in its protocol wire form. Held opaque so a recorded protocol
    integer can be negotiated before the spec is parsed; a client calls
    ``parse_project_spec(metadata.spec)`` to reconstruct it."""
    components: tuple[SelectedComponent, ...]
    output: tuple[OutputRecord, ...]
    reproduction: ReproductionRecord | None = None

    @field_validator("components", "output", mode="before")
    @classmethod
    def _normalise_array(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    def to_json(self) -> str:
        """Return the canonical, deterministic on-disk serialisation.

        Sorted keys, two-space indent, a trailing newline, no ``reproduction``
        key on a normal (``exact``) render. Byte-stable for a given document
        so a client can diff or digest it.
        """
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


UpdateClassification = Literal["unchanged", "added", "removed", "changed", "renamed"]
"""The complete update-target classification vocabulary.

Every :class:`UpdateTarget.classification` value is one of these five --
``docs/generation-provenance.md#update-inputs`` is the source of the
vocabulary, and ``plan_update`` is the only place that assigns it."""


class AppliedRename(_MetadataModel):
    """One owner-declared path move a client should apply before diffing.

    Restates a component manifest's ``[[renames]]`` record
    (``forge_template.component_manifest.RenameRecord``, manifest protocol 3)
    as public update output, scoped to the recorded/installed version window
    that made it apply to this particular update -- see
    ``docs/generation-provenance.md#owner-declared-rename-records``.
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, populate_by_name=True
    )

    component_id: _NonEmptyString
    from_: _NonEmptyString = Field(alias="from")
    to: _NonEmptyString
    since: _NonEmptyString


class UpdateTarget(_MetadataModel):
    """One target's classification against the recorded/current render pair."""

    target: _NonEmptyString
    classification: UpdateClassification
    owner: _NonEmptyString
    """``"foundation"`` or ``"component:<id>"``, as in :class:`OutputRecord`."""
    regeneration: Literal["replace", "skip-if-exists"]


class UpdatePlan(_MetadataModel):
    """The reproducible-render hand-off: classified targets plus applied renames.

    Returned by ``forge_template.engine.plan_update`` from a recorded
    generation-metadata document, the client-reproduced old render, and a
    fresh new render. Carries no filesystem state and performs no merge --
    the client applies it (FT-ROADMAP-01-EX-01).
    """

    targets: tuple[UpdateTarget, ...]
    renames: tuple[AppliedRename, ...]
    reproduction: ReproductionRecord
