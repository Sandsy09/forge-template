"""Fast render-level tests for the production Streamlit archetype.

FT-20.01 / ADR 0070. Real ``uv lock``/build/install/``AppTest`` runs across the
accepted selections and Python endpoints belong to FT-20.03; the deferred
contributions (``run``, ``.streamlit/config.toml``, the secrets ignore rule and
the README section) belong to FT-20.02. See docs/streamlit-archetype.md and
docs/streamlit-compatibility-and-acceptance.md.
"""

from __future__ import annotations

import ast
import json
import re
import tomllib
import warnings
from pathlib import Path

import pytest
from pydantic import ValidationError

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
_STREAMLIT = _COMPONENTS / "streamlit"
_SIBLINGS = ("library", "cli", "data-science")

# The contributions FT-20.01 ships; FT-20.02 adds `pyproject-task-definitions`,
# `gitignore-project-shape` and `readme-project-shape`.
_PYPROJECT_POINTS = {
    "pyproject-build-system",
    "pyproject-archetype-metadata",
    "pyproject-build-configuration",
    "pyproject-runtime-dependencies",
    "pyproject-classifiers",
    "pyproject-development-dependencies",
}


def _payload(
    *,
    archetype: str = "streamlit",
    capabilities: list[str] | None = None,
    component_options: dict[str, object] | None = None,
    name: str = "Demo App",
) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": name,
            "package_name": "demo_app",
            "repository_name": "demo-app",
            "description": "A demonstration.",
            "licence": "mit",
            "authors": [{"name": "Test User", "email": "test@example.invalid"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": archetype,
            "capabilities": capabilities or [],
            "platforms": [],
        },
        "component_options": component_options or {},
    }


def _rendered(*, name: str = "Demo App") -> dict[str, str]:
    spec = parse_project_spec(_payload(name=name))
    return {item.target: item.content.decode() for item in render_project(spec).files}


def test_discovery_exposes_streamlit_as_the_lexically_last_archetype() -> None:
    descriptors = discover_components()

    assert [descriptor.id for descriptor in descriptors][-2:] == [
        "scientific-python",
        "streamlit",
    ]
    assert len(descriptors) == 15

    streamlit = next(d for d in descriptors if d.id == "streamlit")
    assert streamlit.name == "Streamlit"
    assert streamlit.kind == "archetype"
    assert streamlit.version == "1.0.0"
    assert streamlit.projectspec_protocols == (1,)
    assert streamlit.requires_python == ">=3.11"
    # The accepted matrix needs no edge of its own: all four capability
    # selections are valid, so the manifest declares none.
    assert streamlit.requires == ()
    assert streamlit.conflicts == ()
    assert streamlit.options == ()


def test_the_descriptor_is_immutable_and_path_free() -> None:
    streamlit = next(d for d in discover_components() if d.id == "streamlit")

    with pytest.raises(ValidationError):
        streamlit.version = "2.0.0"

    payload = json.dumps(streamlit.model_dump(mode="json"))
    for leak in (
        str(_COMPONENTS),
        "content",
        "extensions",
        "component.toml",
        ".jinja",
        "/",
        "\\",
    ):
        assert leak not in payload, leak


def test_plan_identifies_foundation_and_streamlit_owners() -> None:
    plan = plan_generation(parse_project_spec(_payload()))

    assert plan.component_order == ("streamlit",)
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
        "app.py",
        "src/demo_app/__init__.py",
        "src/demo_app/app.py",
        "src/demo_app/py.typed",
        "tests/__init__.py",
        "tests/test_app.py",
    ):
        assert by_target[owned_target].owner == ComponentOwner(id="streamlit")

    by_point = {
        extension.extension_point: extension
        for extension in by_target["pyproject.toml"].extensions
    }
    assert {
        point
        for point, extension in by_point.items()
        if extension.component_id == "streamlit"
    } == _PYPROJECT_POINTS


def test_composed_file_set_is_the_package_launcher_and_tests() -> None:
    targets = set(_rendered())

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
        "app.py",
        "src/demo_app/__init__.py",
        "src/demo_app/app.py",
        "src/demo_app/py.typed",
        "tests/__init__.py",
        "tests/test_app.py",
    }
    # Tracked placeholders and multipage scaffolding are excluded by contract.
    assert not any(target.startswith("pages/") for target in targets)
    assert not any(target.endswith(".gitkeep") for target in targets)


