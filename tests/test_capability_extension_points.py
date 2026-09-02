"""Executable acceptance criteria for FT-11.01 / ADR 0049.

The three capability-tooling extension points
(``pyproject-development-dependencies``, ``pyproject-task-definitions``,
``pyproject-aggregate-check``) are additive: an unfilled point contributes
zero bytes, manifest validation accepts contributions into each, multiple
capability contributions compose in composition order rather than
last-write-wins, and no protocol, package, or component version moves.

``tests/test_extension_points.py`` pins the eleven-entry inventory itself;
this module exercises the behaviour the four issue acceptance criteria name.
"""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path
from typing import Any

import pytest

import forge_template.engine as engine_module
from forge_template import (
    get_engine_info,
    parse_project_spec,
    render_project,
)
from forge_template.component_manifest import (
    load_component_manifest,
    validate_manifest_set,
)
from forge_template.foundation_source import (
    FOUNDATION_SOURCE_PROTOCOL_VERSION,
    load_foundation_source,
)

_SRC = Path(__file__).parents[1] / "src" / "forge_template"
_PRODUCTION_FOUNDATION = _SRC / "foundation"
_PRODUCTION_COMPONENTS = _SRC / "components"
_CAPABILITY_FIXTURES = Path(__file__).parent / "fixtures" / "capability_tooling"

_CAPABILITY_TOOLING_POINTS = (
    "pyproject-development-dependencies",
    "pyproject-task-definitions",
    "pyproject-aggregate-check",
)


def _payload(
    *,
    archetype: str = "library",
    capabilities: tuple[str, ...] = (),
) -> dict[str, object]:
    options: dict[str, Any] = {}
    if archetype == "library":
        options = {
            "library": {
                "packaging_mode": "uv-build-static",
                "initial_version": "0.1.0",
            }
        }
    return {
        "protocol_version": 1,
        "project": {
            "name": "Capability Tooling Fixture",
            "package_name": "capability_tooling_fixture",
            "repository_name": "capability-tooling-fixture",
            "description": "FT-11.01 capability-tooling extension-point fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": list(capabilities),
            "platforms": [],
        },
        "component_options": options,
    }


def _render(payload: dict[str, object]) -> dict[str, bytes]:
    spec = parse_project_spec(payload)
    return {item.target: item.content for item in render_project(spec).files}


def _strip_capability_tooling_points(foundation_root: Path) -> None:
    """Remove the three FT-11.01 points and their markers in place.

    Leaves a Foundation source that predates FT-11.01 entirely, so a render
    against it is the byte-for-byte baseline the additive points must match
    when no capability fills them.
    """
    manifest = foundation_root / "foundation.toml"
    blocks = manifest.read_text(encoding="utf-8").split("[[extension_points]]")
    kept = [blocks[0]] + [
        block
        for block in blocks[1:]
        if not any(f'id = "{point}"' in block for point in _CAPABILITY_TOOLING_POINTS)
    ]
    manifest.write_text("[[extension_points]]".join(kept), encoding="utf-8")

    pyproject = foundation_root / "content" / "pyproject.toml.jinja"
    lines = pyproject.read_text(encoding="utf-8").splitlines(keepends=True)
    pyproject.write_text(
        "".join(
            line
            for line in lines
            if not any(
                line.strip() == f"[[forge:extension {point}]]"
                for point in _CAPABILITY_TOOLING_POINTS
            )
        ),
        encoding="utf-8",
    )


@pytest.fixture
def catalogue_with_capability_fixtures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """The real production catalogue plus the two synthetic capabilities.

    Only ``_CATALOGUE_ROOT_OVERRIDE`` is redirected: the production Foundation
    source -- with the three real FT-11.01 points -- stays live, so this
    exercises the shipped extension points, not a fixture copy of them.
    """
    root = tmp_path / "components"
    shutil.copytree(_PRODUCTION_COMPONENTS, root)
    for capability in ("alpha-tooling", "beta-tooling"):
        shutil.copytree(_CAPABILITY_FIXTURES / capability, root / capability)
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", root)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", None)
    return root


