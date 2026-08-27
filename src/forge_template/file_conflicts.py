"""Output targets, dispositions, and collision safety for composed output.

This module decides, for a deterministic
:func:`forge_template.composition.composition_plan`, what project-relative
target each owned content path produces and what happens when more than one
component's content maps to the same target. It performs no file operations,
renders and splices no content, and exposes no stable engine error surface;
those remain later Stage 06 and FT-06.07 work. See docs/file-conflicts.md.

Composition order decides *when* a component applies; this module decides
*what happens* when two components' output collides. Being later in
composition order is never implicit permission to replace an earlier
component's target — that boundary, stated by
``forge_template.composition``, is enforced here rather than merely repeated.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict

from forge_template.composition import ComponentPlacement

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


class _ConflictModel(BaseModel):
    """Shared strict and immutable behaviour for file-conflict objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class OutputContribution(_ConflictModel):
    """One component's contribution to a single output target."""

    component_id: str
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
    """
    if content_path.endswith(TEMPLATE_SUFFIX):
        return content_path[: -len(TEMPLATE_SUFFIX)]
    return content_path


def component_targets(placement: ComponentPlacement) -> dict[str, str]:
    """Return one component's owned content paths mapped to output targets.

    Raises when two of the component's own files map to the same target —
    an authoring error inside one component, independent of any other
    component's selection.
    """
    targets: dict[str, str] = {}
    source_by_target: dict[str, str] = {}
    for content_path in placement.content_paths:
        target = output_target(content_path)
        if target in source_by_target:
            msg = (
                f"component {placement.manifest.id!r} maps both "
                f"{source_by_target[target]!r} and {content_path!r} to the "
                f"same target {target!r}"
            )
            raise ValueError(msg)
        source_by_target[target] = content_path
        targets[content_path] = target
    return targets


def resolve_output_plan(
    placements: Iterable[ComponentPlacement],
) -> tuple[OutputFile, ...]:
    """Return the deterministic output plan for a composition plan.

    Every selected component's owned content becomes a ``create``d target.
    A component's declared ``contributions`` then attach as ``extend``
    entries onto the target their published extension point lives in,
    dropped silently when their named owner is absent from ``placements`` —
    catalogue-wide validation
    (``component_manifest.validate_manifest_set``) already proves every
    contribution names a real, published extension point, so an absent
    owner only ever means the owner was not selected, never a typo.

    Extensions attach in the order components appear in ``placements`` —
    composition order — which is what decides the order among multiple
    contributors to one point. It never decides whether a target's base
    exists: a target's own owner always supplies it, regardless of which
    tier the contributing component belongs to. Two components both
    creating the same target is an unsupported collision and raises,
    naming both components and the shared target.
    """
    placement_tuple = tuple(placements)
    manifests_by_id = {
        placement.manifest.id: placement.manifest for placement in placement_tuple
    }

    creator_by_target: dict[str, str] = {}
    bases: dict[str, OutputContribution] = {}
    extensions: dict[str, list[OutputContribution]] = {}

    for placement in placement_tuple:
        for content_path, target in component_targets(placement).items():
            if target in creator_by_target:
                msg = (
                    f"components {creator_by_target[target]!r} and "
                    f"{placement.manifest.id!r} both create target {target!r}"
                )
                raise ValueError(msg)
            creator_by_target[target] = placement.manifest.id
            bases[target] = OutputContribution(
                component_id=placement.manifest.id,
                disposition="create",
                source_path=content_path,
            )
            extensions[target] = []

    for placement in placement_tuple:
        for contribution in placement.manifest.contributions:
            owner = manifests_by_id.get(contribution.component)
            if owner is None:
                continue  # Owner not selected: the contribution does not apply.

            point = next(
                (
                    point
                    for point in owner.extension_points
                    if point.id == contribution.extension_point
                ),
                None,
            )
            if point is None:
                msg = (
                    f"component {placement.manifest.id!r} contributes to "
                    f"undeclared extension point "
                    f"{contribution.extension_point!r} on "
                    f"{contribution.component!r}"
                )
                raise ValueError(msg)

            # ``point.content`` is component-root-relative (matching
            # ``options_schema``'s convention), while every key in
            # ``extensions``/``bases`` is content-root-relative (matching
            # ``ComponentPlacement.content_paths``); rebase before matching.
            point_content_relative = PurePosixPath(point.content).relative_to(
                PurePosixPath(owner.content_root)
            )
            target = output_target(point_content_relative.as_posix())
            target_extensions = extensions.get(target)
            if target_extensions is None:
                msg = (
                    f"component {contribution.component!r} publishes "
                    f"extension point {contribution.extension_point!r} but "
                    f"its placement does not include {point.content!r}"
                )
                raise ValueError(msg)
            target_extensions.append(
                OutputContribution(
                    component_id=placement.manifest.id,
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
