"""Derives every ProjectSpec selection the installed catalogue accepts.

FT-17.05 / ADR 0066. Three prior enumerations of "every valid composition"
(``tests/test_composition_architecture_review.py``,
``tests/test_cross_repository_validation.py``,
``tests/test_capability_composition.py``) are each a hand-written literal that
stopped growing once written -- all three still mean the pre-Stage-17 ten.
This module derives the set instead, from nothing but the path-free
:func:`forge_template.discover_components` descriptors' own ``requires`` /
``conflicts`` edges, so it grows itself the next time a component is added.

The derivation applies exactly the rule
``forge_template.component_manifest.validate_manifest_selection`` enforces --
every ``requires`` id present in the selection, no ``conflicts`` id present in
the selection, no chaining, no version negotiation beyond a compatible
``ProjectSpec`` -- and needs no component resource to compute it: reading only
``ComponentDescriptor.requires`` / ``.conflicts`` (already published,
path-free) is itself a demonstration of the no-resource-read rule
(FT-ROADMAP-01-AC-04) the sweep separately proves. Every composition this
module returns is additionally proved valid downstream by actually calling
``plan_generation`` / ``render_project`` against it
(``tests/test_composition_sweep.py``): a derivation bug here would surface as
a real engine rejection, not a silent miscount.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING

from forge_template import discover_components

if TYPE_CHECKING:
    from collections.abc import Sequence

    from forge_template import ComponentDescriptor

#: The count this module currently derives. A tripwire, not a target: it
#: changes only when the catalogue itself changes, and any such change is a
#: real one worth noticing in review, not a value to update reflexively.
EXPECTED_COMPOSITION_COUNT = 2240


@dataclass(frozen=True, order=True)
class Composition:
    """One selection ``discover_components()`` accepts -- lexically sortable
    the same way ``forge_template.composition.composition_order`` orders a
    plan's component tiers."""

    archetype: str
    capabilities: tuple[str, ...]
    platforms: tuple[str, ...]

    @property
    def slug(self) -> str:
        """A pytest-node-id-safe label, e.g.
        ``library+github+coverage+jupyter``. Deliberately bracket-free --
        square brackets read as a parametrize boundary in a `-k` expression."""
        parts = (self.archetype, *self.platforms, *self.capabilities)
        return "+".join(parts)


def _accepts(
    component_id: str, selected: set[str], by_id: dict[str, ComponentDescriptor]
) -> bool:
    """Mirror ``validate_manifest_selection``'s requires/conflicts check."""
    descriptor = by_id[component_id]
    if not all(reference.id in selected for reference in descriptor.requires):
        return False
    return not any(reference.id in selected for reference in descriptor.conflicts)


def valid_compositions(
    catalogue: Sequence[ComponentDescriptor] | None = None,
) -> tuple[Composition, ...]:
    """Every selection the given (or installed) catalogue accepts.

    One archetype, any subset of capabilities, any subset of platforms --
    filtered to selections where every selected component's ``requires`` is
    satisfied and no selected component's ``conflicts`` fires. Ordered
    deterministically (archetype, then capabilities, then platforms, all
    lexical) so a sweep over the result is itself reproducible.
    """
    descriptors = tuple(catalogue) if catalogue is not None else discover_components()
    by_id = {descriptor.id: descriptor for descriptor in descriptors}
    archetypes = sorted(d.id for d in descriptors if d.kind == "archetype")
    capabilities = sorted(d.id for d in descriptors if d.kind == "capability")
    platforms = sorted(d.id for d in descriptors if d.kind == "platform")

    compositions: list[Composition] = []
    for archetype in archetypes:
        for platform_count in range(len(platforms) + 1):
            for platform_subset in combinations(platforms, platform_count):
                for capability_count in range(len(capabilities) + 1):
                    for capability_subset in combinations(
                        capabilities, capability_count
                    ):
                        selected = {archetype, *capability_subset, *platform_subset}
                        if all(
                            _accepts(component_id, selected, by_id)
                            for component_id in selected
                        ):
                            compositions.append(
                                Composition(
                                    archetype=archetype,
                                    capabilities=capability_subset,
                                    platforms=platform_subset,
                                )
                            )
    return tuple(sorted(compositions))
