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
    ComponentOwner,
    EngineErrorCode,
    ForgeEngineError,
    FoundationOwner,
    PlannedExtension,
    ProjectSpec,
    discover_components,
    get_engine_info,
    map_legacy_library_answers,
    parse_project_spec,
    plan_generation,
    render_project,
    validate_project_spec,
)
from forge_template.schema import REPO_ROOT

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"
FOUNDATION_FIXTURE = Path(__file__).parent / "fixtures" / "foundation"


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
    # None of these fixture components target Foundation (they predate
    # FT-08.02), so isolate from the real installed Foundation source the
    # same way discovery is already isolated from the real installed
    # catalogue -- FIXTURES has no foundation.toml at its own root, so this
    # resolves to "no Foundation available" for these tests.
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", FIXTURES)
    return FIXTURES


@pytest.fixture
def copied_catalogue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "components"
    shutil.copytree(FIXTURES, root)
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", root)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", root)
    return root


def test_engine_info_reports_package_and_protocols_without_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_discovery() -> None:
        raise AssertionError("engine information must not scan the catalogue")

    monkeypatch.setattr(engine_module, "_load_catalogue", fail_discovery)

    info = get_engine_info()

    assert info.package_version == "0.3.0"
    assert info.projectspec_protocols == (1,)
    assert info.component_manifest_protocols == (1, 2)


def test_installed_catalogue_contains_the_production_library_archetype() -> None:
    """FT-08.02 populates the previously-empty production catalogue; FT-08.04
    adds the second, independent CLI Application archetype beside it."""
    descriptors = discover_components()

    assert [descriptor.id for descriptor in descriptors] == ["cli", "library"]
    library = next(d for d in descriptors if d.id == "library")
    assert library.kind == "archetype"
    assert library.version == "1.0.0"
    assert [option.name for option in library.options] == [
        "packaging_mode",
        "initial_version",
    ]
    initial_version = next(
        option for option in library.options if option.name == "initial_version"
    )
    assert initial_version.format == "pep440"


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
        "library-v2",
    ]
    library = next(
        descriptor for descriptor in descriptors if descriptor.id == "library"
    )
    assert library.name == "Library"
    assert library.kind == "archetype"
    assert [option.name for option in library.options] == [
        "build_backend",
        "initial_version",
    ]
    assert "path" not in library.model_dump_json()
    assert "content_root" not in library.model_dump_json()


def test_discovery_exposes_option_format(fixture_catalogue: Path) -> None:
    library_v2 = next(
        descriptor
        for descriptor in discover_components()
        if descriptor.id == "library-v2"
    )
    option = library_v2.options[0]
    assert option.name == "initial_version"
    assert option.format == "pep440"


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