def test_rendered_pyproject_matches_the_streamlit_contract() -> None:
    payload = tomllib.loads(_rendered()["pyproject.toml"])

    project = payload["project"]
    assert project["name"] == "demo-app"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == ["streamlit>=1.63,<2"]
    assert "scripts" not in project
    assert project["classifiers"] == [
        "Typing :: Typed",
        "Environment :: Web Environment",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ]
    assert payload["build-system"] == {
        "requires": ["uv_build>=0.12,<0.13"],
        "build-backend": "uv_build",
    }
    assert payload["tool"]["uv"]["build-backend"] == {
        "module-name": "demo_app",
        "module-root": "src",
    }


def test_numpy_is_capped_for_development_only() -> None:
    """NumPy 2.5's stubs use Python 3.12 syntax that Foundation's mypy, which
    targets the 3.11 floor, cannot parse; the cap must stay out of the wheel
    metadata (ADR 0070)."""
    payload = tomllib.loads(_rendered()["pyproject.toml"])

    dev_group = payload["dependency-groups"]["dev"]
    assert "numpy<2.5" in dev_group
    assert not any("numpy" in item for item in payload["project"]["dependencies"])
    assert "optional-dependencies" not in payload["project"]


def test_the_launcher_is_a_thin_guarded_entry_point() -> None:
    launcher = _rendered()["app.py"]

    tree = ast.parse(launcher)
    (import_node,) = (n for n in tree.body if isinstance(n, ast.ImportFrom))
    assert import_node.module == "demo_app.app"
    assert [alias.name for alias in import_node.names] == ["main"]
    (guard,) = (n for n in tree.body if isinstance(n, ast.If))
    assert ast.unparse(guard.test) == "__name__ == '__main__'"
    # Application code lives in the typed package, not in the launcher.
    assert not any(isinstance(n, ast.FunctionDef) for n in tree.body)


def test_the_package_exports_only_the_version_and_defines_main() -> None:
    files = _rendered()

    init = files["src/demo_app/__init__.py"]
    assert 'version("demo-app")' in init
    assert '__all__ = ["__version__"]' in init
    assert files["src/demo_app/py.typed"] == ""

    tree = ast.parse(files["src/demo_app/app.py"])
    assert [n.name for n in tree.body if isinstance(n, ast.FunctionDef)] == ["main"]
    assert "import streamlit as st" in files["src/demo_app/app.py"]


def test_the_smoke_test_is_in_process_and_bounded() -> None:
    smoke = _rendered()["tests/test_app.py"]

    # A relative path would resolve against tests/, so the launcher is located
    # from __file__ (docs/streamlit-archetype.md, "Tests").
    assert 'Path(__file__).parents[1] / "app.py"' in smoke
    assert "AppTest.from_file(" in smoke
    assert "default_timeout=10" in smoke
    # Non-serving: nothing here may start a server or a subprocess.
    for forbidden in ("subprocess", "streamlit run", "os.system", "socket"):
        assert forbidden not in smoke, forbidden


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("Demo App", id="plain"),
        pytest.param("Ada's Tool", id="apostrophe"),
        pytest.param("Café Explorer", id="accent"),
        pytest.param("日本語 ☃", id="cjk"),
        pytest.param('Say "hi"', id="double-quote"),
        pytest.param("back" + chr(92) + "slash", id="backslash"),
        pytest.param("line1\nline2", id="newline"),
        pytest.param('"""', id="triple-quote"),
        pytest.param("{{ braces }} {% x %}", id="jinja-syntax"),
    ],
)
def test_any_project_name_renders_valid_python_that_round_trips(name: str) -> None:
    """The title is the only place free text reaches a Python literal, so it is
    escaped; the docstrings deliberately carry no name at all. (`ruff format`
    may still re-quote a name containing a double quote -- ADR 0070.)"""
    files = _rendered(name=name)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for target in ("app.py", "src/demo_app/app.py", "tests/test_app.py"):
            compile(files[target], target, "exec")

    tree = ast.parse(files["src/demo_app/app.py"])
    title = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "TITLE"
    )
    assert title == name


