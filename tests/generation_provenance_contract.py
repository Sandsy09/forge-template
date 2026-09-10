"""Doc-derived reference constants for docs/generation-provenance.md.

Since FT-17.01 shipped the real generation-metadata model, serialisation, and
parse/verify surface (``forge_template.GenerationMetadata``,
``parse_generation_metadata``, ``verify_generation_metadata``, and the two
``EngineErrorCode`` values), this module no longer carries a shadow
implementation. What remains is only what a test must *not* read out of the
engine: the field set and classification vocabulary the living document
publishes, and the ``_skip_if_exists`` set ``copier.yml`` still owns.

``RenameRecord`` and ``classify_update`` stay as a placeholder for the update
classifier FT-17.04 ships; ``tests/test_generation_provenance.py`` exercises
them against the documented vocabulary until then.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from forge_template import ProjectSpec

#: The persisted document's top-level fields, in documented order;
#: ``reproduction`` is optional.
REQUIRED_FIELDS = (
    "metadata_version",
    "provider",
    "protocols",
    "spec",
    "components",
    "output",
)
OPTIONAL_FIELDS = ("reproduction",)

#: The documented update classification vocabulary.
CLASSIFICATIONS = ("unchanged", "added", "removed", "changed", "renamed")

#: ``copier.yml``'s ``_skip_if_exists``, the set a protocol-3
#: ``[[regeneration]]`` record marks ``skip-if-exists`` once a component owns
#: one of these targets. No shipped component declares one yet (FT-17.03).
SKIP_IF_EXISTS = frozenset({"CHANGELOG.md", ".env"})


@dataclass(frozen=True)
class RenameRecord:
    """One owner-declared ``{ from, to, since }`` migration pair."""

    source: str
    target: str
    since: str


def digest(content: bytes) -> str:
    """The ``sha256:<hex>`` form the ``output`` entries record."""
    return "sha256:" + hashlib.sha256(content).hexdigest()


def selected_ids(spec: ProjectSpec) -> tuple[str, ...]:
    """Every selected component id: archetype, then capabilities, platforms."""
    return (
        spec.components.archetype,
        *spec.components.capabilities,
        *spec.components.platforms,
    )


def classify_update(
    old: Mapping[str, bytes],
    new: Mapping[str, bytes],
    renames: Sequence[RenameRecord] = (),
) -> dict[str, str]:
    """Classify each target across an old/new render pair.

    Every value is one of :data:`CLASSIFICATIONS`. Renames are applied first,
    so a moved-and-edited file is reported once, as ``renamed``.
    """
    moved = {record.source: record.target for record in renames}
    result: dict[str, str] = {}
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
