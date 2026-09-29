"""Exhaustive composition sweep -- FT-17.05 / ADR 0066.

Every prior "every valid composition" enumeration in this repo is a
hand-written literal frozen at the pre-Stage-17 ten
(``tests/test_composition_architecture_review.py``,
``tests/test_cross_repository_validation.py``,
``tests/test_capability_composition.py``). The real count is
:data:`tests.composition_matrix.EXPECTED_COMPOSITION_COUNT` compositions --
four archetypes (three until FT-20.01 added ``streamlit``), any accepted subset
of ten capabilities, ``github`` on or off. This module plans and renders every
one of them, proving row I1's
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
    plan_generation,
    render_project,
)
from tests.composition_fingerprints import (
    fingerprint,
    load_fingerprints,
    sweep_spec,
)
from tests.composition_matrix import (
    EXPECTED_COMPOSITION_COUNT,
    valid_compositions,
)

if TYPE_CHECKING:
    from tests.composition_matrix import Composition

pytestmark = pytest.mark.sweep

_COMPOSITIONS = valid_compositions()
_FINGERPRINTS = load_fingerprints()


def test_the_derived_matrix_size_is_the_recorded_tripwire() -> None:
    """A changed count means the catalogue changed -- worth noticing in
    review, never silently updated to match."""
    assert len(_COMPOSITIONS) == EXPECTED_COMPOSITION_COUNT


def test_the_fingerprint_baseline_covers_exactly_the_derived_matrix() -> None:
    """FT-25.01: every accepted composition has exactly one recorded
    fingerprint (tests/fixtures/composition_fingerprints.json)."""
    assert set(_FINGERPRINTS) == {composition.slug for composition in _COMPOSITIONS}


@pytest.mark.parametrize("composition", _COMPOSITIONS, ids=lambda c: c.slug)
def test_every_valid_composition_plans_and_renders(composition: Composition) -> None:
    spec = sweep_spec(composition)
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

    # FT-25.01 / ADR 0079: the client-observable output is byte-for-byte the
    # recorded baseline. A mismatch is a behaviour change to explain, never a
    # fixture to regenerate reflexively (tests/composition_fingerprints.py).
    assert fingerprint(project) == _FINGERPRINTS[composition.slug], (
        f"{composition.slug}: rendered output drifted from the recorded "
        "fingerprint baseline"
    )
