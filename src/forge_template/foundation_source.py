"""The implicit, mandatory, non-selectable Foundation content source.

Foundation is not a component: it has no identifier, kind, version,
compatibility, dependencies, conflicts, contributions, or options, and it
never appears in ProjectSpec selections, ``discover_components()``, or
``GenerationPlan.component_order``. It is the one content source composition
always applies before every selected component -- see
[docs/foundation-scope.md](../../../docs/foundation-scope.md) and the
accepted [Library archetype contract](../../../docs/library-archetype.md)
(FT-08.01/ADR 0031).

This module mirrors ``forge_template.component_manifest``'s shape for a
source that is not a component: strict loading and owned-resource
containment, reusing that module's ``component_resource_path`` and
``relative_resource_path`` rather than duplicating either, plus published
extension points -- without any of the identity, compatibility, or
relationship concerns that only apply to a selectable component. It performs
no file operations beyond loading its own manifest and does not decide output
targets, dispositions, or collision safety; that remains
``forge_template.file_conflicts``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path, PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from forge_template.component_manifest import (
    ExtensionPoint,
    RelativeResourcePath,
    component_resource_path,
    relative_resource_path,
)

FOUNDATION_SOURCE_PROTOCOL_VERSION: Literal[1] = 1
"""The only Foundation source manifest protocol understood by this engine
line."""


class _FoundationModel(BaseModel):
    """Shared strict and immutable behaviour for Foundation source objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FoundationSource(_FoundationModel):
    """The one bundled, package-relative Foundation content declaration."""

    foundation_version: Literal[1]
    content_root: RelativeResourcePath
    extension_points: tuple[ExtensionPoint, ...] = ()

    @field_validator("foundation_version", mode="before")
    @classmethod
    def _validate_strict_foundation_version(cls, value: object) -> object:
        if type(value) is not int:
            msg = "foundation_version must be a strict integer"
            raise ValueError(msg)
        return value

    @field_validator("content_root")
    @classmethod
    def _validate_content_root(cls, value: str) -> str:
        return relative_resource_path(value)

    @field_validator("extension_points", mode="before")
    @classmethod
    def _normalise_extension_points(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("extension_points")
    @classmethod
    def _canonicalise_extension_points(
        cls, value: tuple[ExtensionPoint, ...]
    ) -> tuple[ExtensionPoint, ...]:
        identifiers = [point.id for point in value]
        if len(identifiers) != len(set(identifiers)):
            msg = "extension point identifiers must not contain duplicates"
            raise ValueError(msg)
        return tuple(sorted(value, key=lambda point: point.id))

    @model_validator(mode="after")
    def _validate_extension_points_inside_content_root(self) -> Self:
        content_root = PurePosixPath(self.content_root)
        for point in self.extension_points:
            if not PurePosixPath(point.content).is_relative_to(content_root):
                msg = (
                    f"extension point {point.id!r} content {point.content!r} must "
                    f"fall inside content_root {self.content_root!r}"
                )
                raise ValueError(msg)
        return self


def load_foundation_source(path: str | Path) -> FoundationSource:
    """Load one ``foundation.toml`` and validate its owned resources.

    Mirrors ``component_manifest.load_component_manifest``'s existence and
    containment checks for a source that is not itself a component: no
    ``options_schema``, ``requires``, ``conflicts``, or ``contributions`` --
    Foundation is unselectable, has no options, and contributes to nothing.
    """
    manifest_path = Path(path)
    if manifest_path.name != "foundation.toml":
        msg = "the Foundation source manifest must be named 'foundation.toml'"
        raise ValueError(msg)

    resolved_manifest = manifest_path.resolve(strict=True)
    with resolved_manifest.open("rb") as manifest_file:
        source = FoundationSource.model_validate(tomllib.load(manifest_file))

    content_root = component_resource_path(resolved_manifest, source.content_root)
    if not content_root.is_dir():
        msg = f"content_root is not a directory: {source.content_root!r}"
        raise ValueError(msg)
    source_directory = resolved_manifest.parent.resolve(strict=True)
    content_files: list[Path] = []
    for resource in content_root.rglob("*"):
        if not resource.resolve(strict=True).is_relative_to(source_directory):
            msg = f"content resource escapes Foundation directory: {resource}"
            raise ValueError(msg)
        if resource.is_file():
            content_files.append(resource)
    if not content_files:
        msg = f"content_root is empty: {source.content_root!r}"
        raise ValueError(msg)

    for point in source.extension_points:
        point_content = component_resource_path(resolved_manifest, point.content)
        if not point_content.is_file():
            msg = (
                f"extension point {point.id!r} content is not a file: {point.content!r}"
            )
            raise ValueError(msg)

    return source


def foundation_content_order(path: str | Path) -> tuple[str, ...]:
    """Return Foundation's owned content in ascending POSIX-path order.

    Calling ``load_foundation_source`` first reuses its existence and
    containment validation; this function replaces ``rglob``'s
    filesystem-dependent enumeration order with a stable, explicit one --
    mirroring ``composition.component_content_order``.
    """
    resolved_path = Path(path)
    source = load_foundation_source(resolved_path)
    content_root = (
        resolved_path.resolve(strict=True).parent / source.content_root
    ).resolve(strict=True)

    relative_paths = (
        resource.relative_to(content_root).as_posix()
        for resource in content_root.rglob("*")
        if resource.is_file()
    )
    return tuple(sorted(relative_paths))


class FoundationPlacement(_FoundationModel):
    """The loaded Foundation source and its ordered owned content.

    Mirrors ``forge_template.composition.ComponentPlacement`` for the one
    content source that is not a component, so
    ``forge_template.file_conflicts.resolve_output_plan`` reads Foundation
    through the same shape -- a validated source plus its deterministic
    content order -- that it already reads every component placement
    through.
    """

    source: FoundationSource
    content_paths: tuple[str, ...]


def foundation_placement(path: str | Path) -> FoundationPlacement:
    """Return Foundation's loaded source and its deterministic content order."""
    resolved_path = Path(path)
    return FoundationPlacement(
        source=load_foundation_source(resolved_path),
        content_paths=foundation_content_order(resolved_path),
    )
