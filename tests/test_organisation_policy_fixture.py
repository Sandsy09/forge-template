"""Compatibility tests for docs/organisation-policy-fixtures.md and ADR 0040.

Exercises ``tests/organisation_policy_contract.py``, the test-only reference
resolver, against the checked-in placeholder policy documents. Proves the
documented authority order, merge semantics, all 17 named structured-failure
detail codes, the policy/content-extension boundary
([extension-points.md](../docs/extension-points.md)), and one resolution that
actually renders a real project through the public
[template-engine API](../docs/template-engine-api.md).
"""

from __future__ import annotations

import itertools
import json
from typing import Literal

import pytest

from forge_template import (
    ComponentDescriptor,
    ComponentSelection,
    discover_components,
    parse_project_spec,
    render_project,
)
from tests.organisation_policy_contract import (
    POLICY_FIXTURES,
    ExplicitSelection,
    PolicyError,
    load_policy,
    merge_policies,
    parse_policy_document,
    resolve_selection,
)

_FIXTURE_CATALOGUE: tuple[
    tuple[str, Literal["archetype", "capability", "platform"]], ...
] = (
    ("library", "archetype"),
    ("library-v2", "archetype"),
    ("changelog", "capability"),
    ("coverage", "capability"),
    ("documentation", "capability"),
    ("github", "platform"),
)


def _fixture_descriptors() -> tuple[ComponentDescriptor, ...]:
    """Minimal real ``ComponentDescriptor`` values -- only ``id``/``kind``
    are exercised by the reference resolver, but a real model is used
    rather than a stand-in so no type-ignore is needed at the call sites."""
    return tuple(
        ComponentDescriptor(
            id=identifier,
            name=identifier,
            description="",
            kind=kind,
            version="1.0.0",
            projectspec_protocols=(1,),
            requires_python=">=3.11",
            requires=(),
            conflicts=(),
            options=(),
        )
        for identifier, kind in _FIXTURE_CATALOGUE
    )


def _production_payload() -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Policy Fixture Project",
            "package_name": "policy_fixture_project",
            "repository_name": "policy-fixture-project",
            "description": "FT-09.03 organisation-policy reference fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {"archetype": "library", "capabilities": [], "platforms": []},
        "component_options": {
            "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"}
        },
    }


def test_defaults_fill_only_absent_selections() -> None:
    """A policy default applies only when nothing higher-authority was
    supplied; an explicit choice, including an explicitly empty one, is
    never overwritten."""
    baseline = load_policy(POLICY_FIXTURES["example-baseline"])
    merged = merge_policies([baseline])
    catalogue = _fixture_descriptors()

    # No explicit choice at all: every policy default applies.
    filled = resolve_selection(
        merged,
        explicit=ExplicitSelection(),
        catalogue=catalogue,
    )
    assert filled == ComponentSelection(
        archetype="library",
        capabilities=("coverage",),
        platforms=("github",),
    )

    # An explicit, non-empty archetype/platforms choice replaces the
    # matching default; capabilities is left absent so its default still
    # fills -- and the required "coverage" capability is still present.
    explicit_wins = resolve_selection(
        merged,
        explicit=ExplicitSelection(archetype="library", platforms=frozenset()),
        catalogue=catalogue,
    )
    assert explicit_wins == ComponentSelection(
        archetype="library", capabilities=("coverage",), platforms=()
    )


