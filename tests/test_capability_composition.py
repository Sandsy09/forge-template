"""Executable acceptance criteria for FT-11.04 / ADR 0052.

FT-11.02 and FT-11.03 each proved *one* production capability in isolation
(``tests/test_jupyter_capability.py``,
``tests/test_scientific_python_capability.py``). This module proves the
*layer*: that ``jupyter`` and ``scientific-python`` compose across both
production archetypes, that every invalid selection
``docs/data-science-compatibility-and-acceptance.md`` fixes fails closed
through a stable structured engine error *before* any content renders, that
discovery descriptors stay path-free, that Foundation stayed neutral once two
domain capabilities landed on it, and that every manifest-declared resource is
packaged.

Three synthetic capabilities under ``tests/fixtures/capability_composition/``
exercise the ``requires``, ``conflicts``, and options paths the production
catalogue cannot reach -- all four shipped components declare
``requires = []``, ``conflicts = []``, and only ``library`` carries an
``options_schema``. They overlay a copy of the *real* production catalogue
with the *real* Foundation source still live; see
``docs/capability-composition-validation.md``.
"""

from __future__ import annotations

import json
import shutil
import tomllib
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import forge_template.engine as engine_module
from forge_template import (
    ComponentOwner,
    EngineErrorCode,
    ForgeEngineError,
    FoundationOwner,
    GenerationPlan,
    RenderedProject,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)
from forge_template.component_manifest import load_component_manifest
from forge_template.foundation_source import load_foundation_source

_SRC = Path(__file__).parents[1] / "src" / "forge_template"
_PRODUCTION_COMPONENTS = _SRC / "components"
_PRODUCTION_FOUNDATION = _SRC / "foundation"
_SYNTHETIC_FIXTURES = Path(__file__).parent / "fixtures" / "capability_composition"

_SYNTHETIC = ("conflicts-jupyter", "optioned-tooling", "requires-jupyter")
_PRODUCTION_CAPABILITIES = ("jupyter", "scientific-python")
_CAPABILITY_OWNED_TARGET = {
    "jupyter": "scripts/check_notebooks.py",
    "scientific-python": "tests/test_scientific_python.py",
}
_DESCRIPTOR_FIELDS = {
    "id",
    "name",
    "description",
    "kind",
    "version",
    "projectspec_protocols",
    "requires_python",
    "requires",
    "conflicts",
    "options",
}
_NEUTRALITY_TOKENS = (
    "jupyter",
    "ipynb",
    "notebook",
    "numpy",
    "pandas",
    "matplotlib",
    "scikit-learn",
    "sklearn",
    "scientific-python",
)

# Foundation must also never name an archetype-only domain path, framework,
# provider, or client. Generic architecture terms such as "archetype" and
# "capability" remain valid in source comments and neutral generated guidance.
_FOUNDATION_EXCLUDED_TOKENS = (
    *_NEUTRALITY_TOKENS,
    "data-science",
    "data science",
    "/data/raw/",
    "/data/interim/",
    "/data/processed/",
    "/models/",
    "/artifacts/",
    "typer",
    "django",
    "fastapi",
    "flask",
    "github actions",
    "gitlab ci",
    "create-forge",
    "copier",
)


