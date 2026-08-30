"""Strict component manifest protocol models and provisional validators.

This module defines the low-level, machine-readable metadata consumed by
Forge's composition engine.  It deliberately does not discover components,
order them, render their content, or expose stable engine errors; those
remain later Stage 06/08 work.

Two manifest protocols are understood. Protocol 1 (FT-06.02/ADR 0024) models
component-to-component contributions only. Protocol 2 (FT-08.02/ADR 0031, ADR
0033) adds a discriminated contribution ``target`` so a contribution can also
name the implicit Foundation content source -- see
``forge_template.foundation_source`` -- rather than only another component.
Protocol 1 parsing remains supported unchanged for existing
component-to-component fixtures; see docs/component-manifests.md.
"""

from __future__ import annotations

import graphlib
import tomllib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Annotated, Literal, Self

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

if TYPE_CHECKING:
    from forge_template.foundation_source import FoundationSource

COMPONENT_MANIFEST_PROTOCOL_VERSIONS: tuple[Literal[1, 2], ...] = (1, 2)
"""Every component manifest protocol this engine line understands.

Protocol 1 predates the Foundation content source and models
component-to-component contributions only. Protocol 2, added by FT-08.02,
adds the discriminated Foundation/component contribution target. Both remain
valid input on one manifest_version-keyed model.
"""

_NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_ForgeIdentifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"),
]
RelativeResourcePath = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
"""One component- or Foundation-relative resource path. Validated by
``relative_resource_path`` below; promoted to a public name so
``forge_template.foundation_source`` and
``forge_template.file_conflicts.render_output_path`` can reuse both the type
and the validator rather than duplicating either."""
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


def relative_resource_path(value: str) -> str:
    """Validate one component- or Foundation-relative resource path.

    Rejects backslashes, absolute paths (POSIX or Windows), and any ``.`` or
    ``..`` segment -- the same containment rule ``load_component_manifest``
    and ``load_foundation_source`` apply to every owned resource, and that
    ``forge_template.file_conflicts.render_output_path`` applies to a
    *rendered* output path so a template variable can never redirect output
    outside the project tree.
    """
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


class ExtensionPoint(_ManifestModel):
    """One named point an owner publishes for another to extend.

    Shared between a component's own ``[[extension_points]]`` and the
    Foundation content source's -- both name an ``id`` and an owner-relative
    ``content`` path, and both are validated the same way, so this one model
    covers either owner.
    """

    id: _ForgeIdentifier
    content: RelativeResourcePath
    """Owner-relative path to the owned file this point lives in. Must fall
    inside the owner's own ``content_root``: an extension point extends
    content the owner itself emits, not an arbitrary resource."""


class ComponentTarget(_ManifestModel):
    """A contribution targets another component's extension point."""

    kind: Literal["component"] = "component"
    id: _ForgeIdentifier


class FoundationTarget(_ManifestModel):
    """A contribution targets the implicit Foundation content source."""

    kind: Literal["foundation"] = "foundation"


ContributionTarget = Annotated[
    ComponentTarget | FoundationTarget,
    Field(discriminator="kind"),
]
"""Protocol 2's discriminated contribution owner. Protocol 1's flat
``component = "id"`` key is normalised into ``ComponentTarget`` by
``Contribution``'s own before-validator, so every parsed manifest -- either
protocol -- exposes this one typed field."""


class Contribution(_ManifestModel):
    """An additive contribution into another owner's extension point."""

    target: ContributionTarget
    extension_point: _ForgeIdentifier
    content: RelativeResourcePath
    """Component-relative path to the contributed payload. Must fall outside
    ``content_root``: a contribution is not itself an owned output file, so it
    must not also be emitted at its own target."""

    @model_validator(mode="before")
    @classmethod
    def _normalise_legacy_target(cls, value: object) -> object:
        """Accept protocol 1's flat ``component = "id"`` key.

        Protocol 1 names a target component directly. Protocol 2 replaces
        that with a discriminated ``target`` table so a Foundation target
        becomes representable. Rewriting here keeps every existing protocol-1
        fixture and manifest parsing unchanged rather than requiring a second
        code path through the rest of this module.
        """
        if not isinstance(value, dict):
            return value
        if "target" in value and "component" in value:
            msg = "a contribution must not declare both 'target' and 'component'"
            raise ValueError(msg)
        if "component" in value:
            value = dict(value)
            value["target"] = {"kind": "component", "id": value.pop("component")}
        return value


