"""Executable pin for docs/platform-and-tooling-parity.md (FT-15.03 / ADR 0060).

The contract assigns every provider-owned parity gap to a catalogue component
and reserves eight extension points. These tests keep it honest:

* every provider-owned ``gap`` row in ``engine-default-parity.md`` (bar the
  FT-15.02 provenance rows) is assigned an owner here -- a row gaining none
  fails;
* the five reserved Foundation points are still absent from the live
  ``foundation.toml``, so this file fails deliberately when FT-17.03 publishes
  them;
* ``discover_components()`` still returns exactly three archetypes, two
  capabilities and zero platforms, enforcing FT-ROADMAP-01-EX-03;
* and a four-component synthetic catalogue -- overlaid on the *real* production
  catalogue with the *real* Foundation live, following FT-11.04's precedent --
  proves the decided platform shape composes: a path-free descriptor with one
  option, a capability step reaching a platform target against tier order, and
  the cross-tier ``requires``/``conflicts`` edges rejecting before any render.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

import forge_template.engine as engine_module
from forge_template import (
    ComponentOwner,
    EngineErrorCode,
    ForgeEngineError,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)
from forge_template.foundation_source import load_foundation_source

_ROOT = Path(__file__).parents[1]
_CONTRACT = _ROOT / "docs" / "platform-and-tooling-parity.md"
_PARITY = _ROOT / "docs" / "engine-default-parity.md"
_SRC = _ROOT / "src" / "forge_template"
_PRODUCTION_COMPONENTS = _SRC / "components"
_FOUNDATION_TOML = _SRC / "foundation" / "foundation.toml"
_SYNTHETIC_FIXTURES = Path(__file__).parent / "fixtures" / "platform_composition"

_SYNTHETIC = (
    "host-bound-updates",
    "host-ci-extension",
    "host-free-updates",
    "reference-host",
)

_CONTRACT_OWNERS = {
    "github",
    "coverage",
    "pre-commit",
    "pyright",
    "changelog",
    "documentation",
    "dotenv-example",
    "dependabot",
    "renovate",
}

_RESERVED_FOUNDATION_POINTS = {
    "pyproject-project-urls",
    "contributing-project-shape",
    "security-project-shape",
    "pyproject-named-dependency-groups",
    "pyproject-dependency-group-includes",
}


# --- catalogue overlay ----------------------------------------------------


@pytest.fixture
def overlaid_catalogue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The real production catalogue plus the four synthetic components.

    Only ``_CATALOGUE_ROOT_OVERRIDE`` moves; the installed Foundation source
    stays live, so this exercises the shipped composition surface rather than a
    fixture copy of it -- the same isolation
    ``tests/test_capability_composition.py`` relies on.
    """
    root = tmp_path / "components"
    shutil.copytree(_PRODUCTION_COMPONENTS, root)
    for component in _SYNTHETIC:
        shutil.copytree(_SYNTHETIC_FIXTURES / component, root / component)
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", root)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", None)
    return root


def _payload(
    *,
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
    host_option: bool = False,
) -> dict[str, object]:
    options: dict[str, object] = {
        "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"}
    }
    if host_option:
        options["reference-host"] = {"organisation": "forge-example"}
    return {
        "protocol_version": 1,
        "project": {
            "name": "Platform Composition Fixture",
            "package_name": "platform_composition_fixture",
            "repository_name": "platform-composition-fixture",
            "description": "FT-15.03 platform composition fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": "library",
            "capabilities": list(capabilities),
            "platforms": list(platforms),
        },
        "component_options": options,
    }


# --- doc parsing --------------------------------------------------------------


def _parity_gap_rows() -> set[str]:
    """Provider-owned ``gap`` keys in engine-default-parity.md, minus the
    FT-15.02 provenance rows FT-15.03 does not own."""
    keys: set[str] = set()
    for raw in _PARITY.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 7:
            continue
        key = re.fullmatch(r"`([^`]+)`", cells[0])
        if key is None:
            continue
        _, _, status, disposition, _, owner, _ = cells
        if status == "gap" and disposition == "provider" and "FT-15.02" not in owner:
            keys.add(key.group(1))
    return keys


def _contract_ownership() -> dict[str, set[str]]:
    """The `Parity row` -> owner map from the contract's assignment table."""
    text = _CONTRACT.read_text(encoding="utf-8")
    start = text.index("## Provider-owned parity rows and their owners")
    end = text.index("## What this contract does not decide", start)
    rows: dict[str, set[str]] = {}
    for raw in text[start:end].splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        key = re.fullmatch(r"`([^`]+)`", cells[0])
        if key is None:
            continue
        rows[key.group(1)] = set(re.findall(r"`([a-z][a-z-]+)`", cells[1]))
    return rows


def _live_foundation_point_ids() -> set[str]:
    foundation = load_foundation_source(_FOUNDATION_TOML)
    return {point.id for point in foundation.extension_points}


# --- derived contract checks ------------------------------------------------


