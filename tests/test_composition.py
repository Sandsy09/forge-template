"""Tests for deterministic composition order."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from forge_template.component_manifest import ComponentManifest, load_component_manifest
from forge_template.composition import (
    ComponentPlacement,
    component_content_order,
    composition_order,
    composition_plan,
)
from forge_template.project_spec import ProjectSpec

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"


def _manifest_payload(
    identifier: str,
    *,
    kind: str = "capability",
    requires: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    return {
        "manifest_version": 1,
        "id": identifier,
        "name": identifier.replace("-", " ").title(),
        "description": f"The {identifier} component.",
        "kind": kind,
        "version": "1.0.0",
        "content_root": "content",
        "compatibility": {
            "projectspec_protocols": (1,),
            "requires_python": ">=3.11",
        },
        "requires": requires,
        "conflicts": (),
    }


def _manifest(
    identifier: str,
    *,
    kind: str = "capability",
    requires: tuple[dict[str, object], ...] = (),
) -> ComponentManifest:
    return ComponentManifest.model_validate(
        _manifest_payload(identifier, kind=kind, requires=requires)
    )


def _project_spec(
    *,
    archetype: str = "library",
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
) -> ProjectSpec:
    return ProjectSpec.model_validate(
        {
            "protocol_version": 1,
            "project": {
                "name": "Example",
                "package_name": "example",
                "repository_name": "example",
                "licence": "mit",
            },
            "python": {"minimum": "3.11", "development": "3.13"},
            "components": {
                "archetype": archetype,
                "capabilities": capabilities,
                "platforms": platforms,
            },
        }
    )


def _fixture_manifests(*identifiers: str) -> tuple[ComponentManifest, ...]:
    return tuple(
        load_component_manifest(FIXTURES / identifier / "component.toml")
        for identifier in identifiers
    )


def test_tiers_apply_archetype_then_capability_then_platform() -> None:
    manifests = _fixture_manifests("library", "documentation", "changelog", "github")
    spec = _project_spec(
        capabilities=("documentation", "changelog"), platforms=("github",)
    )

    ordered = composition_order(spec, manifests)

    assert [manifest.id for manifest in ordered] == [
        "library",
        "changelog",
        "documentation",
        "github",
    ]


def test_within_tier_order_follows_dependencies_not_pure_lexical_order() -> None:
    manifests = (
        _manifest("library", kind="archetype"),
        _manifest("a", requires=({"id": "b"},)),
        _manifest("b"),
    )
    spec = _project_spec(capabilities=("a", "b"))

    ordered = composition_order(spec, manifests)

    assert [manifest.id for manifest in ordered] == ["library", "b", "a"]


def test_lexicographically_smallest_ready_node_is_chosen_one_at_a_time() -> None:
    # "a" and "c" are both immediately ready; "b" only becomes ready once "a"
    # is done. A batch-wise (rather than one-at-a-time) topological walk
    # would process the whole initial ready set ["a", "c"] together and
    # yield ["a", "c", "b"] instead of the correct ["a", "b", "c"].
    manifests = (
        _manifest("library", kind="archetype"),
        _manifest("a"),
        _manifest("b", requires=({"id": "a"},)),
        _manifest("c"),
    )
    spec = _project_spec(capabilities=("a", "b", "c"))

    ordered = composition_order(spec, manifests)

    assert [manifest.id for manifest in ordered] == ["library", "a", "b", "c"]


def test_cross_tier_dependency_does_not_reorder_tiers() -> None:
    # "release-notes" hard-requires the "vcs" platform, but a capability must
    # still apply entirely before any platform: tier order always wins over
    # a cross-tier dependency edge.
    manifests = (
        _manifest("app", kind="archetype"),
        _manifest("release-notes", requires=({"id": "vcs"},)),
        _manifest("vcs", kind="platform"),
    )
    spec = _project_spec(
        archetype="app", capabilities=("release-notes",), platforms=("vcs",)
    )

    ordered = composition_order(spec, manifests)

    assert [manifest.id for manifest in ordered] == ["app", "release-notes", "vcs"]


def test_composition_order_is_invariant_to_input_order() -> None:
    manifests = _fixture_manifests("library", "documentation", "changelog", "github")
    spec = _project_spec(
        capabilities=("documentation", "changelog"), platforms=("github",)
    )

    forward = composition_order(spec, manifests)
    reversed_input = composition_order(spec, tuple(reversed(manifests)))

    assert forward == reversed_input


def test_composition_order_rejects_dependency_cycles() -> None:
    manifests = (
        _manifest("library", kind="archetype"),
        _manifest("first", requires=({"id": "second"},)),
        _manifest("second", requires=({"id": "first"},)),
    )
    spec = _project_spec(capabilities=("first", "second"))

    with pytest.raises(ValueError, match="cycle"):
        composition_order(spec, manifests)


def test_component_content_order_is_ascending_posix_path() -> None:
    content_paths = component_content_order(FIXTURES / "changelog" / "component.toml")

    assert content_paths == ("a-top.txt", "nested/a-deep.txt", "z-top.txt")


def test_composition_plan_pairs_each_manifest_with_ordered_content() -> None:
    manifest_paths = [
        FIXTURES / identifier / "component.toml"
        for identifier in ("library", "documentation", "changelog", "github")
    ]
    spec = _project_spec(
        capabilities=("documentation", "changelog"), platforms=("github",)
    )

    plan = composition_plan(spec, manifest_paths)

    assert [placement.manifest.id for placement in plan] == [
        "library",
        "changelog",
        "documentation",
        "github",
    ]
    changelog_placement = next(
        placement for placement in plan if placement.manifest.id == "changelog"
    )
    assert changelog_placement.content_paths == (
        "a-top.txt",
        "nested/a-deep.txt",
        "z-top.txt",
    )


def test_component_placement_is_strict_and_frozen() -> None:
    manifest = _manifest("library", kind="archetype")
    placement = ComponentPlacement(manifest=manifest, content_paths=("a.txt",))

    with pytest.raises(ValidationError, match="frozen"):
        placement.content_paths = ("b.txt",)
    with pytest.raises(ValidationError):
        ComponentPlacement.model_validate(
            {
                "manifest": manifest,
                "content_paths": ("a.txt",),
                "unexpected": True,
            }
        )