def test_required_and_forbidden_validate_without_mutating() -> None:
    """Required/forbidden rules validate the resolved selection; they never
    silently add a missing requirement or drop a forbidden one."""
    baseline = load_policy(POLICY_FIXTURES["example-baseline"])
    merged = merge_policies([baseline])
    catalogue = _fixture_descriptors()

    # "coverage" is required but the explicit choice omits it -- resolution
    # fails rather than the resolver quietly adding it.
    with pytest.raises(PolicyError) as exc_info:
        resolve_selection(
            merged,
            explicit=ExplicitSelection(
                archetype="library", capabilities=frozenset(), platforms=frozenset()
            ),
            catalogue=catalogue,
        )
    error = exc_info.value
    assert error.category == "organisation-policy-violation"
    assert any(
        detail.code == "required-selection-missing"
        and detail.path == "capabilities.coverage"
        for detail in error.details
    )

    # "documentation" is forbidden but explicitly selected anyway -- resolution
    # fails rather than the resolver quietly dropping it.
    with pytest.raises(PolicyError) as exc_info:
        resolve_selection(
            merged,
            explicit=ExplicitSelection(
                archetype="library",
                capabilities=frozenset({"coverage", "documentation"}),
            ),
            catalogue=catalogue,
        )
    error = exc_info.value
    assert error.category == "organisation-policy-violation"
    assert any(
        detail.code == "forbidden-selection-selected"
        and detail.path == "capabilities.documentation"
        for detail in error.details
    )


def test_multiple_policies_merge_independently_of_order() -> None:
    """The delivery/quality worked example from organisation-policy.md
    merges to one identical result regardless of caller order."""
    delivery = load_policy(POLICY_FIXTURES["example-delivery-baseline"])
    quality = load_policy(POLICY_FIXTURES["example-quality-baseline"])

    results = {
        merge_policies(list(permutation))
        for permutation in itertools.permutations([delivery, quality])
    }
    assert len(results) == 1

    (merged,) = results
    assert merged.policy_ids == {
        "example-delivery-baseline",
        "example-quality-baseline",
    }
    assert merged.required.platforms == frozenset({"github"})
    assert merged.defaults.capabilities == frozenset({"coverage"})
    assert merged.forbidden.capabilities == frozenset({"documentation"})

    # The restricted-delivery policy requires the same platform
    # example-delivery-baseline forbids -- irreconcilable regardless of order.
    restricted = load_policy(POLICY_FIXTURES["example-restricted-delivery"])
    for permutation in itertools.permutations([delivery, restricted]):
        with pytest.raises(PolicyError) as exc_info:
            merge_policies(list(permutation))
        error = exc_info.value
        assert error.category == "organisation-policy-conflict"
        assert any(
            detail.code == "required-forbidden-conflict" for detail in error.details
        )