def _real_library_payload(
    *, component_options: dict[str, dict[str, Any]] | None = None
) -> dict[str, object]:
    """A payload shaped for the *real* installed catalogue's ``library`` --
    ``packaging_mode``/``initial_version``, not the fixture catalogue's
    legacy ``build_backend`` vocabulary ``_payload`` builds by default."""
    return {
        "protocol_version": 1,
        "project": {
            "name": "Example Project",
            "package_name": "example_project",
            "repository_name": "example-project",
            "licence": "mit",
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {"archetype": "library", "capabilities": [], "platforms": []},
        "component_options": component_options or {},
    }


def test_real_selection_against_the_installed_catalogue_succeeds() -> None:
    """The production catalogue is no longer empty (FT-08.02): a real
    selection against it -- with no options supplied, exercising both
    options' defaults -- now succeeds rather than being rejected."""
    spec = parse_project_spec(_real_library_payload())

    assert validate_project_spec(spec) is spec


def test_missing_installed_foundation_source_is_a_generation_plan_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``library`` always targets Foundation; a missing installed Foundation
    source (simulated here, not reachable in a normal installation) fails at
    planning rather than being silently ignored."""
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", tmp_path)
    spec = parse_project_spec(_real_library_payload())

    with pytest.raises(ForgeEngineError) as exc_info:
        plan_generation(spec)

    assert exc_info.value.code is EngineErrorCode.GENERATION_PLAN_FAILED
    assert "none is available" in exc_info.value.details[0].message


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
    assert github_file.owner == ComponentOwner(id="github")
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


def test_intentional_downstream_template_syntax_survives_rendering(
    copied_catalogue: Path,
) -> None:
    source = copied_catalogue / "library" / "content" / "downstream.txt.jinja"
    source.write_text(
        "{% raw %}{{ downstream_variable }}{% endraw %}\n",
        encoding="utf-8",
    )

    files = {item.target: item.content for item in render_project(_spec()).files}

    assert files["downstream.txt"] == b"{{ downstream_variable }}\n"


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


# --- Foundation (FT-08.02) --------------------------------------------------


@pytest.fixture
def foundation_and_v2_catalogue(monkeypatch: pytest.MonkeyPatch) -> Path:
    """The whole fixture catalogue (including ``library-v2``) plus a real
    Foundation source, both via the private test-only override seam."""
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", FIXTURES)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", FOUNDATION_FIXTURE)
    return FIXTURES


def _v2_payload(*, initial_version: str = "0.1.0") -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Example Project",
            "package_name": "example_project",
            "repository_name": "example-project",
            "licence": "mit",
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {"archetype": "library-v2", "capabilities": [], "platforms": []},
        "component_options": {"library-v2": {"initial_version": initial_version}},
    }


def test_plan_generation_identifies_a_foundation_owned_target(
    foundation_and_v2_catalogue: Path,
) -> None:
    spec = parse_project_spec(_v2_payload())

    plan = plan_generation(spec)

    assert plan.component_order == ("library-v2",)
    pyproject = next(item for item in plan.files if item.target == "pyproject.toml")
    assert pyproject.owner == FoundationOwner()
    assert pyproject.extensions == (
        PlannedExtension(
            component_id="library-v2", extension_point="pyproject-build-system"
        ),
    )
    package_file = next(
        item for item in plan.files if item.target == "src/example_project/py.typed"
    )
    assert package_file.owner == ComponentOwner(id="library-v2")


def test_render_project_splices_a_foundation_targeted_contribution(
    foundation_and_v2_catalogue: Path,
) -> None:
    spec = parse_project_spec(_v2_payload())

    files = {item.target: item.content for item in render_project(spec).files}

    assert files["pyproject.toml"].decode() == (
        "[project]\n"
        'name = "example-project"\n'
        'requires-python = ">=3.11"\n\n'
        "[build-system]\n"
        'requires = ["fixture-backend"]\n'
        'build-backend = "fixture_backend"\n'
    )
    assert files["src/example_project/py.typed"] == b""


def test_render_project_canonicalises_a_pep440_option(
    foundation_and_v2_catalogue: Path,
) -> None:
    spec = parse_project_spec(_v2_payload(initial_version="v0.1.0"))

    # A non-canonical but valid PEP 440 value is accepted and normalised --
    # not rejected -- at resolution time (docs/library-archetype.md).
    plan_generation(spec)


def test_selection_targeting_foundation_fails_without_a_foundation_source(
    fixture_catalogue: Path,
) -> None:
    """``library-v2``'s catalogue presence never implies Foundation exists --
    ``_FOUNDATION_ROOT_OVERRIDE`` is deliberately unset by this fixture."""
    spec = parse_project_spec(_v2_payload())

    with pytest.raises(ForgeEngineError) as exc_info:
        plan_generation(spec)

    assert exc_info.value.code is EngineErrorCode.GENERATION_PLAN_FAILED
    assert "none is available" in exc_info.value.details[0].message


# --- map_legacy_library_answers (FT-08.02) ----------------------------------


@pytest.mark.parametrize(
    ("build_backend", "versioning_resolved", "packaging_mode"),
    [
        ("uv_build", "static", "uv-build-static"),
        ("hatchling", "static", "hatchling-static"),
        ("hatchling", "vcs", "hatchling-vcs"),
    ],
)
def test_map_legacy_library_answers_covers_every_documented_row(
    build_backend: str, versioning_resolved: str, packaging_mode: str
) -> None:
    result = map_legacy_library_answers(
        {"build_backend": build_backend, "versioning_resolved": versioning_resolved}
    )
    assert result == {"packaging_mode": packaging_mode}


def test_map_legacy_library_answers_rejects_an_unsupported_combination() -> None:
    with pytest.raises(ForgeEngineError) as exc_info:
        map_legacy_library_answers(
            {"build_backend": "uv_build", "versioning_resolved": "vcs"}
        )
    assert exc_info.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS
    assert exc_info.value.operation == "map-legacy-answers"


def test_map_legacy_library_answers_rejects_missing_or_unexpected_keys() -> None:
    with pytest.raises(ForgeEngineError) as missing_error:
        map_legacy_library_answers({"build_backend": "uv_build"})
    assert "missing legacy Library answer" in missing_error.value.details[0].message

    with pytest.raises(ForgeEngineError) as unexpected_error:
        map_legacy_library_answers(
            {
                "build_backend": "uv_build",
                "versioning_resolved": "static",
                "extra": "x",
            }
        )
    assert (
        "unexpected legacy Library answer" in unexpected_error.value.details[0].message
    )


def test_map_legacy_library_answers_rejects_non_string_values() -> None:
    with pytest.raises(ForgeEngineError) as exc_info:
        map_legacy_library_answers(
            {"build_backend": "uv_build", "versioning_resolved": 1}
        )
    assert "must be strings" in exc_info.value.details[0].message


def test_public_result_models_are_frozen(fixture_catalogue: Path) -> None:
    plan = plan_generation(_spec())

    with pytest.raises(ValidationError, match="frozen"):
        plan.component_order = ("changed",)


def test_project_version_and_release_workflow_share_one_source() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert 'version = "0.3.0"' in pyproject
    assert (
        "tomllib.load(open('pyproject.toml', 'rb'))['project']['version']" in workflow
    )
    assert "bump:" not in workflow
    assert (REPO_ROOT / "src" / "forge_template" / "py.typed").is_file()
