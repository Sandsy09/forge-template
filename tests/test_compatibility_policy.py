"""Executable assertions for docs/compatibility-policy.md and ADR 0041.

Pins the "Current compatibility state" table against the real engine
constants and installed catalogue, and proves the two behavioural claims the
document makes: that negotiation (``get_engine_info()``) never needs a
component catalogue, and that an unsupported ProjectSpec protocol fails
closed before any catalogue read. Following ``tests/test_extension_points.py``
(FT-09.02), expected values are written literally here rather than parsed out
of the Markdown -- a drift between the two shows up as a failing assertion
naming both.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

import forge_template.engine as engine_module
from forge_template import (
    EngineErrorCode,
    ForgeEngineError,
    discover_components,
    get_engine_info,
    parse_project_spec,
)
from forge_template.component_manifest import COMPONENT_MANIFEST_PROTOCOL_VERSIONS
from forge_template.foundation_source import (
    FOUNDATION_SOURCE_PROTOCOL_VERSION,
    load_foundation_source,
)
from forge_template.project_spec import PROJECT_SPEC_PROTOCOL_VERSION
from forge_template.template_variables import OPTION_SCHEMA_PROTOCOL_VERSIONS

_ROOT = Path(__file__).parents[1]
_FOUNDATION_TOML = _ROOT / "src" / "forge_template" / "foundation" / "foundation.toml"
_PYPROJECT_TOML = _ROOT / "pyproject.toml"


def _minimal_payload(archetype: str = "library") -> dict[str, object]:
    component_options: dict[str, object] = {}
    if archetype == "library":
        component_options = {
            "library": {
                "packaging_mode": "uv-build-static",
                "initial_version": "0.1.0",
            }
        }
    return {
        "protocol_version": PROJECT_SPEC_PROTOCOL_VERSION,
        "project": {
            "name": "Compatibility Policy Fixture",
            "package_name": "compatibility_policy_fixture",
            "repository_name": "compatibility-policy-fixture",
            "description": "FT-09.04 compatibility policy contract fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": [],
            "platforms": [],
        },
        "component_options": component_options,
    }


def test_published_compatibility_state_matches_the_engine() -> None:
    """docs/compatibility-policy.md's "Current compatibility state" table,
    executable -- every row checked against the real constant or the real
    installed catalogue it claims to describe."""
    info = get_engine_info()
    pyproject = tomllib.loads(_PYPROJECT_TOML.read_text(encoding="utf-8"))

    assert info.package_version == pyproject["project"]["version"] == "0.3.2"
    assert info.projectspec_protocols == (PROJECT_SPEC_PROTOCOL_VERSION,) == (1,)
    assert (
        info.component_manifest_protocols
        == COMPONENT_MANIFEST_PROTOCOL_VERSIONS
        == (1, 2)
    )
    assert OPTION_SCHEMA_PROTOCOL_VERSIONS == (1, 2)
    assert FOUNDATION_SOURCE_PROTOCOL_VERSION == 1

    foundation = load_foundation_source(_FOUNDATION_TOML)
    assert foundation.foundation_version == FOUNDATION_SOURCE_PROTOCOL_VERSION

    components = {c.id: c for c in discover_components()}
    assert components.keys() == {
        "cli",
        "jupyter",
        "library",
        "scientific-python",
    }
    assert components["library"].version == "1.0.1"
    assert components["cli"].version == "1.0.1"
    assert components["jupyter"].version == "1.0.0"
    assert components["scientific-python"].version == "1.0.0"


def test_component_versions_are_canonical_pep440() -> None:
    """Every discovered component's ``version`` and ``requires_python``
    parse as canonical PEP 440 -- the compatible-ranges section's
    precondition for talking about component version bumps at all."""
    for component in discover_components():
        parsed = Version(component.version)
        # Canonical round-trip: catches a non-canonical form (leading zeros,
        # local segments, non-normalised pre-release markers) slipping into a
        # manifest undetected.
        assert str(parsed) == component.version
        SpecifierSet(component.requires_python)


def test_negotiation_precedes_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ "What the engine publishes for negotiation": ``get_engine_info()``
    never needs a component catalogue, so package/protocol compatibility can
    be checked before any discovery, planning, or destination decision."""
    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", missing)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", missing)

    info = get_engine_info()
    assert info.package_version
    assert info.projectspec_protocols
    assert info.component_manifest_protocols

    with pytest.raises(ForgeEngineError) as exc_info:
        discover_components()
    assert exc_info.value.code is EngineErrorCode.COMPONENT_DISCOVERY_FAILED


def test_unsupported_protocol_fails_closed() -> None:
    """ "Reporting an unsupported Forge version": a ProjectSpec protocol
    outside the published tuple fails before any catalogue read, naming the
    mismatched axis rather than surfacing a generic parse error."""
    payload = _minimal_payload()
    payload["protocol_version"] = 999

    with pytest.raises(ForgeEngineError) as exc_info:
        parse_project_spec(payload)

    error = exc_info.value
    assert error.code is EngineErrorCode.INVALID_PROJECT_SPEC
    assert error.operation == "parse"
    assert error.details
    assert any(detail.path == ("protocol_version",) for detail in error.details)


def test_every_descriptor_publishes_the_negotiation_facts() -> None:
    """Every discovered component actually carries the facts a client needs
    to negotiate against it -- a non-empty, engine-supported protocol set and
    a real Python floor, not just an identity."""
    supported = get_engine_info().projectspec_protocols
    for component in discover_components():
        assert component.projectspec_protocols
        assert set(component.projectspec_protocols) & set(supported)
        assert re.match(r"^>=\d+\.\d+$", component.requires_python)
