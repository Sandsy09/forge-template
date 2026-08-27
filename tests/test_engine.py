"""Tests for the supported template-engine facade."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import forge_template.engine as engine_module
from forge_template import (
    EngineErrorCode,
    ForgeEngineError,
    ProjectSpec,
    discover_components,
    get_engine_info,
    parse_project_spec,
    plan_generation,
    render_project,
    validate_project_spec,
)
from forge_template.schema import REPO_ROOT

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"


def _payload(
    *,
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
    component_options: dict[str, dict[str, Any]] | None = None,
) -> dict[str, object]:
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
            "platforms": platforms,
        },
        "component_options": component_options
        or {"library": {"build_backend": "uv_build"}},
    }


def _spec(**kwargs: Any) -> ProjectSpec:
    return parse_project_spec(_payload(**kwargs))


@pytest.fixture
def fixture_catalogue(monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", FIXTURES)
    return FIXTURES


@pytest.fixture
def copied_catalogue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "components"
    shutil.copytree(FIXTURES, root)
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", root)
    return root


def test_engine_info_reports_package_and_protocols_without_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_discovery() -> None:
        raise AssertionError("engine information must not scan the catalogue")

    monkeypatch.setattr(engine_module, "_load_catalogue", fail_discovery)

    info = get_engine_info()

    assert info.package_version == "0.2.0"
    assert info.projectspec_protocols == (1,)
    assert info.component_manifest_protocols == (1,)


def test_installed_catalogue_is_deliberately_empty() -> None:
    assert discover_components() == ()


def test_discovery_returns_sorted_path_free_descriptors(
    fixture_catalogue: Path,
) -> None:
    descriptors = discover_components()

    assert [descriptor.id for descriptor in descriptors] == [
        "changelog",
        "coverage",
        "documentation",
        "github",
        "library",
    ]
    library = descriptors[-1]
    assert library.name == "Library"
    assert library.kind == "archetype"
    assert [option.name for option in library.options] == [
        "build_backend",
        "initial_version",
    ]
    assert "path" not in library.model_dump_json()
    assert "content_root" not in library.model_dump_json()


def test_discovery_wraps_missing_and_invalid_catalogues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", missing)
    with pytest.raises(ForgeEngineError) as missing_error:
        discover_components()
    assert missing_error.value.code is EngineErrorCode.COMPONENT_DISCOVERY_FAILED

    duplicate_root = tmp_path / "duplicate"
    shutil.copytree(FIXTURES, duplicate_root)
    shutil.copytree(duplicate_root / "library", duplicate_root / "library-copy")
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", duplicate_root)
    with pytest.raises(ForgeEngineError) as invalid_error:
        discover_components()
    assert invalid_error.value.code is EngineErrorCode.COMPONENT_DISCOVERY_FAILED


def test_parse_project_spec_accepts_every_supported_input() -> None:
    payload = _payload()
    encoded = json.dumps(payload)

    from_mapping = parse_project_spec(payload)

    assert parse_project_spec(from_mapping) is from_mapping
    assert parse_project_spec(encoded) == from_mapping
    assert parse_project_spec(encoded.encode()) == from_mapping


def test_parse_project_spec_returns_structured_validation_details() -> None:
    payload = _payload()
    payload["protocol_version"] = "1"

    with pytest.raises(ForgeEngineError) as exc_info:
        parse_project_spec(payload)

    error = exc_info.value
    assert error.code is EngineErrorCode.INVALID_PROJECT_SPEC
    assert error.operation == "parse"
    assert error.details[0].path == ("protocol_version",)
    assert error.as_dict()["code"] == "invalid-project-spec"


def test_parse_project_spec_rejects_non_wire_input() -> None:
    with pytest.raises(ForgeEngineError) as exc_info:
        parse_project_spec(42)  # type: ignore[call-overload]

    assert exc_info.value.details[0].code == "invalid-input-type"


def test_full_validation_accepts_fixture_selection(fixture_catalogue: Path) -> None:
    spec = _spec(
        capabilities=("coverage",),
        platforms=("github",),
        component_options={
            "library": {"build_backend": "hatchling"},
            "github": {"organisation": "forge-example"},
        },
    )

    assert validate_project_spec(spec) is spec


def test_full_validation_classifies_selection_and_option_failures(
    fixture_catalogue: Path,
) -> None:
    unknown = _spec()
    unknown_payload = unknown.model_dump(mode="json")
    unknown_payload["components"]["archetype"] = "missing"
    unknown_payload["component_options"] = {}
    unknown_spec = parse_project_spec(unknown_payload)
    with pytest.raises(ForgeEngineError) as selection_error:
        validate_project_spec(unknown_spec)
    assert selection_error.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION

    option_spec = _spec(
        component_options={"library": {"build_backend": "uv_build", "bad": True}}
    )
    with pytest.raises(ForgeEngineError) as option_error:
        validate_project_spec(option_spec)
    assert option_error.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS


def test_empty_production_catalogue_rejects_a_real_selection() -> None:
    with pytest.raises(ForgeEngineError) as exc_info:
        validate_project_spec(_spec())

    assert exc_info.value.code is EngineErrorCode.INVALID_COMPONENT_SELECTION


def test_generation_plan_is_deterministic_and_path_free(
    fixture_catalogue: Path,
) -> None:
    spec = _spec(
        capabilities=("coverage",),
        platforms=("github",),
        component_options={
            "library": {"build_backend": "hatchling"},
            "github": {"organisation": "forge-example"},
        },
    )

    plan = plan_generation(spec)

    assert plan.component_order == ("library", "coverage", "github")
    github_file = next(item for item in plan.files if item.target == "ci.yml")
    assert github_file.owner_component_id == "github"
    assert github_file.extensions[0].component_id == "coverage"
    assert github_file.extensions[0].extension_point == "ci-steps"
    assert "source" not in plan.model_dump_json()


def test_render_project_splices_extensions_and_copies_literal_bytes(
    copied_catalogue: Path,
) -> None:
    binary = b"\x00forge\xff"
    (copied_catalogue / "library" / "content" / "logo.bin").write_bytes(binary)
    spec = _spec(
        capabilities=("coverage",),
        platforms=("github",),
        component_options={
            "library": {"build_backend": "hatchling"},
            "github": {"organisation": "forge-example"},
        },
    )

    rendered = render_project(spec)
    files = {item.target: item.content for item in rendered.files}

    assert files["logo.bin"] == binary
    assert files["ci.yml"].decode() == (
        "name: CI\n"
        "jobs:\n"
        "  checks:\n"
        "    steps:\n"
        "      - name: Coverage\n"
        "        run: echo coverage\n"
    )
    assert not (copied_catalogue.parent / "pyproject.toml").exists()


def test_render_project_orders_contributors_and_supports_multiple_points(
    copied_catalogue: Path,
) -> None:
    github_manifest = copied_catalogue / "github" / "component.toml"
    github_manifest.write_text(
        github_manifest.read_text(encoding="utf-8")
        + (
            '\n[[extension_points]]\nid = "summary"\ncontent = "content/ci.yml.jinja"\n'
        ),
        encoding="utf-8",
    )
    owner = copied_catalogue / "github" / "content" / "ci.yml.jinja"
    owner.write_text(
        owner.read_text(encoding="utf-8") + "  [[forge:extension summary]]\n",
        encoding="utf-8",
    )

    changelog = copied_catalogue / "changelog"
    (changelog / "extensions").mkdir()
    (changelog / "extensions" / "ci-step.yml.jinja").write_text(
        "- name: Changelog\n  run: echo changelog\n", encoding="utf-8"
    )
    changelog_manifest = changelog / "component.toml"
    changelog_manifest.write_text(
        changelog_manifest.read_text(encoding="utf-8")
        + (
            "\n[[contributions]]\n"
            'component = "github"\n'
            'extension_point = "ci-steps"\n'
            'content = "extensions/ci-step.yml.jinja"\n'
        ),
        encoding="utf-8",
    )

    documentation = copied_catalogue / "documentation"
    (documentation / "extensions").mkdir()
    (documentation / "extensions" / "summary.yml.jinja").write_text(
        "summary: enabled\n", encoding="utf-8"
    )
    documentation_manifest = documentation / "component.toml"
    documentation_manifest.write_text(
        documentation_manifest.read_text(encoding="utf-8")
        + (
            "\n[[contributions]]\n"
            'component = "github"\n'
            'extension_point = "summary"\n'
            'content = "extensions/summary.yml.jinja"\n'
        ),
        encoding="utf-8",
    )

    spec = _spec(
        capabilities=("documentation", "coverage", "changelog"),
        platforms=("github",),
        component_options={
            "library": {"build_backend": "uv_build"},
            "github": {"organisation": "forge-example"},
        },
    )
    files = {item.target: item.content for item in render_project(spec).files}

    assert files["ci.yml"].decode() == (
        "name: CI\n"
        "jobs:\n"
        "  checks:\n"
        "    steps:\n"
        "      - name: Changelog\n"
        "        run: echo changelog\n"
        "      - name: Coverage\n"
        "        run: echo coverage\n"
        "  summary: enabled\n"
    )


def test_unselected_extension_removes_the_marker(fixture_catalogue: Path) -> None:
    spec = _spec(
        platforms=("github",),
        component_options={
            "library": {"build_backend": "uv_build"},
            "github": {"organisation": "forge-example"},
        },
    )

    files = {item.target: item.content for item in render_project(spec).files}

    assert b"forge:extension" not in files["ci.yml"]
    assert files["ci.yml"].endswith(b"    steps:\n")


def test_strict_undefined_is_a_structured_render_error(
    copied_catalogue: Path,
) -> None:
    source = copied_catalogue / "library" / "content" / "pyproject.toml.jinja"
    source.write_text(
        source.read_text(encoding="utf-8") + "\n{{ options.library.missing }}\n",
        encoding="utf-8",
    )

    with pytest.raises(ForgeEngineError) as exc_info:
        render_project(_spec())

    assert exc_info.value.code is EngineErrorCode.TEMPLATE_RENDER_FAILED
    assert "missing" in exc_info.value.details[0].message


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "malformed",
        "trailing-content",
        "undeclared",
        "literal-owner",
        "literal-contribution",
        "missing-newline",
        "nested",
        "invalid-utf8",
    ],
)
def test_invalid_extension_contracts_fail_during_planning(
    mutation: str, copied_catalogue: Path
) -> None:
    owner_manifest = copied_catalogue / "github" / "component.toml"
    owner = copied_catalogue / "github" / "content" / "ci.yml.jinja"
    contribution_manifest = copied_catalogue / "coverage" / "component.toml"
    contribution = copied_catalogue / "coverage" / "extensions" / "ci-step.yml.jinja"
    token = "      [[forge:extension ci-steps]]\n"

    if mutation == "missing":
        owner.write_text(owner.read_text(encoding="utf-8").replace(token, ""))
    elif mutation == "duplicate":
        owner.write_text(owner.read_text(encoding="utf-8") + token)
    elif mutation == "malformed":
        owner.write_text(owner.read_text(encoding="utf-8").replace(token, f"x{token}"))
    elif mutation == "trailing-content":
        owner.write_text(
            owner.read_text(encoding="utf-8").replace(token, token.rstrip() + " x\n")
        )
    elif mutation == "undeclared":
        owner.write_text(
            owner.read_text(encoding="utf-8") + "[[forge:extension other]]\n"
        )
    elif mutation == "literal-owner":
        literal = owner.with_suffix("")
        owner.rename(literal)
        owner_manifest.write_text(
            owner_manifest.read_text(encoding="utf-8").replace(
                "content/ci.yml.jinja", "content/ci.yml"
            )
        )
    elif mutation == "literal-contribution":
        literal = contribution.with_suffix("")
        contribution.rename(literal)
        contribution_manifest.write_text(
            contribution_manifest.read_text(encoding="utf-8").replace(
                "extensions/ci-step.yml.jinja", "extensions/ci-step.yml"
            )
        )
    elif mutation == "missing-newline":
        contribution.write_text("- name: Coverage", encoding="utf-8")
    elif mutation == "nested":
        contribution.write_text(
            contribution.read_text(encoding="utf-8") + "[[forge:extension nested]]\n",
            encoding="utf-8",
        )
    elif mutation == "invalid-utf8":
        contribution.write_bytes(b"\xff")

    spec = _spec(
        capabilities=("coverage",),
        platforms=("github",),
        component_options={
            "library": {"build_backend": "hatchling"},
            "github": {"organisation": "forge-example"},
        },
    )
    with pytest.raises(ForgeEngineError) as exc_info:
        plan_generation(spec)

    assert exc_info.value.code is EngineErrorCode.GENERATION_PLAN_FAILED


def test_public_result_models_are_frozen(fixture_catalogue: Path) -> None:
    plan = plan_generation(_spec())

    with pytest.raises(ValidationError, match="frozen"):
        plan.component_order = ("changed",)


def test_project_version_and_release_workflow_share_one_source() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert 'version = "0.2.0"' in pyproject
    assert (
        "tomllib.load(open('pyproject.toml', 'rb'))['project']['version']" in workflow
    )
    assert "bump:" not in workflow
    assert (REPO_ROOT / "src" / "forge_template" / "py.typed").is_file()
