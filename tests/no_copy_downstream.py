"""Test-only Blueprint-style client using the supported Forge facade.

This module deliberately lives under ``tests/`` and imports engine behavior
only from the top-level :mod:`forge_template` package. It proves the no-copy
client boundary without introducing a shipped organisation-policy resolver or
making Forge's private catalogue test seam part of the public API.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass

from forge_template import (
    ComponentDescriptor,
    GenerationPlan,
    ProjectSpec,
    RenderedProject,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)
from tests.organisation_policy_contract import (
    POLICY_FIXTURES,
    ExplicitSelection,
    load_policy,
    merge_policies,
    resolve_selection,
)


@dataclass(frozen=True)
class DownstreamGeneration:
    """One effective specification and its side-effect-free engine results."""

    spec: ProjectSpec
    plan: GenerationPlan
    project: RenderedProject


def generate_from_policies(
    payload: Mapping[str, object],
    *,
    policy_names: Sequence[str],
    explicit: ExplicitSelection,
    catalogue: Sequence[ComponentDescriptor] | None = None,
) -> DownstreamGeneration:
    """Resolve policy, construct ProjectSpec, and call the public engine API."""

    available = tuple(catalogue) if catalogue is not None else discover_components()
    policies = tuple(load_policy(POLICY_FIXTURES[name]) for name in policy_names)
    merged = merge_policies(policies)
    selection = resolve_selection(
        merged,
        explicit=explicit,
        catalogue=available,
    )

    effective_payload = deepcopy(dict(payload))
    effective_payload["components"] = {
        "archetype": selection.archetype,
        "capabilities": list(selection.capabilities),
        "platforms": list(selection.platforms),
    }
    effective_payload["provenance"] = {"policies": sorted(merged.policy_ids)}

    spec = parse_project_spec(effective_payload)
    plan = plan_generation(spec)
    project = render_project(spec)
    return DownstreamGeneration(spec=spec, plan=plan, project=project)
