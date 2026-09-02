"""Fast render-level tests for the production Data Science archetype.

Real ``uv build``/wheel/install/import checks live in the slow
``archetype``-marked ``tests/test_data_science_build.py`` instead -- see
docs/data-science-archetype.md.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

from forge_template import (
    ComponentOwner,
    EngineErrorCode,
    ForgeEngineError,
    FoundationOwner,
    discover_components,
    parse_project_spec,
    plan_generation,
    render_project,
)

_COMPONENTS = Path(__file__).parents[1] / "src" / "forge_template" / "components"
_DATA_SCIENCE = _COMPONENTS / "data-science"


def _payload(
    *,
    capabilities: list[str] | None = None,
    component_options: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Churn Model",
            "package_name": "churn_model",
            "repository_name": "churn-model",
            "description": "Churn prediction work.",
            "licence": "mit",
            "authors": [{"name": "Test User", "email": "test@example.invalid"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": "data-science",
            "capabilities": ["jupyter"] if capabilities is None else capabilities,
            "platforms": [],
        },
        "component_options": component_options or {},
    }


def test_discovery_exposes_data_science_between_cli_and_jupyter() -> None:
    descriptors = discover_components()

    assert [descriptor.id for descriptor in descriptors] == [
        "cli",
        "data-science",
        "jupyter",
        "library",
        "scientific-python",
    ]

    data_science = descriptors[1]
    assert data_science.kind == "archetype"
    assert data_science.version == "1.0.0"
    assert data_science.requires_python == ">=3.11"
    assert data_science.options == ()
    assert data_science.conflicts == ()

    assert len(data_science.requires) == 1
    (jupyter_edge,) = data_science.requires
    assert jupyter_edge.id == "jupyter"
    # The manifest declares ">=1,<2"; the loader stores the canonical form.
    assert jupyter_edge.version == "<2,>=1"


def test_plan_identifies_foundation_component_and_capability_owners() -> None:
    spec = parse_project_spec(_payload())

    plan = plan_generation(spec)

    assert plan.component_order == ("data-science", "jupyter")
    by_target = {item.target: item for item in plan.files}

    for foundation_target in (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
        ".python-version",
    ):
        assert by_target[foundation_target].owner == FoundationOwner()

    for owned_target in (
        "src/churn_model/__init__.py",
        "src/churn_model/py.typed",
        "tests/__init__.py",
        "tests/test_smoke.py",
        "notebooks/getting-started.ipynb",
    ):
        assert by_target[owned_target].owner == ComponentOwner(id="data-science")

    assert by_target["scripts/check_notebooks.py"].owner == ComponentOwner(id="jupyter")

    # The archetype contributes the project-shape guidance and the working-tree
    # ignore entries through Foundation's existing reviewed extension points.
    for mixed_target in ("README.md", ".gitignore"):
        owners = {
            extension.component_id for extension in by_target[mixed_target].extensions
        }
        assert "data-science" in owners

    extensions = by_target["pyproject.toml"].extensions
    by_point = {extension.extension_point: extension for extension in extensions}
    assert {
        point
        for point, extension in by_point.items()
        if extension.component_id == "data-science"
    } == {
        "pyproject-build-system",
        "pyproject-archetype-metadata",
        "pyproject-build-configuration",
        "pyproject-classifiers",
    }
    assert {
        point
        for point, extension in by_point.items()
        if extension.component_id == "jupyter"
    } == {
        "pyproject-development-dependencies",
        "pyproject-task-definitions",
        "pyproject-aggregate-check",
    }


def test_rendered_pyproject_matches_the_data_science_contract() -> None:
    spec = parse_project_spec(_payload())

    rendered = render_project(spec)
    files = {item.target: item.content for item in rendered.files}

    payload = tomllib.loads(files["pyproject.toml"].decode())
    assert payload["project"]["name"] == "churn-model"
    assert payload["project"]["version"] == "0.1.0"
    assert payload["project"]["requires-python"] == ">=3.11"
    assert payload["project"]["license"] == "MIT"
    assert payload["project"]["dependencies"] == []
    assert "scripts" not in payload["project"]
    assert payload["project"]["classifiers"] == [
        "Typing :: Typed",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
    ]
    assert payload["build-system"]["build-backend"] == "uv_build"
    assert payload["build-system"]["requires"] == ["uv_build>=0.12,<0.13"]
    assert payload["tool"]["uv"]["build-backend"]["module-name"] == "churn_model"


def test_composed_file_set_is_the_package_and_notebook_tooling_shape() -> None:
    spec = parse_project_spec(_payload())

    rendered = render_project(spec)
    targets = {item.target for item in rendered.files}

    assert targets == {
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
        ".python-version",
        "src/churn_model/__init__.py",
        "src/churn_model/py.typed",
        "tests/__init__.py",
        "tests/test_smoke.py",
        "notebooks/getting-started.ipynb",
        "scripts/check_notebooks.py",
    }
    # The working trees carry no tracked placeholder -- ADR 0045/0047. A clean
    # checkout does not contain data/, models/, or artifacts/ until a user or
    # selected component creates them.
    for reserved in ("data/", "models/", "artifacts/"):
        assert not any(target.startswith(reserved) for target in targets)
    assert not any(target.endswith(".gitkeep") for target in targets)


def test_generated_package_source_resolves_version_from_metadata() -> None:
    spec = parse_project_spec(_payload())

    rendered = render_project(spec)
    files = {item.target: item.content.decode() for item in rendered.files}

    init = files["src/churn_model/__init__.py"]
    assert 'version("churn-model")' in init
    assert '__version__ = "0.0.0"' in init
    assert files["src/churn_model/py.typed"] == ""
    assert "from churn_model import __version__" in files["tests/test_smoke.py"]


@pytest.mark.parametrize(
    "capabilities",
    [
        pytest.param([], id="no-jupyter"),
        pytest.param(["scientific-python"], id="scientific-python-only"),
    ],
)
def test_selecting_data_science_without_jupyter_fails_closed(
    capabilities: list[str],
) -> None:
    spec = parse_project_spec(_payload(capabilities=capabilities))

    with pytest.raises(ForgeEngineError) as plan_exc:
        plan_generation(spec)

    error = plan_exc.value
    assert error.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
    assert error.operation == "validate"
    assert error.details
    assert any("jupyter" in detail.message for detail in error.details)
    # Structured and JSON-serialisable for a client to branch on.
    json.dumps(error.as_dict())

    with pytest.raises(ForgeEngineError) as render_exc:
        render_project(spec)

    assert render_exc.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
    assert render_exc.value.operation == "validate"
    assert render_exc.value.operation != "render"


def test_data_science_is_optionless_and_rejects_supplied_options() -> None:
    spec = parse_project_spec(
        _payload(component_options={"data-science": {"anything": "x"}})
    )

    with pytest.raises(ForgeEngineError) as exc_info:
        plan_generation(spec)

    assert exc_info.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS


def test_archetype_inherits_from_no_sibling_and_shares_no_resource() -> None:
    for path in sorted(_DATA_SCIENCE.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\blibrary\b", text), path
        assert not re.search(r"\bcli\b", text), path

    # The three coincidentally-shared package sources are byte-identical to
    # `library`'s copies -- copied, never read across archetypes.
    for relative in (
        "content/src/{{project.package_name}}/__init__.py.jinja",
        "content/src/{{project.package_name}}/py.typed",
        "content/tests/__init__.py",
    ):
        assert (_DATA_SCIENCE / relative).read_bytes() == (
            _COMPONENTS / "library" / relative
        ).read_bytes()

    spec = parse_project_spec(_payload())
    plan = plan_generation(spec)
    by_target = {item.target: item for item in plan.files}
    for owned_target in (
        "src/churn_model/__init__.py",
        "src/churn_model/py.typed",
        "tests/__init__.py",
    ):
        assert by_target[owned_target].owner == ComponentOwner(id="data-science")


def test_data_science_composes_with_optional_scientific_python() -> None:
    spec = parse_project_spec(_payload(capabilities=["jupyter", "scientific-python"]))

    plan = plan_generation(spec)
    assert plan.component_order == (
        "data-science",
        "jupyter",
        "scientific-python",
    )

    rendered = render_project(spec)
    files = {item.target: item.content for item in rendered.files}
    payload = tomllib.loads(files["pyproject.toml"].decode())
    assert payload["project"]["dependencies"] == [
        "numpy>=2.4,<2.5",
        "pandas>=3.0,<4",
        "matplotlib>=3.11,<4",
        "scikit-learn>=1.9,<2",
    ]
    assert "tests/test_scientific_python.py" in files


_WORKING_TREE_IGNORES = (
    "/data/raw/",
    "/data/interim/",
    "/data/processed/",
    "/models/",
    "/artifacts/",
)


def test_every_generated_target_has_an_explicit_owner_in_the_selection() -> None:
    """Acceptance criterion 1: every generated target is owned by Foundation or
    by a component that is actually in the selection -- no orphan output."""
    spec = parse_project_spec(_payload(capabilities=["jupyter", "scientific-python"]))

    plan = plan_generation(spec)
    selected = {"data-science", "jupyter", "scientific-python"}
    for item in plan.files:
        if isinstance(item.owner, FoundationOwner):
            continue
        assert isinstance(item.owner, ComponentOwner)
        assert item.owner.id in selected, item.target

    by_target = {item.target: item for item in plan.files}
    assert by_target["notebooks/getting-started.ipynb"].owner == ComponentOwner(
        id="data-science"
    )


def test_working_trees_are_ignored_while_their_guidance_stays_tracked() -> None:
    """Acceptance criterion 3: the five root-anchored ignore entries land in
    order, shadow no tracked path, and the README documents every tree -- with
    no .gitkeep or per-directory placeholder anywhere in the output."""
    spec = parse_project_spec(_payload())

    rendered = render_project(spec)
    files = {item.target: item.content.decode() for item in rendered.files}

    gitignore_lines = files[".gitignore"].splitlines()
    positions = [gitignore_lines.index(entry) for entry in _WORKING_TREE_IGNORES]
    assert positions == sorted(positions), gitignore_lines
    # Root-anchored, so none can shadow src/<package>/models/ or a tracked
    # root directory -- docs/notebook-data-and-model-safeguards.md.
    for entry in _WORKING_TREE_IGNORES:
        assert entry.startswith("/")
    for tracked in ("notebooks/", "src/", "tests/"):
        assert not any(
            line.rstrip("/") == tracked.rstrip("/") for line in gitignore_lines
        )

    readme = files["README.md"]
    assert "## Working directories" in readme
    for tree in (
        "data/raw/",
        "data/interim/",
        "data/processed/",
        "models/",
        "artifacts/",
    ):
        assert tree in readme

    targets = {item.target for item in rendered.files}
    assert not any(target.endswith(".gitkeep") for target in targets)
    assert not any(
        target.startswith(("data/", "models/", "artifacts/")) for target in targets
    )


@pytest.mark.parametrize("archetype", ["library", "cli"])
@pytest.mark.parametrize(
    "capabilities",
    [[], ["jupyter"], ["jupyter", "scientific-python"]],
)
def test_library_and_cli_render_without_the_data_science_shape(
    archetype: str, capabilities: list[str]
) -> None:
    """Acceptance criterion 5: the Data Science README and ignore contributions
    reach only a Data Science selection -- Library and CLI are untouched."""
    options: dict[str, object] = {}
    if archetype == "library":
        options = {
            "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"}
        }
    payload = {
        "protocol_version": 1,
        "project": {
            "name": "Sibling Project",
            "package_name": "sibling_project",
            "repository_name": "sibling-project",
            "description": "Regression fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": capabilities,
            "platforms": [],
        },
        "component_options": options,
    }

    rendered = render_project(parse_project_spec(payload))
    files = {item.target: item.content.decode() for item in rendered.files}

    for entry in _WORKING_TREE_IGNORES:
        assert entry not in files[".gitignore"]
    assert "## Working directories" not in files["README.md"]
    assert not any(item.target.startswith("notebooks/") for item in rendered.files)
