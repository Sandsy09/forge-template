"""Catalogue discovery and ProjectSpec validation (private engine module).

ADR 0079. Discovers only the components and Foundation source bundled in the
installed ``forge-template`` distribution, parses the ProjectSpec wire
format, and validates a selection and its options against the catalogue.
Reads package resources only; never writes.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from pydantic import ValidationError

from forge_template._errors import (
    EngineErrorCode,
    ForgeEngineError,
    single_detail,
    validation_details,
)
from forge_template._models import (
    ComponentDescriptor,
    ComponentOption,
    ComponentRelation,
)
from forge_template.component_manifest import (
    ComponentManifest,
    load_component_manifest,
    validate_manifest_selection,
    validate_manifest_set,
)
from forge_template.foundation_source import FoundationPlacement, foundation_placement
from forge_template.project_spec import ProjectSpec
from forge_template.template_variables import (
    OptionSchema,
    load_option_schema,
    resolve_template_variables,
)

# Deliberately private: tests replace this with the checked-in fixture
# catalogue (through tests/engine_seams.py). Public clients cannot redirect
# discovery to arbitrary content.
_CATALOGUE_ROOT_OVERRIDE: Path | None = None

# Deliberately private, mirroring _CATALOGUE_ROOT_OVERRIDE: tests replace this
# with a fixture Foundation source. Public clients cannot redirect Foundation
# to arbitrary content either.
_FOUNDATION_ROOT_OVERRIDE: Path | None = None


@dataclass(frozen=True)
class ComponentRecord:
    manifest_path: Path
    manifest: ComponentManifest
    option_schema: OptionSchema


@dataclass(frozen=True)
class FoundationRecord:
    """The installed Foundation source's manifest path and loaded placement.

    Mirrors ``ComponentRecord`` for the one content source that is not a
    component: ``manifest_path`` is what every owned-resource lookup
    (``_rendering``'s Foundation source resolution) resolves against, exactly
    as ``ComponentRecord.manifest_path`` does for a component.
    """

    manifest_path: Path
    placement: FoundationPlacement


def parse_spec(payload: object) -> ProjectSpec:
    """Strictly parse one ProjectSpec wire payload without catalogue access."""
    if isinstance(payload, ProjectSpec):
        return payload

    try:
        if isinstance(payload, (str, bytes)):
            return ProjectSpec.model_validate_json(payload)
        if isinstance(payload, Mapping):
            return ProjectSpec.model_validate_json(json.dumps(dict(payload)))
    except (TypeError, ValueError, ValidationError) as exc:
        details = (
            validation_details(exc)
            if isinstance(exc, ValidationError)
            else single_detail("invalid-json-value", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.INVALID_PROJECT_SPEC,
            operation="parse",
            message="ProjectSpec is invalid.",
            details=details,
        ) from exc

    message = "ProjectSpec input must be a ProjectSpec, mapping, JSON string, or bytes."
    raise ForgeEngineError(
        code=EngineErrorCode.INVALID_PROJECT_SPEC,
        operation="parse",
        message=message,
        details=single_detail("invalid-input-type", message),
    )


@contextmanager
def _catalogue_directory() -> Iterator[Path]:
    if _CATALOGUE_ROOT_OVERRIDE is not None:
        yield _CATALOGUE_ROOT_OVERRIDE.resolve(strict=True)
        return

    package_root = resources.files("forge_template.components")
    with resources.as_file(package_root) as resolved:
        yield resolved


@contextmanager
def _foundation_directory() -> Iterator[Path | None]:
    """Yield the installed Foundation package directory, or ``None``.

    ``None`` means "no Foundation source is bundled at all" -- true of every
    engine release before FT-08.02 ships production Foundation content, and
    still not an error by itself: nothing forces a caller to need Foundation
    unless a real selection's resolved output plan actually requires it (see
    ``resolve_output_plan``'s own "none is available" failure for that case).
    """
    if _FOUNDATION_ROOT_OVERRIDE is not None:
        yield _FOUNDATION_ROOT_OVERRIDE.resolve(strict=True)
        return

    try:
        package_root = resources.files("forge_template.foundation")
    except ModuleNotFoundError:
        yield None
        return
    with resources.as_file(package_root) as resolved:
        yield resolved


def load_foundation() -> FoundationRecord | None:
    try:
        with _foundation_directory() as root:
            if root is None:
                return None
            manifest_path = root / "foundation.toml"
            if not manifest_path.is_file():
                return None
            return FoundationRecord(
                manifest_path=manifest_path,
                placement=foundation_placement(manifest_path),
            )
    except (FileNotFoundError, OSError) as exc:
        raise ForgeEngineError(
            code=EngineErrorCode.COMPONENT_DISCOVERY_FAILED,
            operation="discover",
            message="The installed Foundation content source could not be read.",
            details=single_detail("foundation-unavailable", str(exc)),
        ) from exc
    except (ValueError, ValidationError) as exc:
        details = (
            validation_details(exc)
            if isinstance(exc, ValidationError)
            else single_detail("invalid-foundation", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.COMPONENT_DISCOVERY_FAILED,
            operation="discover",
            message="The installed Foundation content source is invalid.",
            details=details,
        ) from exc


def load_catalogue() -> tuple[ComponentRecord, ...]:
    try:
        with _catalogue_directory() as root:
            manifest_paths = tuple(sorted(root.rglob("component.toml")))
            loaded = tuple(
                (path, load_component_manifest(path)) for path in manifest_paths
            )
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise ForgeEngineError(
            code=EngineErrorCode.COMPONENT_DISCOVERY_FAILED,
            operation="discover",
            message="The installed component catalogue could not be read.",
            details=single_detail("catalogue-unavailable", str(exc)),
        ) from exc
    except (ValueError, ValidationError) as exc:
        details = (
            validation_details(exc)
            if isinstance(exc, ValidationError)
            else single_detail("invalid-manifest", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.COMPONENT_DISCOVERY_FAILED,
            operation="discover",
            message="The installed component catalogue is invalid.",
            details=details,
        ) from exc

    foundation = load_foundation()
    try:
        validate_manifest_set(
            (manifest for _path, manifest in loaded),
            foundation.placement.source if foundation is not None else None,
        )
        return tuple(
            ComponentRecord(
                manifest_path=path,
                manifest=manifest,
                option_schema=load_option_schema(path, manifest),
            )
            for path, manifest in loaded
        )
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        details = (
            validation_details(exc)
            if isinstance(exc, ValidationError)
            else single_detail("invalid-catalogue", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.COMPONENT_DISCOVERY_FAILED,
            operation="discover",
            message="The installed component catalogue is invalid.",
            details=details,
        ) from exc


def descriptor(record: ComponentRecord) -> ComponentDescriptor:
    manifest = record.manifest
    return ComponentDescriptor(
        id=manifest.id,
        name=manifest.name,
        description=manifest.description,
        kind=manifest.kind,
        version=manifest.version,
        projectspec_protocols=manifest.compatibility.projectspec_protocols,
        requires_python=manifest.compatibility.requires_python,
        requires=tuple(
            ComponentRelation(id=reference.id, version=reference.version)
            for reference in manifest.requires
        ),
        conflicts=tuple(
            ComponentRelation(id=reference.id, version=reference.version)
            for reference in manifest.conflicts
        ),
        options=tuple(
            ComponentOption(
                name=option.name,
                type=option.type,
                required=option.required,
                default=option.default,
                choices=option.choices,
                description=option.description,
                format=option.format,
            )
            for option in record.option_schema.options
        ),
    )


def discover() -> tuple[ComponentDescriptor, ...]:
    """The installed, reviewed component catalogue in lexical order."""
    return tuple(descriptor(record) for record in load_catalogue())


def validate_against_catalogue(
    spec: ProjectSpec,
    records: tuple[ComponentRecord, ...],
    foundation: FoundationRecord | None,
) -> None:
    manifests = tuple(record.manifest for record in records)
    try:
        validate_manifest_selection(
            spec,
            manifests,
            foundation.placement.source if foundation is not None else None,
        )
    except (ValueError, ValidationError) as exc:
        details = (
            validation_details(exc)
            if isinstance(exc, ValidationError)
            else single_detail("invalid-selection", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.INVALID_COMPONENT_SELECTION,
            operation="validate",
            message="ProjectSpec component selection is invalid.",
            details=details,
        ) from exc

    schemas = {record.manifest.id: record.option_schema for record in records}
    try:
        resolve_template_variables(spec, schemas)
    except (ValueError, ValidationError) as exc:
        details = (
            validation_details(exc)
            if isinstance(exc, ValidationError)
            else single_detail("invalid-options", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.INVALID_COMPONENT_OPTIONS,
            operation="validate",
            message="ProjectSpec component options are invalid.",
            details=details,
        ) from exc


def validate_spec(spec: ProjectSpec) -> ProjectSpec:
    """Validate a parsed ProjectSpec against the installed component catalogue."""
    validate_against_catalogue(spec, load_catalogue(), load_foundation())
    return spec