def test_every_provider_owned_gap_row_has_exactly_one_assignment() -> None:
    parity = _parity_gap_rows()
    ownership = _contract_ownership()

    assert parity, "no provider-owned gap rows parsed from engine-default-parity.md"
    assert set(ownership) == parity, (
        "ownership table and the parity matrix disagree: "
        f"unassigned={sorted(parity - set(ownership))}, "
        f"stale={sorted(set(ownership) - parity)}"
    )
    for key, owners in ownership.items():
        assert owners, f"{key}: names no owner"
        assert owners <= _CONTRACT_OWNERS, f"{key}: unknown owner(s) {owners}"


def test_dependency_updates_names_both_updaters() -> None:
    assert _contract_ownership()["dependency_updates"] == {"dependabot", "renovate"}


def test_reserved_foundation_points_are_not_yet_published() -> None:
    """Tripwire: fails when FT-17.03 adds one of these to foundation.toml,
    forcing docs/platform-and-tooling-parity.md and ADR 0060 to be revisited."""
    live = _live_foundation_point_ids()
    for point in _RESERVED_FOUNDATION_POINTS:
        assert point not in live, (
            f"{point!r} is now published -- update the contract to move it out "
            "of the reserved set"
        )
        assert point in _CONTRACT.read_text(encoding="utf-8")


def test_existing_points_the_contract_reuses_are_live() -> None:
    """`readme-project-shape` is the one existing Foundation point `github` and
    the capabilities reuse; it must really be published."""
    assert "readme-project-shape" in _live_foundation_point_ids()
    assert "readme-project-shape" in _CONTRACT.read_text(encoding="utf-8")


def test_contract_states_the_exclusion_and_the_archetype_set() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "FT-ROADMAP-01-EX-03" in text
    assert "no archetype" in text.lower()
    assert "`cli`, `data-science`, `library`" in text


# --- FT-ROADMAP-01-EX-03: the catalogue is unchanged ------------------------


def test_discovery_is_still_three_archetypes_two_capabilities_no_platform() -> None:
    """Runs against the real installed catalogue -- no overlay."""
    kinds = sorted(component.kind for component in discover_components())
    assert kinds == ["archetype", "archetype", "archetype", "capability", "capability"]
    assert not [c for c in discover_components() if c.kind == "platform"]


# --- synthetic platform composition ----------------------------------------


def test_synthetic_platform_descriptor_is_path_free_with_one_option(
    overlaid_catalogue: Path,
) -> None:
    descriptors = {d.id: d for d in discover_components()}
    host = descriptors["reference-host"]
    assert host.kind == "platform"

    serialised = host.model_dump_json()
    for leak in (
        "content_root",
        "options_schema",
        "extensions/",
        "content/",
        "component.toml",
        "fixtures",
        "\\\\",
        "//",
    ):
        assert leak not in serialised, f"descriptor leaks {leak!r}"

    assert [option["name"] for option in host.model_dump()["options"]] == [
        "organisation"
    ]


def test_capability_step_reaches_the_platform_target_against_tier_order(
    overlaid_catalogue: Path,
) -> None:
    spec = parse_project_spec(
        _payload(
            capabilities=("host-ci-extension",),
            platforms=("reference-host",),
            host_option=True,
        )
    )
    plan = plan_generation(spec)

    ci = next(item for item in plan.files if item.target == "ci.yml")
    assert isinstance(ci.owner, ComponentOwner)
    assert ci.owner.id == "reference-host"
    contributed = {
        extension.extension_point
        for extension in ci.extensions
        if extension.component_id == "host-ci-extension"
    }
    assert contributed == {"ci-steps"}

    # The capability tier applies before the platform tier even though the
    # capability extends the platform.
    order = list(plan.component_order)
    assert order.index("host-ci-extension") < order.index("reference-host")

    rendered = {item.target: item.content for item in render_project(spec).files}
    assert b"echo extended" in rendered["ci.yml"]


def test_cross_tier_requires_edge_rejects_before_render(
    overlaid_catalogue: Path,
) -> None:
    payload = _payload(capabilities=("host-bound-updates",))  # no reference-host

    for call in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as caught:
            call(parse_project_spec(payload))
        assert caught.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
        assert caught.value.operation == "validate"


def test_conflicts_edge_rejects_before_render(overlaid_catalogue: Path) -> None:
    payload = _payload(
        capabilities=("host-bound-updates", "host-free-updates"),
        platforms=("reference-host",),
        host_option=True,
    )

    for call in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as caught:
            call(parse_project_spec(payload))
        assert caught.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
        assert caught.value.operation == "validate"


def test_platform_composition_is_deterministic_and_platform_applies_last(
    overlaid_catalogue: Path,
) -> None:
    payload = _payload(
        capabilities=("host-ci-extension",),
        platforms=("reference-host",),
        host_option=True,
    )

    plan = plan_generation(parse_project_spec(payload))
    order = list(plan.component_order)
    assert order == ["library", "host-ci-extension", "reference-host"]

    first = {
        item.target: item.content
        for item in render_project(parse_project_spec(payload)).files
    }
    again = {
        item.target: item.content
        for item in render_project(parse_project_spec(payload)).files
    }
    assert first == again
