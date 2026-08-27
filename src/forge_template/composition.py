"""Deterministic composition order for a validated ProjectSpec selection.

This module defines exactly one application order over an effective
ProjectSpec's selected components. It partitions a valid selection into the
Foundation-then-archetype-then-capability-then-platform tiers, orders each
tier by a lexicographically smallest topological sort over that tier's own
``requires`` edges, and orders each selected component's owned content by
ascending POSIX-relative path. It deliberately does not discover components,
decide output paths or targets, perform file operations, resolve collisions
between components, or expose a stable engine error surface; those remain
later Stage 06 work (FT-06.04 and FT-06.07). See docs/composition-order.md.

Order alone confers no rendering or overwrite authority. A component placed
later in this order never gains implicit permission to replace an earlier
component's content; that boundary is normative, not incidental.
"""

from __future__ import annotations

import graphlib
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from forge_template.component_manifest import (
    ComponentManifest,
    load_component_manifest,
    validate_manifest_selection,
)
from forge_template.project_spec import ProjectSpec

COMPOSITION_TIER_ORDER: tuple[str, ...] = ("archetype", "capability", "platform")
"""Kind application order. Foundation is the implicit baseline and is not a
component, so it precedes every tier without appearing in this sequence."""


class _CompositionModel(BaseModel):
    """Shared strict and immutable behaviour for composition objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ComponentPlacement(_CompositionModel):
    """One selected component's manifest and ordered owned content."""

    manifest: ComponentManifest
    content_paths: tuple[str, ...]


def _lexical_topological_order(graph: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Return graph's nodes in lexicographically smallest topological order.

    Picks the lexicographically smallest ready node one at a time, so the
    result is a single deterministic total order rather than merely one
    valid topological order among several. Callers must have already
    rejected cycles: ``composition_order`` guarantees this by calling
    ``validate_manifest_selection`` first, which validates the complete
    supplied catalogue and therefore every same-tier subgraph of it too.
    """
    sorter: graphlib.TopologicalSorter[str] = graphlib.TopologicalSorter(graph)
    sorter.prepare()

    order: list[str] = []
    ready: set[str] = set(sorter.get_ready())
    while ready:
        identifier = min(ready)
        ready.remove(identifier)
        order.append(identifier)
        sorter.done(identifier)
        ready.update(sorter.get_ready())
    return tuple(order)


def _order_tier(
    tier_manifests: list[ComponentManifest],
) -> tuple[ComponentManifest, ...]:
    """Order one kind tier.

    Only edges between components already in this tier influence order; a
    ``requires`` reference targeting another tier is a selection constraint
    enforced elsewhere and never reorders tiers.
    """
    by_id = {manifest.id: manifest for manifest in tier_manifests}
    graph = {
        manifest.id: tuple(
            reference.id for reference in manifest.requires if reference.id in by_id
        )
        for manifest in tier_manifests
    }
    return tuple(by_id[identifier] for identifier in _lexical_topological_order(graph))


def composition_order(
    spec: ProjectSpec,
    manifests: Iterable[ComponentManifest],
) -> tuple[ComponentManifest, ...]:
    """Return spec's selected components in deterministic application order.

    Selection validity — identity, kind, compatibility, hard dependencies,
    conflicts, and dependency-graph acyclicity — is delegated entirely to
    ``forge_template.component_manifest.validate_manifest_selection``; this
    function only decides the order in which an already-valid, already-
    acyclic selection applies.
    """
    selected = validate_manifest_selection(spec, manifests)
    by_tier: dict[str, list[ComponentManifest]] = {
        tier: [] for tier in COMPOSITION_TIER_ORDER
    }
    for manifest in selected:
        by_tier[manifest.kind].append(manifest)

    ordered: list[ComponentManifest] = []
    for tier in COMPOSITION_TIER_ORDER:
        ordered.extend(_order_tier(by_tier[tier]))
    return tuple(ordered)


def component_content_order(manifest_path: str | Path) -> tuple[str, ...]:
    """Return one component's owned content in ascending POSIX-path order.

    Calling ``load_component_manifest`` first reuses its existence and
    containment validation; this function replaces ``rglob``'s
    filesystem-dependent enumeration order with a stable, explicit one.
    """
    resolved_manifest_path = Path(manifest_path)
    manifest = load_component_manifest(resolved_manifest_path)
    content_root = (
        resolved_manifest_path.resolve(strict=True).parent / manifest.content_root
    ).resolve(strict=True)

    relative_paths = (
        resource.relative_to(content_root).as_posix()
        for resource in content_root.rglob("*")
        if resource.is_file()
    )
    return tuple(sorted(relative_paths))


def composition_plan(
    spec: ProjectSpec,
    manifest_paths: Iterable[str | Path],
) -> tuple[ComponentPlacement, ...]:
    """Return the deterministic per-component application plan for spec.

    Callers supply explicit ``component.toml`` paths; this function does not
    discover components itself (FT-06.07 remains the owner of discovery).
    """
    paths = [Path(path) for path in manifest_paths]
    manifests = tuple(load_component_manifest(path) for path in paths)
    paths_by_id = {
        manifest.id: path for manifest, path in zip(manifests, paths, strict=True)
    }

    ordered = composition_order(spec, manifests)
    return tuple(
        ComponentPlacement(
            manifest=manifest,
            content_paths=component_content_order(paths_by_id[manifest.id]),
        )
        for manifest in ordered
    )
