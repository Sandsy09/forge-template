"""Output targets, dispositions, and collision safety for composed output.

This low-level module decides, for a deterministic
:func:`forge_template.composition.composition_plan` plus the implicit
Foundation content source, what project-relative target each owned content
path produces and what happens when more than one owner's content maps to
the same target. It performs no file operations and renders or splices no
file *content*; the supported facade in ``forge_template.engine`` composes it
with those responsibilities and structured errors. See docs/file-conflicts.md.

Composition order decides *when* a component applies; this module decides
*what happens* when two owners' output collides. Being later in composition
order is never implicit permission to replace an earlier owner's target --
that boundary, stated by ``forge_template.composition``, is enforced here
rather than merely repeated. Foundation always applies first and is supplied
as its own argument rather than a placement: it is not a component and must
never appear in ``GenerationPlan.component_order``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal

from jinja2 import Environment, StrictUndefined, TemplateError
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from forge_template.component_manifest import (
    FoundationTarget,
    relative_resource_path,
)
from forge_template.composition import ComponentPlacement

if TYPE_CHECKING:
    from forge_template.foundation_source import FoundationPlacement

TEMPLATE_SUFFIX = ".jinja"
"""Suffix stripped from a content path to produce a rendered output target."""

FILE_DISPOSITIONS: tuple[str, ...] = ("create", "extend", "merge", "override")
"""Every disposition protocol v1 classifies. Not every one is grantable; see
``GRANTED_DISPOSITIONS``."""

GRANTED_DISPOSITIONS: tuple[str, ...] = ("create", "extend")
"""Dispositions protocol v1 actually grants a component. ``merge`` and
``override`` are classified concepts, reserved for a documented extension
point and future organisation policy rather than expressible today; a
collision that would need either fails clearly instead."""

_PATH_JINJA_ENVIRONMENT = Environment(undefined=StrictUndefined)
"""Renders content *paths* only -- never file content, which the supported
facade in ``forge_template.engine`` renders with its own environment. Kept
separate so this module's Jinja usage stays limited to what output-target
derivation needs; it performs no autoescaping decision because a path is
never HTML."""


class _ConflictModel(BaseModel):
    """Shared strict and immutable behaviour for file-conflict objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ComponentOwner(_ConflictModel):
    """One selected component, identified as an output target's owner."""

    kind: Literal["component"] = "component"
    id: str


class FoundationOwner(_ConflictModel):
    """The implicit Foundation content source, identified as an owner."""

    kind: Literal["foundation"] = "foundation"


Owner = ComponentOwner | FoundationOwner
"""Every kind of output-target owner. Discriminated on ``kind`` so a strict
consumer -- ``forge_template.engine.PlannedFile.owner`` included -- never has
to guess which fields are present."""


class OutputContribution(_ConflictModel):
    """One owner's contribution to a single output target."""

    owner: Owner = Field(discriminator="kind")
    disposition: Literal["create", "extend"]
    source_path: str
    extension_point: str | None = None


class OutputFile(_ConflictModel):
    """One output target's sole creator and its ordered extensions."""

    target: str
    base: OutputContribution
    extensions: tuple[OutputContribution, ...] = ()


def output_target(content_path: str) -> str:
    """Return the project-relative output target for one owned content path.

    A trailing ``.jinja`` suffix means the file renders before it lands at
    the stripped path; every other path copies literally at its own path.
    The path itself may already have been rendered by ``render_output_path``;
    this function only ever strips the suffix.
    """
    if content_path.endswith(TEMPLATE_SUFFIX):
        return content_path[: -len(TEMPLATE_SUFFIX)]
    return content_path


def render_output_path(content_path: str, context: Mapping[str, JsonValue]) -> str:
    """Render one owned content path through the template-variable context.

    Runs before the ``.jinja`` suffix is stripped, so a content path may
    itself use template variables
    (``content/src/{{ project.package_name }}/py.typed``) -- required by the
    Library archetype's ``src/<package_name>/`` layout, which no
    content-path-only syntax could otherwise express. Uses the same
    ``StrictUndefined`` strictness as file-content rendering: a path
    referencing an undefined variable fails here rather than rendering as an
    empty segment. The rendered result is then validated as a normalised
    relative POSIX path through
    ``forge_template.component_manifest.relative_resource_path`` -- it must
    not become absolute, escape via ``..``, or produce an empty segment -- so
    a path variable can never redirect output outside the project tree.
    """
    try:
        rendered = _PATH_JINJA_ENVIRONMENT.from_string(content_path).render(**context)
    except TemplateError as exc:
        msg = f"content path {content_path!r} failed to render: {exc}"
        raise ValueError(msg) from exc
    return relative_resource_path(rendered)


def _owned_targets(
    content_paths: Iterable[str],
    context: Mapping[str, JsonValue],
    *,
    owner_label: str,
) -> dict[str, str]:
    """Return one owner's content paths mapped to rendered output targets.

    Raises when two of one owner's own files map to the same target -- an
    authoring error inside that owner, independent of any other owner's
    selection or presence.
    """
    targets: dict[str, str] = {}
    source_by_target: dict[str, str] = {}
    for content_path in content_paths:
        target = output_target(render_output_path(content_path, context))
        if target in source_by_target:
            msg = (
                f"{owner_label} maps both {source_by_target[target]!r} and "
                f"{content_path!r} to the same target {target!r}"
            )
            raise ValueError(msg)
        source_by_target[target] = content_path
        targets[content_path] = target
    return targets


