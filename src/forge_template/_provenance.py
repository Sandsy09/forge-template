"""Package identity, generation metadata and update planning (private module).

ADR 0079. Owns the installed provider's identity and supported protocol set,
builds the generation-metadata document for a render, parses, negotiates and
verifies a document a client hands back, and classifies an update from a
recorded document and a reproduced/new render pair. Everything here is in
memory: it reads no destination, writes nothing, and never merges -- the
client applies the result (docs/generation-provenance.md).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from importlib import metadata
from typing import Literal, TypeAlias

from packaging.version import Version
from pydantic import ValidationError

from forge_template import _discovery
from forge_template._errors import (
    EngineErrorCode,
    ForgeEngineError,
    metadata_error,
    validation_details,
)
from forge_template._models import GenerationPlan, RenderedFile, RenderedProject
from forge_template.component_manifest import COMPONENT_MANIFEST_PROTOCOL_VERSIONS
from forge_template.file_conflicts import FoundationOwner, Owner
from forge_template.generation_metadata import (
    GENERATION_METADATA_VERSION,
    AppliedRename,
    GenerationMetadata,
    MetadataProtocols,
    OutputRecord,
    ProviderIdentity,
    ReproductionRecord,
    SelectedComponent,
    UpdateClassification,
    UpdatePlan,
    UpdateTarget,
)
from forge_template.project_spec import PROJECT_SPEC_PROTOCOL_VERSION, ProjectSpec

SUPPORTED_PROJECTSPEC_PROTOCOLS: tuple[int, ...] = (PROJECT_SPEC_PROTOCOL_VERSION,)
"""ProjectSpec wire protocols accepted by this engine compatibility line."""

SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS: tuple[int, ...] = (
    COMPONENT_MANIFEST_PROTOCOL_VERSIONS
)
"""Component manifest protocols accepted by this engine compatibility line."""

_SUPPORTED_GENERATION_METADATA_VERSIONS: frozenset[int] = frozenset(
    {GENERATION_METADATA_VERSION}
)
"""Generation-metadata schema versions this engine line reads. Single-valued
today; a client negotiates against ``EngineInfo.metadata_version``."""

GenerationMetadataPayload: TypeAlias = (
    GenerationMetadata | Mapping[str, object] | str | bytes
)
"""Inputs accepted by :func:`forge_template.parse_generation_metadata`."""

_DISTRIBUTION_NAME: Literal["forge-template"] = "forge-template"


def package_version() -> str:
    try:
        return metadata.version(_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        # A raw source-tree import is not a supported installed engine, but a
        # diagnostic value is more useful than making metadata inspection fail.
        return "0+unknown"


def _digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _owner_token(owner: Owner) -> str:
    """Restate ``PlannedFile.owner`` as the metadata document's owner string."""
    if isinstance(owner, FoundationOwner):
        return "foundation"
    return f"component:{owner.id}"


def build_generation_metadata(
    spec: ProjectSpec,
    plan: GenerationPlan,
    rendered: tuple[RenderedFile, ...],
    versions_by_id: Mapping[str, str],
) -> GenerationMetadata:
    """Assemble the provenance document for one completed render.

    Every value comes from the effective spec, the resolved plan, the
    installed catalogue, the rendered bytes, or the fixed distribution
    identity -- the "Secret-free persisted and displayed data" allowlist.
    """
    planned_by_target = {file.target: file for file in plan.files}
    output = tuple(
        OutputRecord(
            target=file.target,
            owner=_owner_token(planned_by_target[file.target].owner),
            digest=_digest(file.content),
            regeneration=planned_by_target[file.target].regeneration,
        )
        for file in rendered
    )
    return GenerationMetadata(
        metadata_version=GENERATION_METADATA_VERSION,
        provider=ProviderIdentity(
            distribution=_DISTRIBUTION_NAME, version=package_version()
        ),
        protocols=MetadataProtocols(
            projectspec=spec.protocol_version,
            component_manifest=SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS,
        ),
        spec=spec.model_dump(mode="json"),
        components=tuple(
            SelectedComponent(id=component_id, version=versions_by_id[component_id])
            for component_id in plan.component_order
        ),
        output=output,
    )


def _parse_metadata_json(raw: str | bytes) -> GenerationMetadata:
    try:
        return GenerationMetadata.model_validate_json(raw)
    except ValidationError as exc:
        raise ForgeEngineError(
            code=EngineErrorCode.INVALID_GENERATION_METADATA,
            operation="validate",
            message="The generation-metadata document is malformed.",
            details=validation_details(exc),
        ) from exc
    except ValueError as exc:
        raise metadata_error(
            EngineErrorCode.INVALID_GENERATION_METADATA,
            "parse",
            (),
            "the generation-metadata document is not valid JSON.",
        ) from exc


