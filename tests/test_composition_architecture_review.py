"""Executable findings from the Stage 08 and Stage 14 composition reviews."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from forge_template import (
    ComponentOwner,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)
from forge_template.component_manifest import load_component_manifest

_COMPONENTS = Path(__file__).parents[1] / "src" / "forge_template" / "components"

_VALID_COMPOSITIONS = (
    *(
        (archetype, capabilities)
        for archetype in ("library", "cli")
        for capabilities in (
            (),
            ("jupyter",),
            ("scientific-python",),
            ("jupyter", "scientific-python"),
        )
    ),
    ("data-science", ("jupyter",)),
    ("data-science", ("jupyter", "scientific-python")),
)

_DUPLICATE_RESOURCE_GROUPS = (
    (
        ("library", "cli", "data-science"),
        "content/src/{{project.package_name}}/__init__.py.jinja",
    ),
    (
        ("library", "cli", "data-science"),
        "content/src/{{project.package_name}}/py.typed",
    ),
    (("library", "cli", "data-science"), "content/tests/__init__.py"),
    (("library", "data-science"), "content/tests/test_smoke.py.jinja"),
    (("cli", "data-science"), "extensions/archetype-metadata.toml.jinja"),
    (("cli", "data-science"), "extensions/build-configuration.toml.jinja"),
    (("cli", "data-science"), "extensions/build-system.toml.jinja"),
)

_DUPLICATE_CONTENT_TARGETS = {
    "content/src/{{project.package_name}}/__init__.py.jinja": (
        "src/reference_project/__init__.py"
    ),
    "content/src/{{project.package_name}}/py.typed": "src/reference_project/py.typed",
    "content/tests/__init__.py": "tests/__init__.py",
    "content/tests/test_smoke.py.jinja": "tests/test_smoke.py",
}

# ADR 0056's package-size review measurement, pinned executably by FT-14.02
# (docs/cross-repository-validation.md). "The package" here means Foundation
# plus every catalogue component's tree -- not the built wheel, whose zip
# metadata (timestamps, compression) is not byte-reproducible across
# machines; `scripts/check_wheel.py` ceilings that separately.
_FOUNDATION_ROOT = Path(__file__).parents[1] / "src" / "forge_template" / "foundation"
_OWNED_COMPONENTS = ("cli", "data-science", "jupyter", "library", "scientific-python")
_EXPECTED_CONTENT_FILE_COUNT = 60
_EXPECTED_CONTENT_BYTES = 39_182
_EXPECTED_DUPLICATE_OVERHEAD_BYTES = 892


def _payload(
    archetype: str, capabilities: tuple[str, ...] | None = None
) -> dict[str, object]:
    component_options: dict[str, object] = {}
    if archetype == "library":
        component_options = {
            "library": {
                "packaging_mode": "uv-build-static",
                "initial_version": "0.1.0",
            }
        }
    selected_capabilities: tuple[str, ...] = (
        ("jupyter",) if capabilities is None and archetype == "data-science" else ()
    )
    if capabilities is not None:
        selected_capabilities = capabilities

    return {
        "protocol_version": 1,
        "project": {
            "name": "Reference Project",
            "package_name": "reference_project",
            "repository_name": "reference-project",
            "description": "Composition architecture review fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": list(selected_capabilities),
            "platforms": [],
        },
        "component_options": component_options,
    }


def _rendered_files(
    archetype: str, capabilities: tuple[str, ...] | None = None
) -> dict[str, bytes]:
    spec = parse_project_spec(_payload(archetype, capabilities))
    return {item.target: item.content for item in render_project(spec).files}


def test_independent_archetypes_keep_coincidentally_shared_files_owned() -> None:
    for owners, relative in _DUPLICATE_RESOURCE_GROUPS:
        contents = {(_COMPONENTS / owner / relative).read_bytes() for owner in owners}
        assert len(contents) == 1, (owners, relative)

        if target := _DUPLICATE_CONTENT_TARGETS.get(relative):
            for owner in owners:
                plan = plan_generation(parse_project_spec(_payload(owner)))
                planned = next(item for item in plan.files if item.target == target)
                assert planned.owner == ComponentOwner(id=owner)
        else:
            for owner in owners:
                manifest = load_component_manifest(
                    _COMPONENTS / owner / "component.toml"
                )
                contribution = next(
                    item for item in manifest.contributions if item.content == relative
                )
                assert contribution.target.model_dump() == {"kind": "foundation"}

    for archetype in ("library", "cli", "data-science"):
        descriptor = next(d for d in discover_components() if d.id == archetype)
        assert descriptor.conflicts == ()

        requirements = tuple(
            (requirement.id, str(requirement.version))
            for requirement in descriptor.requires
        )
        expected = (("jupyter", "<2,>=1"),) if archetype == "data-science" else ()
        assert requirements == expected


def test_package_content_size_matches_the_recorded_review_baseline() -> None:
    """Pins ADR 0056's 2026-09-04 review measurement: Foundation plus every
    catalogue component's tree total 60 files and 39,182 raw bytes, of which
    892 bytes are the seven duplicate groups' overhead
    (docs/composition-architecture-review.md, "Operational consequences").
    Content only -- `__pycache__` is excluded, matching how the review byte
    count was taken. A deliberate content change should move this pin and
    the prose figures together, per FT-14.02's cross-repository record.
    """
    trees = (_FOUNDATION_ROOT, *(_COMPONENTS / owner for owner in _OWNED_COMPONENTS))
    files = [
        path
        for tree in trees
        for path in tree.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ]
    assert len(files) == _EXPECTED_CONTENT_FILE_COUNT, sorted(
        str(f.relative_to(_COMPONENTS.parent)) for f in files
    )
    assert sum(f.stat().st_size for f in files) == _EXPECTED_CONTENT_BYTES

    overhead = sum(
        (len(owners) - 1) * (_COMPONENTS / owners[0] / relative).stat().st_size
        for owners, relative in _DUPLICATE_RESOURCE_GROUPS
    )
    assert overhead == _EXPECTED_DUPLICATE_OVERHEAD_BYTES


@pytest.mark.parametrize(
    ("archetype", "capabilities"),
    _VALID_COMPOSITIONS,
    ids=(
        f"{archetype}-{'+'.join(capabilities) or 'none'}"
        for archetype, capabilities in _VALID_COMPOSITIONS
    ),
)
def test_every_valid_composition_plans_and_renders_deterministically(
    archetype: str, capabilities: tuple[str, ...]
) -> None:
    payload = _payload(archetype, capabilities)
    reordered = _payload(archetype, tuple(reversed(capabilities)))

    first_plan = plan_generation(parse_project_spec(payload))
    assert first_plan == plan_generation(parse_project_spec(payload))
    assert first_plan == plan_generation(parse_project_spec(reordered))
    assert first_plan.component_order == (archetype, *sorted(capabilities))

    first_render = render_project(parse_project_spec(payload))
    assert first_render == render_project(parse_project_spec(payload))
    assert first_render == render_project(parse_project_spec(reordered))


@pytest.mark.parametrize("archetype", ["library", "cli", "data-science"])
def test_foundation_quality_configuration_is_layout_neutral(archetype: str) -> None:
    payload = tomllib.loads(_rendered_files(archetype)["pyproject.toml"].decode())

    assert "src" not in payload["tool"]["ruff"]
    assert "files" not in payload["tool"]["mypy"]
    assert "overrides" not in payload["tool"]["mypy"]
    assert "testpaths" not in payload["tool"]["pytest"]["ini_options"]
    assert payload["tool"]["poe"]["tasks"]["typecheck"] == "mypy ."


@pytest.mark.parametrize("archetype", ["library", "cli", "data-science"])
def test_foundation_excludes_optional_coverage_and_pre_commit(
    archetype: str,
) -> None:
    files = _rendered_files(archetype)
    payload = tomllib.loads(files["pyproject.toml"].decode())

    dependency_groups = payload["dependency-groups"]
    assert all(
        not requirement.startswith(("pre-commit", "pytest-cov"))
        for requirements in dependency_groups.values()
        for requirement in requirements
        if isinstance(requirement, str)
    )
    assert "coverage" not in payload["tool"]
    assert not any(
        option.startswith("--cov")
        for option in payload["tool"]["pytest"]["ini_options"]["addopts"]
    )
    assert b"pre-commit install" not in files["README.md"]
    assert b"pre-commit install" not in files["CONTRIBUTING.md"]
    assert (
        b"Foundation does not install a\n`detect-private-key` hook"
        in files["SECURITY.md"]
    )


def test_archetypes_own_their_typed_distribution_classifiers() -> None:
    library = tomllib.loads(_rendered_files("library")["pyproject.toml"].decode())
    cli = tomllib.loads(_rendered_files("cli")["pyproject.toml"].decode())
    data_science = tomllib.loads(
        _rendered_files("data-science")["pyproject.toml"].decode()
    )

    assert library["project"]["classifiers"] == ["Typing :: Typed"]
    assert cli["project"]["classifiers"] == [
        "Typing :: Typed",
        "Environment :: Console",
    ]
    assert data_science["project"]["classifiers"] == [
        "Typing :: Typed",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
    ]


@pytest.mark.parametrize("archetype", ["library", "cli", "data-science"])
def test_foundation_exposes_the_locked_aggregate_quality_contract(
    archetype: str,
) -> None:
    files = _rendered_files(archetype)
    payload = tomllib.loads(files["pyproject.toml"].decode())
    tasks = payload["tool"]["poe"]["tasks"]

    assert tasks["lock:check"] == "uv lock --check"
    assert tasks["check"][0] == "lock:check"
    assert b"uv sync --all-groups --locked" in files["README.md"]
    assert b"uv run --locked poe check" in files["README.md"]
    assert b"uv run --locked poe check" in files["CONTRIBUTING.md"]
