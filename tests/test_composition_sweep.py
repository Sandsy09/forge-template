"""Exhaustive composition sweep -- FT-17.05 / ADR 0066.

Every prior "every valid composition" enumeration in this repo is a
hand-written literal frozen at the pre-Stage-17 ten
(``tests/test_composition_architecture_review.py``,
``tests/test_cross_repository_validation.py``,
``tests/test_capability_composition.py``). Post-FT-17.03 the real count is
:data:`tests.composition_matrix.EXPECTED_COMPOSITION_COUNT` compositions --
three archetypes, any accepted subset of ten capabilities, ``github`` on or
off. This module plans and renders every one of them, proving row I1's
"renders every valid composition" and row R1's regression claim generalise
past the ten compositions those earlier suites cover.

``sweep``-marked (``uv run poe sweep``, ``-n 4 --no-cov``): plan+render across
the full matrix, ~1s each single-process. ``--no-cov`` matters here
specifically -- coverage.py's branch tracing measurably slows this many
CPU-bound in-process calls (unlike ``combos``/``archetype``/``crossrepo``,
dominated by subprocess wall time, where the same instrumentation is noise),
and every line this sweep exercises is already covered by the fast suite
`poe check` runs with coverage on. Deliberately its own marker rather than
joining ``archetype`` -- it builds nothing and installs nothing, so it does
not share that marker's network/build cost profile, and keeping it separate
lets CI run both in parallel jobs. See docs/provider-acceptance-validation.md.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest

from forge_template import (
    FoundationOwner,
    parse_project_spec,
    plan_generation,
    render_project,
)
from tests.composition_matrix import (
    EXPECTED_COMPOSITION_COUNT,
    Composition,
    valid_compositions,
)

if TYPE_CHECKING:
    from forge_template import ProjectSpec

pytestmark = pytest.mark.sweep

_COMPOSITIONS = valid_compositions()


def _payload(composition: Composition) -> dict[str, object]:
    options: dict[str, dict[str, object]] = {
        "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"},
    }
    if "github" in composition.platforms:
        options["github"] = {"organisation": "sweep-org"}
    if "coverage" in composition.capabilities:
        options["coverage"] = {"fail_under": 80}
    if "documentation" in composition.capabilities:
        options["documentation"] = {"site_name": "Sweep Fixture"}
    return {
        "protocol_version": 1,
        "project": {
            "name": "Composition Sweep Fixture",
            "package_name": "composition_sweep_fixture",
            "repository_name": "composition-sweep-fixture",
            "description": "FT-17.05 exhaustive composition sweep fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": composition.archetype,
            "capabilities": list(composition.capabilities),
            "platforms": list(composition.platforms),
        },
        "component_options": {
            component_id: value
            for component_id, value in options.items()
            if component_id == composition.archetype
            or component_id in composition.capabilities
            or component_id in composition.platforms
        },
    }


def _spec(composition: Composition) -> ProjectSpec:
    return parse_project_spec(_payload(composition))


def test_the_derived_matrix_size_is_the_recorded_tripwire() -> None:
    """A changed count means the catalogue changed -- worth noticing in
    review, never silently updated to match."""
    assert len(_COMPOSITIONS) == EXPECTED_COMPOSITION_COUNT


@pytest.mark.parametrize("composition", _COMPOSITIONS, ids=lambda c: c.slug)
def test_every_valid_composition_plans_and_renders(composition: Composition) -> None:
    spec = _spec(composition)
    plan = plan_generation(spec)

    expected_order = (
        composition.archetype,
        *sorted(composition.capabilities),
        *sorted(composition.platforms),
    )
    assert plan.component_order == expected_order

    selected = {
        composition.archetype,
        *composition.capabilities,
        *composition.platforms,
    }
    for planned in plan.files:
        assert (
            isinstance(planned.owner, FoundationOwner) or planned.owner.id in selected
        )

    project = render_project(spec)
    files = {item.target: item.content for item in project.files}
    assert set(files) == {item.target for item in plan.files}

    pyproject = tomllib.loads(files["pyproject.toml"].decode("utf-8"))
    dependencies = pyproject["project"].get("dependencies", [])
    assert all(
        not dependency.lower().startswith(("forge-template", "create-forge"))
        for dependency in dependencies
    )