def _contribution_target_key(contribution: Contribution) -> tuple[str, str]:
    target = contribution.target
    if isinstance(target, FoundationTarget):
        return ("foundation", "")
    return ("component", target.id)


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

    manifest_version: Literal[1, 2]
    id: _ForgeIdentifier
    name: _NonEmptyString
    description: _NonEmptyString
    kind: Literal["archetype", "capability", "platform"]
    version: str
    content_root: RelativeResourcePath
    options_schema: RelativeResourcePath | None = None
    compatibility: ComponentCompatibility
    requires: tuple[ComponentReference, ...] = ()
    conflicts: tuple[ComponentReference, ...] = ()
    extension_points: tuple[ExtensionPoint, ...] = ()
    contributions: tuple[Contribution, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _validate_protocol_specific_contribution_shape(cls, value: object) -> object:
        """Reject a contribution's shape mismatched to its own protocol.

        Runs on the raw payload, before ``Contribution``'s own before-
        validator rewrites a legacy ``component`` key into ``target`` --
        otherwise that rewrite would erase the distinction this check exists
        to enforce. A protocol-1 manifest must use the legacy flat key
        (extending it with a ``target`` table -- and therefore a Foundation
        target -- is protocol-2-only); a protocol-2 manifest must use the
        discriminated table so its intent is never ambiguous.
        """
        if not isinstance(value, dict):
            return value
        manifest_version = value.get("manifest_version")
        contributions = value.get("contributions")
        if not isinstance(contributions, (list, tuple)):
            return value
        for entry in contributions:
            if not isinstance(entry, dict):
                continue
            if manifest_version == 1 and "target" in entry:
                msg = (
                    "manifest protocol 1 contributions must use 'component', "
                    "not 'target'"
                )
                raise ValueError(msg)
            if manifest_version == 2 and "component" in entry:
                msg = (
                    "manifest protocol 2 contributions must use 'target', "
                    "not 'component'"
                )
                raise ValueError(msg)
        return value

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
        return relative_resource_path(value)

    @field_validator(
        "requires", "conflicts", "extension_points", "contributions", mode="before"
    )
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

    @field_validator("contributions")
    @classmethod
    def _canonicalise_contributions(
        cls, value: tuple[Contribution, ...]
    ) -> tuple[Contribution, ...]:
        targets = [
            (_contribution_target_key(contribution), contribution.extension_point)
            for contribution in value
        ]
        if len(targets) != len(set(targets)):
            msg = "contributions must not target the same extension point twice"
            raise ValueError(msg)
        return tuple(
            sorted(
                value,
                key=lambda contribution: (
                    _contribution_target_key(contribution),
                    contribution.extension_point,
                ),
            )
        )

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

    @model_validator(mode="after")
    def _validate_extension_relationships(self) -> Self:
        content_root = PurePosixPath(self.content_root)

        for point in self.extension_points:
            if not PurePosixPath(point.content).is_relative_to(content_root):
                msg = (
                    f"extension point {point.id!r} content {point.content!r} must "
                    f"fall inside content_root {self.content_root!r}"
                )
                raise ValueError(msg)

        for contribution in self.contributions:
            target = contribution.target
            if isinstance(target, ComponentTarget) and target.id == self.id:
                msg = "a component must not contribute to its own extension point"
                raise ValueError(msg)
            if PurePosixPath(contribution.content).is_relative_to(content_root):
                msg = (
                    f"contribution content {contribution.content!r} must fall "
                    f"outside content_root {self.content_root!r}"
                )
                raise ValueError(msg)
        return self


def component_resource_path(manifest_path: Path, relative_path: str) -> Path:
    """Resolve one component- or Foundation-relative resource path.

    Shared by every owned-resource check in this module, by
    ``forge_template.foundation_source`` (a source that is not itself a
    component but resolves resources the identical way), and by
    ``forge_template.template_variables`` to resolve ``options_schema``
    through the same symlink-escape-checked containment rule, rather than
    duplicating it.
    """
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

    content_root = component_resource_path(resolved_manifest, manifest.content_root)
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
        options_schema = component_resource_path(
            resolved_manifest, manifest.options_schema
        )
        if not options_schema.is_file():
            msg = f"options_schema is not a file: {manifest.options_schema!r}"
            raise ValueError(msg)

    for point in manifest.extension_points:
        point_content = component_resource_path(resolved_manifest, point.content)
        if not point_content.is_file():
            msg = (
                f"extension point {point.id!r} content is not a file: {point.content!r}"
            )
            raise ValueError(msg)

    for contribution in manifest.contributions:
        contribution_content = component_resource_path(
            resolved_manifest, contribution.content
        )
        if not contribution_content.is_file():
            msg = f"contribution content is not a file: {contribution.content!r}"
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


def _reject_unknown_extension_points(
    manifests: Iterable[ComponentManifest],
    by_id: dict[str, ComponentManifest],
    foundation: FoundationSource | None,
) -> None:
    """Reject a contribution naming a target or point that does not exist.

    This runs catalogue-wide, independent of any ProjectSpec selection, so a
    contribution with a typo'd owner or extension point fails at packaging and
    review time. It is what makes it safe for
    ``forge_template.file_conflicts.resolve_output_plan`` to silently skip a
    component-targeted contribution whose owner happens not to be selected:
    that path is only ever reached once every contribution is already proven
    to name a real, published extension point.

    A Foundation-targeted contribution is checked against ``foundation`` when
    supplied. When it is not -- callers that validate a catalogue without
    knowing the installed Foundation source, such as
    ``forge_template.composition``'s internal re-validation -- that specific
    check is deferred rather than assumed to fail; the caller that actually
    has the Foundation source (``forge_template.engine``) performs the
    authoritative check.
    """
    for manifest in manifests:
        for contribution in manifest.contributions:
            target = contribution.target
            if isinstance(target, FoundationTarget):
                if foundation is None:
                    continue
                published = {point.id for point in foundation.extension_points}
                if contribution.extension_point not in published:
                    msg = (
                        f"component {manifest.id!r} contributes to undeclared "
                        f"extension point {contribution.extension_point!r} on "
                        "the Foundation content source"
                    )
                    raise ValueError(msg)
                continue

            owner = by_id.get(target.id)
            if owner is None:
                msg = (
                    f"component {manifest.id!r} contributes to missing component "
                    f"{target.id!r}"
                )
                raise ValueError(msg)
            published = {point.id for point in owner.extension_points}
            if contribution.extension_point not in published:
                msg = (
                    f"component {manifest.id!r} contributes to undeclared "
                    f"extension point {contribution.extension_point!r} on "
                    f"{target.id!r}"
                )
                raise ValueError(msg)


def validate_manifest_set(
    manifests: Iterable[ComponentManifest],
    foundation: FoundationSource | None = None,
) -> tuple[ComponentManifest, ...]:
    """Validate cross-manifest identity and reference integrity.

    ``foundation``, when supplied, lets a Foundation-targeted contribution be
    checked against its real published extension points; see
    ``_reject_unknown_extension_points``. The lexical return order supports
    deterministic catalogue inspection only; it is explicitly not composition
    order.
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
    _reject_unknown_extension_points(manifest_tuple, by_id, foundation)

    return tuple(sorted(manifest_tuple, key=lambda manifest: manifest.id))


def validate_manifest_selection(
    spec: ProjectSpec,
    manifests: Iterable[ComponentManifest],
    foundation: FoundationSource | None = None,
) -> tuple[ComponentManifest, ...]:
    """Validate an effective ProjectSpec against provisional manifest metadata."""
    catalogue = validate_manifest_set(manifests, foundation)
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