def component_targets(
    placement: ComponentPlacement, context: Mapping[str, JsonValue]
) -> dict[str, str]:
    """Return one component's owned content paths mapped to output targets."""
    return _owned_targets(
        placement.content_paths,
        context,
        owner_label=f"component {placement.manifest.id!r}",
    )


def resolve_output_plan(
    placements: Iterable[ComponentPlacement],
    context: Mapping[str, JsonValue] | None = None,
    *,
    foundation: FoundationPlacement | None = None,
) -> tuple[OutputFile, ...]:
    """Return the deterministic output plan for a composition plan.

    Foundation's owned content becomes every target's `create`d base first --
    it always applies before any selected component. Every selected
    component's own owned content then becomes a `create`d base too. A
    component's declared ``contributions`` attach as ``extend`` entries onto
    the target their published extension point lives in -- whether that point
    is published by another selected component or by Foundation -- dropped
    silently only when a *component*-targeted owner is absent from
    ``placements``: catalogue-wide validation
    (``component_manifest.validate_manifest_set``) already proves every
    contribution names a real, published extension point, so an absent
    component owner only ever means the owner was not selected, never a
    typo. A Foundation-targeted contribution has no such "not selected" case
    -- Foundation is mandatory whenever it is supplied here at all -- so a
    missing ``foundation`` argument is a hard error instead.

    Extensions attach in the order components appear in ``placements`` --
    composition order -- which is what decides the order among multiple
    contributors to one point. It never decides whether a target's base
    exists: a target's own owner always supplies it, regardless of which
    tier the contributing component belongs to. Two owners both creating the
    same target is an unsupported collision and raises, naming both owners
    and the shared target.
    """
    context = context or {}
    placement_tuple = tuple(placements)
    manifests_by_id = {
        placement.manifest.id: placement.manifest for placement in placement_tuple
    }

    bases: dict[str, OutputContribution] = {}
    extensions: dict[str, list[OutputContribution]] = {}

    def _claim(target: str, contribution: OutputContribution, owner_label: str) -> None:
        if target in bases:
            existing = bases[target].owner
            existing_label = (
                "the Foundation content source"
                if isinstance(existing, FoundationOwner)
                else f"component {existing.id!r}"
            )
            msg = f"{existing_label} and {owner_label} both create target {target!r}"
            raise ValueError(msg)
        bases[target] = contribution
        extensions[target] = []

    if foundation is not None:
        for content_path, target in _owned_targets(
            foundation.content_paths,
            context,
            owner_label="the Foundation content source",
        ).items():
            _claim(
                target,
                OutputContribution(
                    owner=FoundationOwner(),
                    disposition="create",
                    source_path=content_path,
                ),
                "the Foundation content source",
            )

    for placement in placement_tuple:
        for content_path, target in component_targets(placement, context).items():
            _claim(
                target,
                OutputContribution(
                    owner=ComponentOwner(id=placement.manifest.id),
                    disposition="create",
                    source_path=content_path,
                ),
                f"component {placement.manifest.id!r}",
            )

    for placement in placement_tuple:
        for contribution in placement.manifest.contributions:
            if isinstance(contribution.target, FoundationTarget):
                if foundation is None:
                    msg = (
                        f"component {placement.manifest.id!r} contributes to "
                        "the Foundation content source, but none is available"
                    )
                    raise ValueError(msg)
                published_points = foundation.source.extension_points
                owner_content_root = foundation.source.content_root
                missing_owner_message = None  # Foundation is never "not selected".
            else:
                owner_manifest = manifests_by_id.get(contribution.target.id)
                if owner_manifest is None:
                    continue  # Owner not selected: the contribution does not apply.
                published_points = owner_manifest.extension_points
                owner_content_root = owner_manifest.content_root
                missing_owner_message = contribution.target.id

            point = next(
                (p for p in published_points if p.id == contribution.extension_point),
                None,
            )
            if point is None:
                owner_description = (
                    "the Foundation content source"
                    if missing_owner_message is None
                    else repr(missing_owner_message)
                )
                msg = (
                    f"component {placement.manifest.id!r} contributes to "
                    f"undeclared extension point "
                    f"{contribution.extension_point!r} on {owner_description}"
                )
                raise ValueError(msg)

            # ``point.content`` is owner-root-relative (matching
            # ``options_schema``'s convention), while every key in
            # ``extensions``/``bases`` is content-root-relative (matching
            # ``ComponentPlacement.content_paths``); rebase before matching.
            point_content_relative = PurePosixPath(point.content).relative_to(
                PurePosixPath(owner_content_root)
            )
            target = output_target(
                render_output_path(point_content_relative.as_posix(), context)
            )
            target_extensions = extensions.get(target)
            if target_extensions is None:
                owner_description = (
                    "the Foundation content source"
                    if missing_owner_message is None
                    else repr(missing_owner_message)
                )
                msg = (
                    f"{owner_description} publishes extension point "
                    f"{contribution.extension_point!r} but its placement does "
                    f"not include {point.content!r}"
                )
                raise ValueError(msg)
            target_extensions.append(
                OutputContribution(
                    owner=ComponentOwner(id=placement.manifest.id),
                    disposition="extend",
                    source_path=contribution.content,
                    extension_point=contribution.extension_point,
                )
            )

    return tuple(
        OutputFile(
            target=target, base=bases[target], extensions=tuple(extensions[target])
        )
        for target in sorted(bases)
    )