def test_every_documented_detail_code_is_reachable() -> None:
    """All 17 detail codes organisation-policy.md names across its three
    structured-failure categories are actually reachable, not just prose."""
    catalogue = _fixture_descriptors()

    # -- document category (6) --------------------------------------------
    document_cases: dict[str, dict[str, object]] = {
        "unsupported-policy-version": {
            "policy_version": 2,
            "id": "example-x",
            "required": {"platforms": ["github"]},
        },
        "invalid-policy-id": {
            "policy_version": 1,
            "id": "NOT-KEBAB",
            "required": {"platforms": ["github"]},
        },
        "invalid-field-type": {
            "policy_version": 1,
            "id": "example-x",
            "defaults": "not-an-object",
        },
        "unknown-field": {
            "policy_version": 1,
            "id": "example-x",
            "unexpected": True,
            "required": {"platforms": ["github"]},
        },
        "duplicate-selection-id": {
            "policy_version": 1,
            "id": "example-x",
            "required": {"platforms": ["github", "github"]},
        },
        "empty-policy": {"policy_version": 1, "id": "example-x"},
    }
    for expected_code, payload in document_cases.items():
        with pytest.raises(PolicyError) as exc_info:
            parse_policy_document(payload, source="inline")
        error = exc_info.value
        assert error.category == "invalid-organisation-policy"
        assert any(detail.code == expected_code for detail in error.details), (
            expected_code
        )

    # -- policy-set category (6) --------------------------------------------
    a = parse_policy_document(
        {"policy_version": 1, "id": "example-a", "defaults": {"archetype": "library"}},
        source="a",
    )
    b_conflicting_default = parse_policy_document(
        {
            "policy_version": 1,
            "id": "example-b",
            "defaults": {"archetype": "library-v2"},
        },
        source="b",
    )
    with pytest.raises(PolicyError) as exc_info:
        merge_policies([a, b_conflicting_default])
    assert any(
        detail.code == "conflicting-archetype-default"
        for detail in exc_info.value.details
    )

    a_required = parse_policy_document(
        {"policy_version": 1, "id": "example-a", "required": {"archetype": "library"}},
        source="a",
    )
    b_required_conflicting = parse_policy_document(
        {
            "policy_version": 1,
            "id": "example-b",
            "required": {"archetype": "library-v2"},
        },
        source="b",
    )
    with pytest.raises(PolicyError) as exc_info:
        merge_policies([a_required, b_required_conflicting])
    assert any(
        detail.code == "conflicting-archetype-requirement"
        for detail in exc_info.value.details
    )

    default_only = parse_policy_document(
        {"policy_version": 1, "id": "example-a", "defaults": {"archetype": "library"}},
        source="a",
    )
    required_other = parse_policy_document(
        {
            "policy_version": 1,
            "id": "example-b",
            "required": {"archetype": "library-v2"},
        },
        source="b",
    )
    with pytest.raises(PolicyError) as exc_info:
        merge_policies([default_only, required_other])
    assert any(
        detail.code == "default-requirement-conflict"
        for detail in exc_info.value.details
    )

    default_capability = parse_policy_document(
        {
            "policy_version": 1,
            "id": "example-a",
            "defaults": {"capabilities": ["coverage"]},
        },
        source="a",
    )
    forbid_same_capability = parse_policy_document(
        {
            "policy_version": 1,
            "id": "example-b",
            "forbidden": {"capabilities": ["coverage"]},
        },
        source="b",
    )
    with pytest.raises(PolicyError) as exc_info:
        merge_policies([default_capability, forbid_same_capability])
    assert any(
        detail.code == "default-forbidden-conflict" for detail in exc_info.value.details
    )

    required_platform = parse_policy_document(
        {"policy_version": 1, "id": "example-a", "required": {"platforms": ["github"]}},
        source="a",
    )
    forbid_same_platform = parse_policy_document(
        {
            "policy_version": 1,
            "id": "example-b",
            "forbidden": {"platforms": ["github"]},
        },
        source="b",
    )
    with pytest.raises(PolicyError) as exc_info:
        merge_policies([required_platform, forbid_same_platform])
    assert any(
        detail.code == "required-forbidden-conflict"
        for detail in exc_info.value.details
    )

    duplicate_id = parse_policy_document(
        {"policy_version": 1, "id": "example-a", "required": {"platforms": ["github"]}},
        source="a2",
    )
    with pytest.raises(PolicyError) as exc_info:
        merge_policies([required_platform, duplicate_id])
    # required_platform.id == "example-a" == duplicate_id.id
    assert any(
        detail.code == "duplicate-policy-id" for detail in exc_info.value.details
    )

    # -- effective-selection category (5) -----------------------------------
    no_rules = parse_policy_document(
        {"policy_version": 1, "id": "example-c", "defaults": {"platforms": ["github"]}},
        source="c",
    )
    merged_no_rules = merge_policies([no_rules])

    with pytest.raises(PolicyError) as exc_info:
        resolve_selection(
            merged_no_rules,
            explicit=ExplicitSelection(archetype="does-not-exist"),
            catalogue=catalogue,
        )
    assert any(detail.code == "unknown-component" for detail in exc_info.value.details)

    with pytest.raises(PolicyError) as exc_info:
        resolve_selection(
            merged_no_rules,
            explicit=ExplicitSelection(
                archetype="github"
            ),  # a platform, not an archetype
            catalogue=catalogue,
        )
    assert any(
        detail.code == "component-kind-mismatch" for detail in exc_info.value.details
    )

    with pytest.raises(PolicyError) as exc_info:
        resolve_selection(
            merged_no_rules,
            explicit=ExplicitSelection(),
            catalogue=catalogue,
        )
    assert any(
        detail.code == "no-permitted-archetype" for detail in exc_info.value.details
    )

    # required-selection-missing and forbidden-selection-selected are already
    # covered by test_required_and_forbidden_validate_without_mutating.
    baseline = load_policy(POLICY_FIXTURES["example-baseline"])
    merged_baseline = merge_policies([baseline])
    with pytest.raises(PolicyError) as exc_info:
        resolve_selection(
            merged_baseline,
            explicit=ExplicitSelection(archetype="library", capabilities=frozenset()),
            catalogue=catalogue,
        )
    assert any(
        detail.code == "required-selection-missing" for detail in exc_info.value.details
    )


