"""Doc-derived reference constants for docs/generation-provenance.md.

Since FT-17.01 shipped the real generation-metadata model, serialisation, and
parse/verify surface (``forge_template.GenerationMetadata``,
``parse_generation_metadata``, ``verify_generation_metadata``, and the two
``EngineErrorCode`` values), and FT-17.04 / ADR 0065 shipped the real
reproducible-render and update-classification surface (``plan_update``,
``UpdatePlan``, ``UpdateTarget``, ``AppliedRename``), this module no longer
carries a shadow implementation. What remains is only what a test must *not*
read out of the engine: the field set and classification vocabulary the
living document publishes, and the ``_skip_if_exists`` set ``copier.yml``
still owns. The former placeholder ``RenameRecord`` dataclass and
``classify_update`` reference implementation (ADR 0062 decision 8) are
retired -- ``tests/test_generation_provenance.py`` now drives
``forge_template.plan_update`` directly.
"""

from __future__ import annotations

import hashlib

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
