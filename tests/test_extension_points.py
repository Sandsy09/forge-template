"""Executable assertions for docs/extension-points.md and ADR 0039.

Pins the published content extension-point inventory, proves ``merge`` and
``override`` stay unconstructible rather than merely unused, and proves an
unsupported collision surfaces as the stable structured failure a downstream
client is documented to expect.
"""

from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath

import pytest
from pydantic import ValidationError

import forge_template.engine as engine_module
from forge_template import (
    EngineErrorCode,
    ForgeEngineError,
    FoundationOwner,
    parse_project_spec,
    plan_generation,
)
from forge_template.component_manifest import Contribution, load_component_manifest
from forge_template.file_conflicts import (
    FILE_DISPOSITIONS,
    GRANTED_DISPOSITIONS,
    OutputContribution,
    output_target,
)
from forge_template.foundation_source import load_foundation_source

_ROOT = Path(__file__).parents[1] / "src" / "forge_template"
_FOUNDATION_TOML = _ROOT / "foundation" / "foundation.toml"
_COMPONENTS = _ROOT / "components"

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"
INVALID_FIXTURES = Path(__file__).parent / "fixtures" / "invalid_components"


def _production_payload(archetype: str) -> dict[str, object]:
    component_options: dict[str, object] = {}
    if archetype == "library":
        component_options = {
            "library": {
                "packaging_mode": "uv-build-static",
                "initial_version": "0.1.0",
            }
        }
    return {
        "protocol_version": 1,
        "project": {
            "name": "Extension Point Fixture",
            "package_name": "extension_point_fixture",
            "repository_name": "extension-point-fixture",
            "description": "FT-09.02 extension-point contract fixture.",
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


def _fixture_payload(*, capabilities: tuple[str, ...]) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Example Project",
            "package_name": "example_project",
            "repository_name": "example-project",
            "licence": "mit",
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": "library",
            "capabilities": capabilities,
            "platforms": [],
        },
        "component_options": {"library": {"build_backend": "uv_build"}},
    }


def test_published_extension_point_inventory_matches_the_contract() -> None:
    """docs/extension-points.md's inventory table, executable."""
    foundation = load_foundation_source(_FOUNDATION_TOML)
    published = {(point.id, point.content) for point in foundation.extension_points}

    assert published == {
        ("pyproject-build-system", "content/pyproject.toml.jinja"),
        ("pyproject-archetype-metadata", "content/pyproject.toml.jinja"),
        ("pyproject-build-configuration", "content/pyproject.toml.jinja"),
        ("pyproject-runtime-dependencies", "content/pyproject.toml.jinja"),
        ("pyproject-classifiers", "content/pyproject.toml.jinja"),
        ("pyproject-entry-points", "content/pyproject.toml.jinja"),
        ("readme-project-shape", "content/README.md.jinja"),
        ("gitignore-project-shape", "content/.gitignore.jinja"),
    }

    # Neither production archetype publishes an extension point of its own --
    # both only contribute into Foundation's.
    for archetype in ("library", "cli"):
        manifest = load_component_manifest(_COMPONENTS / archetype / "component.toml")
        assert manifest.extension_points == ()


def test_foundation_files_without_extension_points_stay_create_only() -> None:
    """The six Foundation files the contract names as non-extensible really
    publish no point -- stated, not merely absent by omission."""
    foundation = load_foundation_source(_FOUNDATION_TOML)
    extensible_content = {point.content for point in foundation.extension_points}

    foundation_root = _FOUNDATION_TOML.parent
    all_content = {
        str(path.relative_to(foundation_root)).replace("\\", "/")
        for path in (foundation_root / foundation.content_root).rglob("*")
        if path.is_file()
    }

    assert sorted(all_content - extensible_content) == [
        "content/.editorconfig",
        "content/.gitattributes",
        "content/.python-version.jinja",
        "content/CONTRIBUTING.md.jinja",
        "content/LICENSE.jinja",
        "content/SECURITY.md.jinja",
    ]


def test_only_create_and_extend_dispositions_are_granted() -> None:
    """``merge``/``override`` stay classified for precision but are never
    constructible -- the denial is a type-level guarantee, not just policy."""
    assert GRANTED_DISPOSITIONS == ("create", "extend")
    assert FILE_DISPOSITIONS == ("create", "extend", "merge", "override")

    ungranted = set(FILE_DISPOSITIONS) - set(GRANTED_DISPOSITIONS)
    assert ungranted == {"merge", "override"}

    for disposition in sorted(ungranted):
        with pytest.raises(ValidationError):
            OutputContribution(
                owner=FoundationOwner(),
                disposition=disposition,  # type: ignore[arg-type]
                source_path="content/example.txt",
            )


def test_manifest_rejects_a_disposition_grant_field() -> None:
    """No manifest field lets a component request 'override' -- the strict
    schema has no disposition key to misuse in the first place."""
    with pytest.raises(ValidationError):
        Contribution.model_validate(
            {
                "target": {"kind": "foundation"},
                "extension_point": "pyproject-build-system",
                "content": "extensions/build-system.toml.jinja",
                "disposition": "override",
            }
        )


def test_production_contributions_reach_the_public_plan_as_extensions() -> None:
    """The granted ``extend`` mechanism actually functions for real
    production content: each archetype's contributions surface as
    ``PlannedExtension`` entries on the Foundation-owned target its
    published point lives in."""
    foundation = load_foundation_source(_FOUNDATION_TOML)
    content_root = PurePosixPath(foundation.content_root)
    point_target = {
        point.id: output_target(
            PurePosixPath(point.content).relative_to(content_root).as_posix()
        )
        for point in foundation.extension_points
    }

    for archetype in ("library", "cli"):
        manifest = load_component_manifest(_COMPONENTS / archetype / "component.toml")
        expected: dict[str, set[str]] = {}
        for contribution in manifest.contributions:
            target = point_target[contribution.extension_point]
            expected.setdefault(target, set()).add(contribution.extension_point)
        assert expected, f"{archetype} contributes to no Foundation extension point"

        spec = parse_project_spec(_production_payload(archetype))
        plan = plan_generation(spec)
        by_target = {item.target: item for item in plan.files}

        for target, extension_point_ids in expected.items():
            planned = by_target[target]
            assert isinstance(planned.owner, FoundationOwner)
            actual = {
                extension.extension_point
                for extension in planned.extensions
                if extension.component_id == archetype
            }
            assert actual == extension_point_ids


def test_unsupported_override_fails_as_a_structured_engine_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one collision a valid catalogue can still produce at selection
    time -- two independently valid components both creating the same
    target -- surfaces as the documented structured failure, not a bare
    ``ValueError`` and not a silent override."""
    root = tmp_path / "components"
    shutil.copytree(FIXTURES, root)
    shutil.copytree(INVALID_FIXTURES / "colliding-first", root / "colliding-first")
    shutil.copytree(INVALID_FIXTURES / "colliding-second", root / "colliding-second")
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", root)
    # These fixtures predate FT-08.02 and target no Foundation source; a
    # missing Foundation source here resolves to "none available", the same
    # isolation `tests/test_engine.py`'s `fixture_catalogue` fixture relies on.
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", root)

    spec = parse_project_spec(
        _fixture_payload(capabilities=("colliding-first", "colliding-second"))
    )

    with pytest.raises(ForgeEngineError) as exc_info:
        plan_generation(spec)

    error = exc_info.value
    assert error.code is EngineErrorCode.GENERATION_PLAN_FAILED
    assert error.operation == "plan"
    assert error.details
    message = error.details[0].message
    assert "colliding-first" in message
    assert "colliding-second" in message
    assert "shared.txt" in message