def _document(payload: object) -> GenerationMetadata:
    """Structurally read one generation-metadata payload of any accepted form."""
    if isinstance(payload, GenerationMetadata):
        return payload
    if isinstance(payload, (str, bytes)):
        return _parse_metadata_json(payload)
    if isinstance(payload, Mapping):
        return _parse_metadata_json(json.dumps(dict(payload)))
    raise metadata_error(
        EngineErrorCode.INVALID_GENERATION_METADATA,
        "parse",
        (),
        "a generation-metadata document must be a JSON object.",
    )


def _negotiate(document: GenerationMetadata) -> None:
    """Fail closed on an out-of-range recorded schema or protocol integer."""
    if document.metadata_version not in _SUPPORTED_GENERATION_METADATA_VERSIONS:
        raise metadata_error(
            EngineErrorCode.UNSUPPORTED_GENERATION_METADATA,
            "validate",
            ("metadata_version",),
            f"metadata_version {document.metadata_version!r} is not supported; "
            f"this engine reads {sorted(_SUPPORTED_GENERATION_METADATA_VERSIONS)}.",
        )
    if document.protocols.projectspec not in SUPPORTED_PROJECTSPEC_PROTOCOLS:
        raise metadata_error(
            EngineErrorCode.UNSUPPORTED_GENERATION_METADATA,
            "validate",
            ("protocols", "projectspec"),
            f"recorded ProjectSpec protocol {document.protocols.projectspec!r} is "
            f"outside the supported set {list(SUPPORTED_PROJECTSPEC_PROTOCOLS)}.",
        )
    unsupported = sorted(
        protocol
        for protocol in document.protocols.component_manifest
        if protocol not in SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS
    )
    if unsupported:
        raise metadata_error(
            EngineErrorCode.UNSUPPORTED_GENERATION_METADATA,
            "validate",
            ("protocols", "component_manifest"),
            f"recorded component-manifest protocol(s) {unsupported} are outside "
            f"the supported set {list(SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS)}.",
        )


def _validate_recorded_selection(
    document: GenerationMetadata, *, require_version_match: bool = True
) -> ProjectSpec:
    """Check the embedded spec parses and every recorded component is real.

    ``require_version_match=True`` -- the default, and what
    ``parse_generation_metadata`` uses unchanged -- additionally requires each
    recorded component version to equal the installed one: right for the
    reproduce path, where the recorded release and the running engine must be
    the same release. ``plan_update`` reads with
    ``require_version_match=False``: an update is by definition an old
    document read on a newer engine, so a drifted component version is
    expected input, not a failure (docs/generation-provenance.md).
    """
    try:
        spec = _discovery.parse_spec(document.spec)
    except ForgeEngineError as exc:
        raise metadata_error(
            EngineErrorCode.INVALID_GENERATION_METADATA,
            "validate",
            ("spec",),
            "the embedded ProjectSpec does not parse.",
        ) from exc

    catalogue = {component.id: component.version for component in _discovery.discover()}
    for index, component in enumerate(document.components):
        if component.id not in catalogue:
            raise metadata_error(
                EngineErrorCode.INVALID_GENERATION_METADATA,
                "validate",
                ("components", index),
                f"recorded component {component.id!r} is not in the installed "
                "catalogue.",
            )
        if require_version_match and catalogue[component.id] != component.version:
            raise metadata_error(
                EngineErrorCode.INVALID_GENERATION_METADATA,
                "validate",
                ("components", index, "version"),
                f"recorded {component.id!r} version {component.version!r} does not "
                f"match the installed {catalogue[component.id]!r}.",
            )

    selected = {
        spec.components.archetype,
        *spec.components.capabilities,
        *spec.components.platforms,
    }
    if {component.id for component in document.components} != selected:
        raise metadata_error(
            EngineErrorCode.INVALID_GENERATION_METADATA,
            "validate",
            ("components",),
            "recorded components do not match the embedded spec's selection.",
        )
    return spec


def parse(payload: object) -> GenerationMetadata:
    """Structural read, negotiation, and exact recorded-selection check."""
    document = _document(payload)
    _negotiate(document)
    _validate_recorded_selection(document)
    return document


def verify(metadata: GenerationMetadata, project: RenderedProject) -> None:
    """Check a document's digests and coverage against a re-rendered project."""
    rendered = {file.target: file.content for file in project.files}
    if {entry.target for entry in metadata.output} != set(rendered):
        raise metadata_error(
            EngineErrorCode.INVALID_GENERATION_METADATA,
            "validate",
            ("output",),
            "recorded output does not cover exactly the reproduced targets.",
        )
    for index, entry in enumerate(metadata.output):
        if entry.digest != _digest(rendered[entry.target]):
            raise metadata_error(
                EngineErrorCode.INVALID_GENERATION_METADATA,
                "validate",
                ("output", index, "digest"),
                f"recorded digest for {entry.target!r} does not match the "
                "reproduced content.",
            )