def _payload(
    *,
    archetype: str = "library",
    capabilities: tuple[str, ...] = (),
    component_options: dict[str, dict[str, Any]] | None = None,
) -> dict[str, object]:
    options: dict[str, Any] = dict(component_options or {})
    if archetype == "library" and "library" not in options:
        options["library"] = {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        }
    return {
        "protocol_version": 1,
        "project": {
            "name": "Capability Composition Fixture",
            "package_name": "capability_composition_fixture",
            "repository_name": "capability-composition-fixture",
            "description": "FT-11.04 capability composition fixture.",
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


def _plan(payload: dict[str, object]) -> GenerationPlan:
    return plan_generation(parse_project_spec(payload))


def _render(payload: dict[str, object]) -> RenderedProject:
    return render_project(parse_project_spec(payload))


def _files(project: RenderedProject) -> dict[str, bytes]:
    return {item.target: item.content for item in project.files}


@pytest.fixture
def overlaid_catalogue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The real production catalogue plus the three synthetic capabilities.

    Only ``_CATALOGUE_ROOT_OVERRIDE`` moves: the installed Foundation source,
    with its real FT-11.01 extension points, stays live so this exercises the
    shipped composition surface rather than a fixture copy of it.
    """
    root = tmp_path / "components"
    shutil.copytree(_PRODUCTION_COMPONENTS, root)
    for capability in _SYNTHETIC:
        shutil.copytree(_SYNTHETIC_FIXTURES / capability, root / capability)
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", root)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", None)
    return root


# --- AC1: every claimed composition renders --------------------------------

_COMPOSITIONS = [
    (archetype, capabilities)
    for archetype in ("library", "cli")
    for capabilities in (
        (),
        ("jupyter",),
        ("scientific-python",),
        ("jupyter", "scientific-python"),
    )
]


@pytest.mark.parametrize(("archetype", "capabilities"), _COMPOSITIONS)
def test_every_claimed_composition_plans_and_renders(
    archetype: str, capabilities: tuple[str, ...]
) -> None:
    payload = _payload(archetype=archetype, capabilities=capabilities)
    plan = _plan(payload)

    assert plan.component_order == (archetype, *sorted(capabilities))

    selected = {archetype, *capabilities}
    for planned in plan.files:
        assert isinstance(planned.owner, FoundationOwner) or (
            isinstance(planned.owner, ComponentOwner) and planned.owner.id in selected
        )

    files = _files(_render(payload))
    tomllib.loads(files["pyproject.toml"].decode())

    for capability, target in _CAPABILITY_OWNED_TARGET.items():
        assert (target in files) is (capability in capabilities)


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_both_capabilities_compose_in_composition_order(archetype: str) -> None:
    files = _files(
        _render(_payload(archetype=archetype, capabilities=_PRODUCTION_CAPABILITIES))
    )

    for content in files.values():
        assert b"forge:extension" not in content

    readme = files["README.md"].decode()
    assert readme.index("## Notebooks") < readme.index("## Scientific Python")

    pyproject = tomllib.loads(files["pyproject.toml"].decode())
    dependencies = pyproject["project"]["dependencies"]
    scientific = [
        "numpy>=2.4,<2.5",
        "pandas>=3.0,<4",
        "matplotlib>=3.11,<4",
        "scikit-learn>=1.9,<2",
    ]
    archetype_runtime = [] if archetype == "library" else ["typer>=0.27,<1"]
    assert dependencies == [*archetype_runtime, *scientific]

    check = pyproject["tool"]["poe"]["tasks"]["check"]
    assert check[-1] == "notebook:check"
    assert check[:5] == ["lock:check", "format:check", "lint", "typecheck", "test"]


@pytest.mark.parametrize(("archetype", "capabilities"), _COMPOSITIONS)
def test_rendering_is_deterministic_under_repetition_and_reordering(
    archetype: str, capabilities: tuple[str, ...]
) -> None:
    first = _files(_render(_payload(archetype=archetype, capabilities=capabilities)))
    again = _files(_render(_payload(archetype=archetype, capabilities=capabilities)))
    reversed_order = _files(
        _render(
            _payload(archetype=archetype, capabilities=tuple(reversed(capabilities)))
        )
    )

    assert first == again == reversed_order


# --- AC2: invalid selections fail closed before rendering ------------------

_INVALID_SELECTIONS: list[tuple[str, dict[str, Any], EngineErrorCode, str]] = [
    (
        "duplicate-capability",
        {"capabilities": ("jupyter", "jupyter")},
        EngineErrorCode.INVALID_PROJECT_SPEC,
        "parse",
    ),
    (
        "component-under-two-kinds",
        {"capabilities": ("library",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "capability-as-archetype",
        {"archetype": "jupyter"},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "archetype-as-capability",
        {"capabilities": ("cli",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "unknown-component",
        {"capabilities": ("does-not-exist",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "unsatisfied-requires",
        {"capabilities": ("requires-jupyter",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "declared-conflict",
        {"capabilities": ("conflicts-jupyter", "jupyter")},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "options-for-optionless-component",
        {
            "capabilities": ("jupyter",),
            "component_options": {"jupyter": {"timeout": 1}},
        },
        EngineErrorCode.INVALID_COMPONENT_OPTIONS,
        "validate",
    ),
    (
        "missing-required-option",
        {"capabilities": ("optioned-tooling",)},
        EngineErrorCode.INVALID_COMPONENT_OPTIONS,
        "validate",
    ),
    (
        "option-value-not-among-choices",
        {
            "capabilities": ("optioned-tooling",),
            "component_options": {"optioned-tooling": {"label": "x", "mode": "bogus"}},
        },
        EngineErrorCode.INVALID_COMPONENT_OPTIONS,
        "validate",
    ),
    (
        "option-value-wrong-type",
        {
            "capabilities": ("optioned-tooling",),
            "component_options": {"optioned-tooling": {"label": 123}},
        },
        EngineErrorCode.INVALID_COMPONENT_OPTIONS,
        "validate",
    ),
]


def _drive(kwargs: dict[str, Any], sink: Callable[[Any], object]) -> ForgeEngineError:
    with pytest.raises(ForgeEngineError) as exc_info:
        sink(parse_project_spec(_payload(**kwargs)))
    return exc_info.value


@pytest.mark.parametrize(
    ("name", "kwargs", "code", "operation"),
    _INVALID_SELECTIONS,
    ids=[row[0] for row in _INVALID_SELECTIONS],
)
def test_invalid_selection_fails_closed_before_rendering(
    overlaid_catalogue: Path,
    name: str,
    kwargs: dict[str, Any],
    code: EngineErrorCode,
    operation: str,
) -> None:
    planned = _drive(kwargs, plan_generation)
    assert planned.code is code
    assert planned.operation == operation
    assert planned.details
    json.dumps(planned.as_dict())  # structured and serialisable for a client

    # render_project must raise the same failure, never reach "render".
    rendered = _drive(kwargs, render_project)
    assert rendered.code is code
    assert rendered.operation == operation
    assert rendered.operation != "render"


def test_satisfied_requires_edge_composes(overlaid_catalogue: Path) -> None:
    plan = _plan(_payload(capabilities=("requires-jupyter", "jupyter")))
    assert plan.component_order == ("library", "jupyter", "requires-jupyter")
    assert "scripts/check_notebooks.py" in _files(
        _render(_payload(capabilities=("requires-jupyter", "jupyter")))
    )


def test_valid_capability_options_reach_output(overlaid_catalogue: Path) -> None:
    payload = _payload(
        capabilities=("optioned-tooling",),
        component_options={"optioned-tooling": {"label": "release", "mode": "full"}},
    )
    pyproject = _files(_render(payload))["pyproject.toml"].decode()
    tasks = tomllib.loads(pyproject)["tool"]["poe"]["tasks"]
    assert tasks["optioned:label"] == "release"
    assert tasks["optioned:mode"] == "full"


# --- AC3: discovery descriptors are path-free -----------------------------


def test_production_descriptors_are_immutable_and_path_free() -> None:
    descriptors = {d.id: d for d in discover_components()}
    assert set(descriptors) == {
        "cli",
        "data-science",
        "jupyter",
        "library",
        "scientific-python",
    }

    for descriptor in descriptors.values():
        assert set(descriptor.model_dump()) == _DESCRIPTOR_FIELDS
        serialised = descriptor.model_dump_json()
        for leak in (
            "content_root",
            "options_schema",
            "extensions/",
            "content/",
            "component.toml",
            "src/forge_template",
            "\\\\",
            "//",
        ):
            assert leak not in serialised
        with pytest.raises(ValidationError):
            descriptor.name = "changed"

    assert discover_components() == discover_components()
    assert [d.id for d in discover_components()] == sorted(descriptors)


# --- AC4: Foundation neutral, generated projects free of Forge ------------


def test_foundation_source_names_no_capability_or_domain_tool() -> None:
    for path in _PRODUCTION_FOUNDATION.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        haystack = path.read_bytes().lower()
        for token in _FOUNDATION_EXCLUDED_TOKENS:
            assert token.encode() not in haystack, f"{token!r} leaked into {path}"


@pytest.mark.parametrize("archetype", ["library", "cli"])
def test_capability_free_render_is_domain_neutral(archetype: str) -> None:
    for content in _files(_render(_payload(archetype=archetype))).values():
        haystack = content.lower()
        for token in _NEUTRALITY_TOKENS:
            assert token.encode() not in haystack


@pytest.mark.parametrize(("archetype", "capabilities"), _COMPOSITIONS)
def test_no_composition_depends_on_a_forge_package(
    archetype: str, capabilities: tuple[str, ...]
) -> None:
    files = _files(_render(_payload(archetype=archetype, capabilities=capabilities)))
    pyproject = tomllib.loads(files["pyproject.toml"].decode())

    declared = [
        *pyproject["project"].get("dependencies", []),
        *(
            requirement
            for group in pyproject.get("dependency-groups", {}).values()
            for requirement in group
            if isinstance(requirement, str)
        ),
    ]
    assert all(
        not requirement.lower().startswith(("forge-template", "create-forge"))
        for requirement in declared
    )
    for target, content in files.items():
        if target.endswith(".py"):
            assert b"import forge_template" not in content


# --- Scope: every manifest-declared resource is packaged -----------------


def test_every_manifest_declared_resource_is_reachable_as_a_package_resource() -> None:
    components_root = resources.files("forge_template.components")
    foundation_root = resources.files("forge_template.foundation")

    foundation_manifest = foundation_root / "foundation.toml"
    assert foundation_manifest.is_file()
    foundation = load_foundation_source(_PRODUCTION_FOUNDATION / "foundation.toml")
    for point in foundation.extension_points:
        assert (foundation_root / point.content).is_file(), point.content

    seen_ids: set[str] = set()
    for child in components_root.iterdir():
        manifest_resource = child / "component.toml"
        if not manifest_resource.is_file():
            continue
        component_id = child.name
        seen_ids.add(component_id)

        manifest = load_component_manifest(
            _PRODUCTION_COMPONENTS / component_id / "component.toml"
        )
        assert manifest.id == component_id

        # load_component_manifest already proved the content tree is a
        # non-empty directory on disk; this asserts the same tree, and every
        # individually declared resource, is reachable as a package resource.
        assert (child / manifest.content_root).is_dir()

        if manifest.options_schema is not None:
            assert (child / manifest.options_schema).is_file(), manifest.options_schema
        for point in manifest.extension_points:
            assert (child / point.content).is_file(), point.content
        for contribution in manifest.contributions:
            assert (child / contribution.content).is_file(), contribution.content

    assert seen_ids == {
        "cli",
        "data-science",
        "jupyter",
        "library",
        "scientific-python",
    }
