"""Strict component manifest protocol models and provisional validators.

This module defines the low-level, machine-readable metadata consumed by
Forge's future composition engine.  It deliberately does not discover
components, order them, render their content, or expose stable engine errors;
those remain later Stage 06 work.
"""

from __future__ import annotations

import graphlib
import tomllib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated, Literal, Self

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from forge_template.project_spec import ProjectSpec

COMPONENT_MANIFEST_PROTOCOL_VERSION = 1
"""The only component manifest protocol understood by this engine line."""

_NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_ForgeIdentifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"),
]
_RelativeResourcePath = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_ProtocolSet = Annotated[
    tuple[Literal[1], ...],
    Field(min_length=1),
]


class _ManifestModel(BaseModel):
    """Shared strict and immutable behaviour for manifest objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _canonical_version(value: str) -> str:
    try:
        parsed = Version(value)
    except InvalidVersion as exc:
        msg = f"invalid PEP 440 version: {value!r}"
        raise ValueError(msg) from exc

    canonical = str(parsed)
    if value != canonical:
        msg = f"component version must be canonical PEP 440: use {canonical!r}"
        raise ValueError(msg)
    return value


def _canonical_specifier(value: str, *, field: str) -> str:
    if not value.strip():
        msg = f"{field} must not be empty"
        raise ValueError(msg)
    try:
        return str(SpecifierSet(value))
    except InvalidSpecifier as exc:
        msg = f"invalid PEP 440 specifier for {field}: {value!r}"
        raise ValueError(msg) from exc


def _relative_resource_path(value: str) -> str:
    if "\\" in value:
        msg = "resource paths must use forward slashes"
        raise ValueError(msg)

    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or value != path.as_posix()
        or path == PurePosixPath(".")
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        msg = "resource paths must be normalised component-relative paths"
        raise ValueError(msg)
    return value


class ComponentReference(_ManifestModel):
    """A hard dependency or incompatibility with another component."""

    id: _ForgeIdentifier
    version: str | None = None

    @field_validator("version")
    @classmethod
    def _validate_version_specifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _canonical_specifier(value, field="component reference version")

    def accepts(self, component_version: str) -> bool:
        """Return whether a packaged component version matches this reference."""
        return self.version is None or Version(component_version) in SpecifierSet(
            self.version
        )


class ComponentCompatibility(_ManifestModel):
    """ProjectSpec protocol and generated-Python requirements."""

    projectspec_protocols: _ProtocolSet
    requires_python: str

    @field_validator("projectspec_protocols", mode="before")
    @classmethod
    def _normalise_protocol_array(cls, value: object) -> object:
        if isinstance(value, list):
            value = tuple(value)
        if isinstance(value, tuple) and any(type(item) is not int for item in value):
            msg = "ProjectSpec protocol versions must be strict integers"
            raise ValueError(msg)
        return value

    @field_validator("projectspec_protocols")
    @classmethod
    def _canonicalise_protocols(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if len(value) != len(set(value)):
            msg = "ProjectSpec protocol compatibility must not contain duplicates"
            raise ValueError(msg)
        return tuple(sorted(value))

    @field_validator("requires_python")
    @classmethod
    def _validate_requires_python(cls, value: str) -> str:
        return _canonical_specifier(value, field="requires_python")

    def supports(self, spec: ProjectSpec) -> bool:
        """Return whether this component supports the complete ProjectSpec range."""
        python_requirement = SpecifierSet(self.requires_python)
        return spec.protocol_version in self.projectspec_protocols and all(
            Version(version) in python_requirement
            for version in spec.python.tested_versions
        )


class ComponentManifest(_ManifestModel):
    """One bundled archetype, capability, or platform declaration."""

    manifest_version: Literal[1]
    id: _ForgeIdentifier
    name: _NonEmptyString
    description: _NonEmptyString
    kind: Literal["archetype", "capability", "platform"]
    version: str
    content_root: _RelativeResourcePath
    options_schema: _RelativeResourcePath | None = None
    compatibility: ComponentCompatibility
    requires: tuple[ComponentReference, ...] = ()
    conflicts: tuple[ComponentReference, ...] = ()

    @field_validator("manifest_version", mode="before")
    @classmethod
    def _validate_strict_manifest_version(cls, value: object) -> object:
        if type(value) is not int:
            msg = "manifest_version must be a strict integer"
            raise ValueError(msg)
        return value

    @field_validator("version")
    @classmethod
    def _validate_component_version(cls, value: str) -> str:
        return _canonical_version(value)

    @field_validator("content_root", "options_schema")
    @classmethod
    def _validate_resource_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _relative_resource_path(value)

    @field_validator("requires", "conflicts", mode="before")
    @classmethod
    def _normalise_reference_array(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("requires", "conflicts")
    @classmethod
    def _canonicalise_references(
        cls, value: tuple[ComponentReference, ...]
    ) -> tuple[ComponentReference, ...]:
        identifiers = [reference.id for reference in value]
        if len(identifiers) != len(set(identifiers)):
            msg = "component references must not contain duplicate identifiers"
            raise ValueError(msg)
        return tuple(sorted(value, key=lambda reference: reference.id))

    @model_validator(mode="after")
    def _validate_reference_relationships(self) -> Self:
        required = {reference.id for reference in self.requires}
        conflicting = {reference.id for reference in self.conflicts}
        if self.id in required or self.id in conflicting:
            msg = "a component must not reference itself"
            raise ValueError(msg)

        contradictory = sorted(required & conflicting)
        if contradictory:
            msg = "components cannot be both required and conflicting: " + ", ".join(
                contradictory
            )
            raise ValueError(msg)
        return self


def _resource_path(manifest_path: Path, relative_path: str) -> Path:
    component_root = manifest_path.parent.resolve(strict=True)
    candidate = (component_root / Path(*PurePosixPath(relative_path).parts)).resolve(
        strict=True
    )
    if not candidate.is_relative_to(component_root):
        msg = f"resource escapes component directory: {relative_path!r}"
        raise ValueError(msg)
    return candidate


def load_component_manifest(path: str | Path) -> ComponentManifest:
    """Load one ``component.toml`` and validate its owned resources."""
    manifest_path = Path(path)
    if manifest_path.name != "component.toml":
        msg = "component manifests must be named 'component.toml'"
        raise ValueError(msg)

    resolved_manifest = manifest_path.resolve(strict=True)
    with resolved_manifest.open("rb") as manifest_file:
        manifest = ComponentManifest.model_validate(tomllib.load(manifest_file))

    content_root = _resource_path(resolved_manifest, manifest.content_root)
    if not content_root.is_dir():
        msg = f"content_root is not a directory: {manifest.content_root!r}"
        raise ValueError(msg)
    component_directory = resolved_manifest.parent.resolve(strict=True)
    content_files: list[Path] = []
    for resource in content_root.rglob("*"):
        if not resource.resolve(strict=True).is_relative_to(component_directory):
            msg = f"content resource escapes component directory: {resource}"
            raise ValueError(msg)
        if resource.is_file():
            content_files.append(resource)
    if not content_files:
        msg = f"content_root is empty: {manifest.content_root!r}"
        raise ValueError(msg)

    if manifest.options_schema is not None:
        options_schema = _resource_path(resolved_manifest, manifest.options_schema)
        if not options_schema.is_file():
            msg = f"options_schema is not a file: {manifest.options_schema!r}"
            raise ValueError(msg)

    return manifest


def _reject_dependency_cycles(manifests: Iterable[ComponentManifest]) -> None:
    """Reject a catalogue whose ``requires`` edges form a cycle.

    This runs catalogue-wide, independent of component kind, so a cyclic
    bundled catalogue fails at packaging and review time rather than only
    when some future selection happens to include both ends of the cycle.
    Composition order itself is decided by
    ``forge_template.composition``, which orders each kind tier separately;
    this check only proves the underlying dependency graph is acyclic.
    """
    graph = {
        manifest.id: tuple(reference.id for reference in manifest.requires)
        for manifest in manifests
    }
    sorter: graphlib.TopologicalSorter[str] = graphlib.TopologicalSorter(graph)
    try:
        sorter.prepare()
    except graphlib.CycleError as exc:
        cycle = " -> ".join(str(node) for node in exc.args[1])
        msg = f"component dependency graph contains a cycle: {cycle}"
        raise ValueError(msg) from exc


def validate_manifest_set(
    manifests: Iterable[ComponentManifest],
) -> tuple[ComponentManifest, ...]:
    """Validate cross-manifest identity and reference integrity.

    The lexical return order supports deterministic catalogue inspection only;
    it is explicitly not composition order.
    """
    manifest_tuple = tuple(manifests)
    by_id = {manifest.id: manifest for manifest in manifest_tuple}
    if len(by_id) != len(manifest_tuple):
        msg = "component identifiers must be globally unique"
        raise ValueError(msg)

    for manifest in manifest_tuple:
        for reference in (*manifest.requires, *manifest.conflicts):
            target = by_id.get(reference.id)
            if target is None:
                msg = (
                    f"component {manifest.id!r} references missing component "
                    f"{reference.id!r}"
                )
                raise ValueError(msg)
            if not reference.accepts(target.version):
                constraint = reference.version or "any version"
                msg = (
                    f"component {manifest.id!r} references {reference.id!r} "
                    f"with {constraint!r}, found {target.version!r}"
                )
                raise ValueError(msg)

    _reject_dependency_cycles(manifest_tuple)

    return tuple(sorted(manifest_tuple, key=lambda manifest: manifest.id))


def validate_manifest_selection(
    spec: ProjectSpec,
    manifests: Iterable[ComponentManifest],
) -> tuple[ComponentManifest, ...]:
    """Validate an effective ProjectSpec against provisional manifest metadata."""
    catalogue = validate_manifest_set(manifests)
    by_id = {manifest.id: manifest for manifest in catalogue}

    selections = (
        (spec.components.archetype, "archetype"),
        *((identifier, "capability") for identifier in spec.components.capabilities),
        *((identifier, "platform") for identifier in spec.components.platforms),
    )
    selection_ids = [identifier for identifier, _kind in selections]
    if len(selection_ids) != len(set(selection_ids)):
        msg = "ProjectSpec must not select one component under multiple kinds"
        raise ValueError(msg)
    selected_kinds = dict(selections)
    selected: list[ComponentManifest] = []
    for identifier, expected_kind in selected_kinds.items():
        manifest = by_id.get(identifier)
        if manifest is None:
            msg = f"ProjectSpec selects unknown component {identifier!r}"
            raise ValueError(msg)
        if manifest.kind != expected_kind:
            msg = (
                f"ProjectSpec selects {identifier!r} as {expected_kind}, "
                f"but its manifest kind is {manifest.kind}"
            )
            raise ValueError(msg)
        if not manifest.compatibility.supports(spec):
            msg = f"component {identifier!r} is incompatible with this ProjectSpec"
            raise ValueError(msg)
        selected.append(manifest)

    selected_ids = set(selected_kinds)
    for manifest in selected:
        missing = sorted(
            reference.id
            for reference in manifest.requires
            if reference.id not in selected_ids
        )
        if missing:
            msg = (
                f"component {manifest.id!r} requires selected component(s): "
                + ", ".join(missing)
            )
            raise ValueError(msg)

        conflicts = sorted(
            reference.id
            for reference in manifest.conflicts
            if reference.id in selected_ids
        )
        if conflicts:
            msg = (
                f"component {manifest.id!r} conflicts with selected component(s): "
                + ", ".join(conflicts)
            )
            raise ValueError(msg)

    return tuple(sorted(selected, key=lambda manifest: manifest.id))