def test_rendering_is_deterministic() -> None:
    spec = parse_project_spec(_payload())

    first = {item.target: item.content for item in render_project(spec).files}
    second = {item.target: item.content for item in render_project(spec).files}

    assert first == second


def test_streamlit_is_optionless_and_rejects_supplied_options() -> None:
    spec = parse_project_spec(_payload(component_options={"streamlit": {"x": "y"}}))

    with pytest.raises(ForgeEngineError) as exc_info:
        plan_generation(spec)

    assert exc_info.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS


def test_the_archetype_reads_and_shares_no_sibling_resource() -> None:
    for path in sorted(_STREAMLIT.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for sibling in _SIBLINGS:
            assert not re.search(rf"(?<![\w-]){re.escape(sibling)}(?![\w-])", text), (
                path,
                sibling,
            )

    # Coincidentally identical sources are copied into the archetype's own tree,
    # never read across archetypes.
    for relative, source in (
        ("content/src/{{project.package_name}}/__init__.py.jinja", "library"),
        ("content/src/{{project.package_name}}/py.typed", "library"),
        ("content/tests/__init__.py", "library"),
        ("extensions/archetype-metadata.toml.jinja", "cli"),
        ("extensions/build-configuration.toml.jinja", "cli"),
        ("extensions/build-system.toml.jinja", "cli"),
    ):
        assert (_STREAMLIT / relative).read_bytes() == (
            _COMPONENTS / source / relative
        ).read_bytes(), relative


def test_the_manifest_publishes_no_extension_point_and_targets_foundation() -> None:
    manifest = tomllib.loads((_STREAMLIT / "component.toml").read_text("utf-8"))

    assert "extension_points" not in manifest
    assert "options_schema" not in manifest
    assert "regeneration" not in manifest
    assert "renames" not in manifest
    assert manifest["manifest_version"] == 2
    assert {
        c["extension_point"] for c in manifest["contributions"]
    } == _PYPROJECT_POINTS
    assert all(c["target"] == {"kind": "foundation"} for c in manifest["contributions"])


@pytest.mark.parametrize(
    ("components", "expected"),
    [
        pytest.param(
            {"archetype": "library", "capabilities": ["streamlit"], "platforms": []},
            "as capability, but its manifest kind is archetype",
            id="archetype-as-capability",
        ),
        pytest.param(
            {"archetype": "library", "capabilities": [], "platforms": ["streamlit"]},
            "as platform, but its manifest kind is archetype",
            id="archetype-as-platform",
        ),
        pytest.param(
            {"archetype": "streamlit", "capabilities": ["cli"], "platforms": []},
            "'cli' as capability, but its manifest kind is archetype",
            id="two-archetypes",
        ),
        pytest.param(
            {"archetype": "streamlit", "capabilities": ["streamlit"], "platforms": []},
            "must not select one component under multiple kinds",
            id="archetype-also-capability",
        ),
        pytest.param(
            {"archetype": "streamlit", "capabilities": ["nope"], "platforms": []},
            "unknown component 'nope'",
            id="unknown-component",
        ),
        pytest.param(
            {"archetype": "jupyter", "capabilities": [], "platforms": []},
            "as archetype, but its manifest kind is capability",
            id="capability-as-archetype",
        ),
    ],
)
def test_malformed_selections_fail_closed_before_rendering(
    components: dict[str, object], expected: str
) -> None:
    payload = _payload()
    payload["components"] = components
    spec = parse_project_spec(payload)

    with pytest.raises(ForgeEngineError) as plan_exc:
        plan_generation(spec)

    error = plan_exc.value
    assert error.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
    assert error.operation == "validate"
    assert any(expected in detail.message for detail in error.details)
    json.dumps(error.as_dict())

    with pytest.raises(ForgeEngineError) as render_exc:
        render_project(spec)

    assert render_exc.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
    assert render_exc.value.operation == "validate"


def test_a_duplicate_selection_is_rejected_at_parse_time() -> None:
    payload = _payload()
    payload["components"] = {
        "archetype": "streamlit",
        "capabilities": ["jupyter", "jupyter"],
        "platforms": [],
    }

    with pytest.raises(ForgeEngineError) as exc_info:
        parse_project_spec(payload)

    assert exc_info.value.code is EngineErrorCode.INVALID_PROJECT_SPEC
