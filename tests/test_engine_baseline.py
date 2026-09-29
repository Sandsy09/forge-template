"""Fast-suite deterministic-output baseline -- FT-25.01 / ADR 0079.

The exhaustive per-composition fingerprints run under the ``sweep`` marker
(``tests/test_composition_sweep.py``). This module keeps ``poe check`` itself
sensitive to an output change: discovery order, one recorded fingerprint per
archetype, and the update classifications ``plan_update`` reports for a
representative transition set per archetype
(``tests/fixtures/update_classifications.json``; regenerate deliberately with
``--update-goldens`` and review the diff).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from forge_template import (
    discover_components,
    parse_project_spec,
    plan_update,
    render_project,
)
from tests.composition_fingerprints import (
    composition_fingerprint,
    load_fingerprints,
    sweep_payload,
)
from tests.composition_matrix import Composition, valid_compositions

if TYPE_CHECKING:
    from forge_template import RenderedProject

UPDATE_CLASSIFICATIONS = (
    Path(__file__).parent / "fixtures" / "update_classifications.json"
)

_ARCHETYPES = tuple(
    sorted(
        descriptor.id
        for descriptor in discover_components()
        if descriptor.kind == "archetype"
    )
)


def _smallest(archetype: str) -> Composition:
    """The accepted composition with the fewest components for an archetype
    (``data-science`` requires ``jupyter``; the rest stand alone)."""
    return min(
        (
            composition
            for composition in valid_compositions()
            if composition.archetype == archetype and not composition.platforms
        ),
        key=lambda composition: (len(composition.capabilities), composition),
    )


def _with(
    composition: Composition,
    *,
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
) -> Composition:
    return Composition(
        archetype=composition.archetype,
        capabilities=tuple(sorted({*composition.capabilities, *capabilities})),
        platforms=tuple(sorted({*composition.platforms, *platforms})),
    )


def test_discovery_order_is_lexical_and_repeatable() -> None:
    first = tuple(descriptor.id for descriptor in discover_components())
    again = tuple(descriptor.id for descriptor in discover_components())
    assert first == again == tuple(sorted(first))


@pytest.mark.parametrize("archetype", _ARCHETYPES)
def test_the_smallest_composition_matches_its_recorded_fingerprint(
    archetype: str,
) -> None:
    composition = _smallest(archetype)
    assert composition_fingerprint(composition) == load_fingerprints()[composition.slug]


def _transitions(archetype: str) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    base = _smallest(archetype)
    with_changelog = _with(base, capabilities=("changelog",))
    with_github = _with(base, platforms=("github",))

    renamed_organisation = sweep_payload(with_github)
    options = deepcopy(renamed_organisation["component_options"])
    assert isinstance(options, dict)
    options["github"] = {"organisation": "renamed-org"}
    renamed_organisation["component_options"] = options

    return {
        "no-op": (sweep_payload(base), sweep_payload(base)),
        "add-capability": (sweep_payload(base), sweep_payload(with_changelog)),
        "remove-capability": (sweep_payload(with_changelog), sweep_payload(base)),
        "add-platform": (sweep_payload(base), sweep_payload(with_github)),
        "change-option": (sweep_payload(with_github), renamed_organisation),
    }


_RENDERS: dict[str, RenderedProject] = {}


def _render(payload: dict[str, Any]) -> RenderedProject:
    """Render once per distinct payload; transitions share their endpoints."""
    key = json.dumps(payload, sort_keys=True)
    if key not in _RENDERS:
        _RENDERS[key] = render_project(parse_project_spec(payload))
    return _RENDERS[key]


def _classify(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    old = _render(before)
    new = _render(after)
    assert old.metadata is not None
    update = plan_update(
        old.metadata.to_json(),
        old={item.target: item.content for item in old.files},
        new=new,
    )
    return {
        "targets": [
            [item.target, item.classification, item.owner, item.regeneration]
            for item in update.targets
        ],
        "renames": [rename.model_dump(mode="json") for rename in update.renames],
        "reproduction": update.reproduction.mode,
    }


def test_update_classifications_match_the_recorded_baseline(
    update_goldens: bool,
) -> None:
    actual = {
        archetype: {
            name: _classify(before, after)
            for name, (before, after) in _transitions(archetype).items()
        }
        for archetype in _ARCHETYPES
    }
    if update_goldens:
        text = json.dumps(actual, indent=2, sort_keys=True) + "\n"
        UPDATE_CLASSIFICATIONS.write_bytes(text.encode("utf-8"))
    recorded = json.loads(UPDATE_CLASSIFICATIONS.read_text(encoding="utf-8"))
    assert actual == recorded