def test_policy_cannot_carry_content_metadata_or_options() -> None:
    """A policy naming a file, project-metadata field, or component option
    is rejected outright -- ties back to extension-points.md's four-surface
    split: selection is the only thing a policy may express."""
    for field_name, value in (
        ("content", "src/pyproject.toml.jinja"),
        ("project", {"name": "Example"}),
        ("component_options", {"library": {"packaging_mode": "hatchling-static"}}),
        ("override", True),
    ):
        payload = {
            "policy_version": 1,
            "id": "example-overreaching",
            "required": {"platforms": ["github"]},
            field_name: value,
        }
        with pytest.raises(PolicyError) as exc_info:
            parse_policy_document(payload, source="overreaching")
        error = exc_info.value
        assert error.category == "invalid-organisation-policy"
        assert any(
            detail.code == "unknown-field" and field_name in detail.path
            for detail in error.details
        ), field_name


def test_resolved_selection_renders_a_real_project() -> None:
    """A policy-resolved selection is directly ProjectSpec-shaped and
    renders a real project through the public engine API -- the end-to-end
    half a shipped resolver would also have to satisfy."""
    policy = load_policy(POLICY_FIXTURES["example-production-library"])
    merged = merge_policies([policy])
    catalogue = discover_components()

    selection = resolve_selection(
        merged,
        explicit=ExplicitSelection(
            archetype="library", capabilities=frozenset(), platforms=frozenset()
        ),
        catalogue=catalogue,
    )
    assert selection.archetype == "library"

    payload = _production_payload()
    payload["components"] = {
        "archetype": selection.archetype,
        "capabilities": list(selection.capabilities),
        "platforms": list(selection.platforms),
    }
    payload["provenance"] = {"policies": sorted(merged.policy_ids)}

    spec = parse_project_spec(payload)
    assert spec.provenance.policies == ("example-production-library",)

    rendered = render_project(spec)
    targets = {rendered_file.target for rendered_file in rendered.files}
    assert "pyproject.toml" in targets


def test_fixture_policies_carry_no_organisation_specific_values() -> None:
    """Every checked-in policy is a neutral placeholder: an ``example-``
    prefixed id, naming only identifiers a real catalogue actually has."""
    production_ids = {descriptor.id for descriptor in discover_components()}
    fixture_ids = {identifier for identifier, _ in _FIXTURE_CATALOGUE}
    allowed = production_ids | fixture_ids

    for name, path in POLICY_FIXTURES.items():
        assert name.startswith("example-"), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["id"].startswith("example-"), name

        referenced: set[str] = set()
        for section in ("defaults", "required"):
            rules = payload.get(section) or {}
            archetype = rules.get("archetype")
            if archetype is not None:
                referenced.add(archetype)
            referenced.update(rules.get("capabilities") or [])
            referenced.update(rules.get("platforms") or [])
        forbidden = payload.get("forbidden") or {}
        referenced.update(forbidden.get("archetypes") or [])
        referenced.update(forbidden.get("capabilities") or [])
        referenced.update(forbidden.get("platforms") or [])

        assert referenced <= allowed, (name, referenced - allowed)