def _renames_between(
    document: GenerationMetadata, new: RenderedProject
) -> tuple[AppliedRename, ...]:
    """Surface owner-declared renames whose ``since`` falls in the update window.

    For each component recorded in ``document`` that is still selected in
    ``new``, keeps the installed manifest's ``[[renames]]`` records where
    ``recorded < since <= installed`` (docs/generation-provenance.md#
    owner-declared-rename-records). A component the new selection dropped
    contributes none -- its content is gone either way.
    """
    manifests = {
        record.manifest.id: record.manifest for record in _discovery.load_catalogue()
    }
    recorded_versions = {
        component.id: component.version for component in document.components
    }
    still_selected = set(new.plan.component_order)

    applied: list[AppliedRename] = []
    for component_id, recorded_version in recorded_versions.items():
        if component_id not in still_selected:
            continue
        manifest = manifests.get(component_id)
        if manifest is None:
            continue
        recorded = Version(recorded_version)
        installed = Version(manifest.version)
        for record in manifest.renames:
            since = Version(record.since)
            if recorded < since <= installed:
                applied.append(
                    AppliedRename(
                        component_id=component_id,
                        to=record.to,
                        since=record.since,
                        **{"from": record.from_},
                    )
                )
    return tuple(
        sorted(applied, key=lambda rename: (rename.component_id, rename.from_))
    )


def _classify_update(
    old: Mapping[str, bytes],
    new: Mapping[str, bytes],
    renames: tuple[AppliedRename, ...],
) -> dict[str, UpdateClassification]:
    """Classify each target across an old/new render pair.

    Every value is one of the five documented classifications
    (docs/generation-provenance.md#update-inputs). Renames are applied first,
    so a moved-and-edited file is reported once, under its new target, as
    ``"renamed"`` -- the old target never also appears as ``"removed"``.
    Promoted from the ADR 0062 placeholder that lived in
    ``tests/generation_provenance_contract.py``.
    """
    moved = {rename.from_: rename.to for rename in renames}
    result: dict[str, UpdateClassification] = {}
    for source, destination in moved.items():
        if source in old and destination in new:
            result[destination] = "renamed"
    for target in old.keys() | new.keys():
        if target in result or target in moved:
            continue
        if target in old and target in new:
            result[target] = "unchanged" if old[target] == new[target] else "changed"
        elif target in new:
            result[target] = "added"
        else:
            result[target] = "removed"
    return result


def plan_update(
    recorded: object, *, old: Mapping[str, bytes], new: RenderedProject
) -> UpdatePlan:
    """Lenient read, fail-closed input checks, then rename-aware classification.

    See :func:`forge_template.plan_update` for the supported contract.
    """
    document = _document(recorded)
    _negotiate(document)
    _validate_recorded_selection(document, require_version_match=False)

    if not old and document.output:
        raise metadata_error(
            EngineErrorCode.UNSUPPORTED_GENERATION_METADATA,
            "validate",
            ("provider",),
            f"recorded provider version {document.provider.version!r} was not "
            "supplied as reproduced old-render input; provision that exact "
            "forge-template release and reproduce it, or record an explicit "
            "degraded two-way update.",
        )

    recorded_targets = {entry.target for entry in document.output}
    if recorded_targets != set(old):
        raise metadata_error(
            EngineErrorCode.INVALID_GENERATION_METADATA,
            "validate",
            ("output",),
            "the supplied old render does not match the recorded output target set.",
        )
    for entry in document.output:
        if entry.digest != _digest(old[entry.target]):
            raise metadata_error(
                EngineErrorCode.INVALID_GENERATION_METADATA,
                "validate",
                ("output",),
                f"the supplied old render does not match the recorded digest "
                f"for {entry.target!r}.",
            )

    renames = _renames_between(document, new)
    new_content = {file.target: file.content for file in new.files}
    classification = _classify_update(old, new_content, renames)

    new_by_target = {item.target: item for item in new.plan.files}
    recorded_by_target = {entry.target: entry for entry in document.output}
    targets = tuple(
        UpdateTarget(
            target=target,
            classification=kind,
            owner=(
                _owner_token(new_by_target[target].owner)
                if target in new_by_target
                else recorded_by_target[target].owner
            ),
            regeneration=(
                new_by_target[target].regeneration
                if target in new_by_target
                else recorded_by_target[target].regeneration
            ),
        )
        for target, kind in sorted(classification.items())
    )
    return UpdatePlan(
        targets=targets,
        renames=renames,
        reproduction=ReproductionRecord(mode="exact"),
    )