# --- Acceptance criterion 2: empty points are byte-neutral -------------------


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_unfilled_points_render_production_archetypes_unchanged(
    archetype: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", None)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", None)
    production = _render(_payload(archetype=archetype))

    stripped = tmp_path / "foundation"
    shutil.copytree(_PRODUCTION_FOUNDATION, stripped)
    _strip_capability_tooling_points(stripped)
    pre_capability_catalogue = tmp_path / "components"
    shutil.copytree(_PRODUCTION_COMPONENTS, pre_capability_catalogue)
    shutil.rmtree(pre_capability_catalogue / "jupyter")
    monkeypatch.setattr(
        engine_module, "_CATALOGUE_ROOT_OVERRIDE", pre_capability_catalogue
    )
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", stripped)
    baseline = _render(_payload(archetype=archetype))

    assert production == baseline


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_aggregate_check_reformat_is_semantics_only(archetype: str) -> None:
    """The one deliberate output change (ADR 0049): the ``check`` array is
    multi-line, but parses to exactly the historic five-entry sequence."""
    payload = tomllib.loads(
        _render(_payload(archetype=archetype))["pyproject.toml"].decode()
    )
    tasks = payload["tool"]["poe"]["tasks"]

    assert tasks["check"] == [
        "lock:check",
        "format:check",
        "lint",
        "typecheck",
        "test",
    ]
    assert payload["dependency-groups"]["dev"] == [
        {"include-group": "lint"},
        {"include-group": "test"},
        {"include-group": "typecheck"},
        "poethepoet>=0.31",
    ]


# --- Acceptance criterion 1: manifest validation recognises contributions ---


def test_manifest_validation_accepts_contributions_to_each_point() -> None:
    foundation = load_foundation_source(_PRODUCTION_FOUNDATION / "foundation.toml")
    published = {point.id for point in foundation.extension_points}
    assert set(_CAPABILITY_TOOLING_POINTS) <= published

    manifests = (
        *(
            load_component_manifest(
                _CAPABILITY_FIXTURES / capability / "component.toml"
            )
            for capability in ("alpha-tooling", "beta-tooling")
        ),
        load_component_manifest(_PRODUCTION_COMPONENTS / "library" / "component.toml"),
    )

    validate_manifest_set(manifests, foundation)

    contributed = {
        contribution.extension_point
        for manifest in manifests
        for contribution in manifest.contributions
    }
    assert set(_CAPABILITY_TOOLING_POINTS) <= contributed


def test_contribution_to_an_undeclared_point_is_rejected(
    tmp_path: Path,
) -> None:
    foundation = load_foundation_source(_PRODUCTION_FOUNDATION / "foundation.toml")

    broken = tmp_path / "broken-tooling"
    shutil.copytree(_CAPABILITY_FIXTURES / "alpha-tooling", broken)
    manifest = broken / "component.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "pyproject-task-definitions", "pyproject-task-definitions-typo"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="pyproject-task-definitions-typo"):
        validate_manifest_set((load_component_manifest(manifest),), foundation)


# --- Acceptance criterion 3: multiple contributions compose in order --------


def test_multiple_capability_contributions_compose_without_last_write_wins(
    catalogue_with_capability_fixtures: Path,
) -> None:
    # Selection order is deliberately reversed to prove composition order, not
    # selection order, decides the result.
    files = _render(_payload(capabilities=("beta-tooling", "alpha-tooling")))
    pyproject = files["pyproject.toml"]
    assert b"forge:extension" not in pyproject

    text = pyproject.decode()
    payload = tomllib.loads(text)
    tasks = payload["tool"]["poe"]["tasks"]

    # Every contribution survives -- nothing is overwritten.
    assert payload["dependency-groups"]["dev"][-2:] == [
        "alpha-tooling-dep>=1,<2",
        "beta-tooling-dep>=2,<3",
    ]
    assert tasks["alpha:check"] == "python -c \"print('alpha')\""
    assert tasks["beta:check"] == "python -c \"print('beta')\""
    assert tasks["check"] == [
        "lock:check",
        "format:check",
        "lint",
        "typecheck",
        "test",
        "alpha:check",
        "beta:check",
    ]

    # Composition order: archetype tier is applied before the capability
    # tier, and lexical order breaks the tie inside it -- alpha before beta.
    assert text.index('"alpha-tooling-dep') < text.index('"beta-tooling-dep')
    assert text.index('"alpha:check" =') < text.index('"beta:check" =')


# --- Acceptance criterion 4: no protocol or version moves ------------------


def test_no_protocol_or_version_moves() -> None:
    source = load_foundation_source(_PRODUCTION_FOUNDATION / "foundation.toml")
    assert source.foundation_version == 1
    assert FOUNDATION_SOURCE_PROTOCOL_VERSION == 1

    info = get_engine_info()
    assert info.package_version == "0.3.2"
    assert info.projectspec_protocols == (1,)
    assert info.component_manifest_protocols == (1, 2)

    for archetype in ("library", "cli"):
        manifest = load_component_manifest(
            _PRODUCTION_COMPONENTS / archetype / "component.toml"
        )
        assert manifest.version == "1.0.1"
        assert manifest.extension_points == ()
