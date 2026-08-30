"""Tests for component manifest protocol v1 and its provisional validators."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from forge_template.component_manifest import (
    COMPONENT_MANIFEST_PROTOCOL_VERSIONS,
    ComponentCompatibility,
    ComponentManifest,
    ComponentReference,
    ComponentTarget,
    Contribution,
    ExtensionPoint,
    FoundationTarget,
    load_component_manifest,
    validate_manifest_selection,
    validate_manifest_set,
)
from forge_template.foundation_source import FoundationSource
from forge_template.project_spec import ProjectSpec

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"


def _manifest_payload(
    identifier: str,
    *,
    kind: str = "capability",
    version: str = "1.0.0",
    requires_python: str = ">=3.11",
    requires: tuple[dict[str, object], ...] = (),
    conflicts: tuple[dict[str, object], ...] = (),
    extension_points: tuple[dict[str, object], ...] = (),
    contributions: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    return {
        "manifest_version": 1,
        "id": identifier,
        "name": identifier.replace("-", " ").title(),
        "description": f"The {identifier} component.",
        "kind": kind,
        "version": version,
        "content_root": "content",
        "compatibility": {
            "projectspec_protocols": (1,),
            "requires_python": requires_python,
        },
        "requires": requires,
        "conflicts": conflicts,
        "extension_points": extension_points,
        "contributions": contributions,
    }


def _manifest(
    identifier: str,
    *,
    kind: str = "capability",
    version: str = "1.0.0",
    requires_python: str = ">=3.11",
    requires: tuple[dict[str, object], ...] = (),
    conflicts: tuple[dict[str, object], ...] = (),
    extension_points: tuple[dict[str, object], ...] = (),
    contributions: tuple[dict[str, object], ...] = (),
) -> ComponentManifest:
    return ComponentManifest.model_validate(
        _manifest_payload(
            identifier,
            kind=kind,
            version=version,
            requires_python=requires_python,
            requires=requires,
            conflicts=conflicts,
            extension_points=extension_points,
            contributions=contributions,
        )
    )


def _project_spec(
    *,
    archetype: str = "library",
    capabilities: tuple[str, ...] = ("documentation",),
    platforms: tuple[str, ...] = ("github",),
    minimum: str = "3.11",
    development: str = "3.13",
) -> ProjectSpec:
    return ProjectSpec.model_validate(
        {
            "protocol_version": 1,
            "project": {
                "name": "Example",
                "package_name": "example",
                "repository_name": "example",
                "licence": "mit",
            },
            "python": {"minimum": minimum, "development": development},
            "components": {
                "archetype": archetype,
                "capabilities": capabilities,
                "platforms": platforms,
            },
        }
    )


def _fixture_manifests() -> tuple[ComponentManifest, ...]:
    return tuple(
        load_component_manifest(FIXTURES / identifier / "component.toml")
        for identifier in ("library", "documentation", "github")
    )


@pytest.mark.parametrize(
    ("identifier", "kind"),
    [
        ("library", "archetype"),
        ("documentation", "capability"),
        ("github", "platform"),
    ],
)
def test_loads_valid_manifest_kinds(identifier: str, kind: str) -> None:
    manifest = load_component_manifest(FIXTURES / identifier / "component.toml")

    assert manifest.manifest_version in COMPONENT_MANIFEST_PROTOCOL_VERSIONS
    assert manifest.id == identifier
    assert manifest.kind == kind


def test_models_are_strict_frozen_and_generate_json_schema() -> None:
    manifest = _manifest("example")
    schema = ComponentManifest.model_json_schema()

    assert schema["properties"]["manifest_version"]["enum"] == [1, 2]
    assert schema["additionalProperties"] is False

    with pytest.raises(ValidationError, match="frozen"):
        manifest.name = "Changed"

    payload = _manifest_payload("example")
    payload["manifest_version"] = "1"
    payload["unexpected"] = True
    with pytest.raises(ValidationError) as exc_info:
        ComponentManifest.model_validate(payload)

    error_types = {error["type"] for error in exc_info.value.errors()}
    assert "value_error" in error_types
    assert "extra_forbidden" in error_types


@pytest.mark.parametrize("manifest_version", [None, 3, True])
def test_missing_unsupported_or_coerced_manifest_version_is_rejected(
    manifest_version: object,
) -> None:
    payload = _manifest_payload("example")
    if manifest_version is None:
        del payload["manifest_version"]
    else:
        payload["manifest_version"] = manifest_version

    with pytest.raises(ValidationError):
        ComponentManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "Bad_Id"),
        ("kind", "foundation"),
        ("name", "   "),
        ("description", ""),
        ("version", "v1.0"),
        ("version", "not-a-version"),
    ],
)
def test_invalid_identity_and_version_metadata_is_rejected(
    field: str, value: str
) -> None:
    payload = _manifest_payload("example")
    payload[field] = value

    with pytest.raises(ValidationError):
        ComponentManifest.model_validate(payload)


def test_reference_specifiers_are_validated_and_canonicalised() -> None:
    reference = ComponentReference(id="library", version=">=1,<2")

    assert reference.version == "<2,>=1"
    assert reference.accepts("1.2.0") is True
    assert reference.accepts("2.0.0") is False

    with pytest.raises(ValidationError, match="invalid PEP 440 specifier"):
        ComponentReference(id="library", version="not a specifier")
    with pytest.raises(ValidationError, match="must not be empty"):
        ComponentReference(id="library", version="")


def test_extension_point_and_contribution_are_strict_and_frozen() -> None:
    point = ExtensionPoint(id="ci-steps", content="content/ci.yml")
    contribution = Contribution.model_validate(
        {
            "component": "github",
            "extension_point": "ci-steps",
            "content": "extensions/step.yml",
        }
    )

    assert contribution.target == ComponentTarget(id="github")

    with pytest.raises(ValidationError, match="frozen"):
        point.id = "changed"
    with pytest.raises(ValidationError, match="frozen"):
        contribution.target = FoundationTarget()
    with pytest.raises(ValidationError):
        ExtensionPoint.model_validate(
            {"id": "ci-steps", "content": "content/ci.yml", "unexpected": True}
        )


def test_contribution_accepts_protocol_1_legacy_component_key() -> None:
    """Protocol 1's flat ``component = "id"`` key still parses unchanged,
    normalised into a ``ComponentTarget`` -- see FT-08.02/ADR 0033."""
    contribution = Contribution.model_validate(
        {
            "component": "github",
            "extension_point": "ci-steps",
            "content": "extensions/step.yml",
        }
    )
    assert contribution.target == ComponentTarget(kind="component", id="github")


def test_contribution_accepts_protocol_2_discriminated_target() -> None:
    component_target = Contribution.model_validate(
        {
            "target": {"kind": "component", "id": "github"},
            "extension_point": "ci-steps",
            "content": "extensions/step.yml",
        }
    )
    assert component_target.target == ComponentTarget(id="github")

    foundation_target = Contribution.model_validate(
        {
            "target": {"kind": "foundation"},
            "extension_point": "pyproject-build-system",
            "content": "extensions/build-system.toml.jinja",
        }
    )
    assert foundation_target.target == FoundationTarget()


def test_contribution_rejects_both_legacy_and_discriminated_target() -> None:
    with pytest.raises(ValidationError, match="not declare both"):
        Contribution.model_validate(
            {
                "component": "github",
                "target": {"kind": "foundation"},
                "extension_point": "ci-steps",
                "content": "extensions/step.yml",
            }
        )


def test_python_compatibility_covers_the_whole_tested_range() -> None:
    spec = _project_spec(minimum="3.11", development="3.13")

    assert ComponentCompatibility(
        projectspec_protocols=(1,), requires_python=">=3.11"
    ).supports(spec)
    assert not ComponentCompatibility(
        projectspec_protocols=(1,), requires_python=">=3.12"
    ).supports(spec)


def test_protocol_compatibility_is_non_empty_unique_and_supported() -> None:
    with pytest.raises(ValidationError):
        ComponentCompatibility(projectspec_protocols=(), requires_python=">=3.11")
    with pytest.raises(ValidationError, match="duplicates"):
        ComponentCompatibility(projectspec_protocols=(1, 1), requires_python=">=3.11")
    with pytest.raises(ValidationError):
        ComponentCompatibility.model_validate(
            {"projectspec_protocols": (2,), "requires_python": ">=3.11"}
        )


@pytest.mark.parametrize(
    "resource",
    ["/absolute", "C:/absolute", "../outside", "content/../outside", "a\\b"],
)
def test_resource_paths_must_be_normalised_and_relative(resource: str) -> None:
    payload = _manifest_payload("example")
    payload["content_root"] = resource

    with pytest.raises(ValidationError, match="resource paths"):
        ComponentManifest.model_validate(payload)


def _copy_fixture(tmp_path: Path, identifier: str = "library") -> Path:
    destination = tmp_path / identifier
    shutil.copytree(FIXTURES / identifier, destination)
    return destination / "component.toml"


def test_loader_requires_canonical_filename(tmp_path: Path) -> None:
    manifest_path = _copy_fixture(tmp_path)
    renamed = manifest_path.with_name("manifest.toml")
    manifest_path.rename(renamed)

    with pytest.raises(ValueError, match=r"component\.toml"):
        load_component_manifest(renamed)


def test_loader_rejects_missing_empty_and_invalid_resource_types(
    tmp_path: Path,
) -> None:
    missing = _copy_fixture(tmp_path / "missing")
    shutil.rmtree(missing.parent / "content")
    with pytest.raises(FileNotFoundError):
        load_component_manifest(missing)

    empty = _copy_fixture(tmp_path / "empty")
    shutil.rmtree(empty.parent / "content")
    (empty.parent / "content").mkdir()
    with pytest.raises(ValueError, match="content_root is empty"):
        load_component_manifest(empty)

    wrong_type = _copy_fixture(tmp_path / "wrong-type")
    shutil.rmtree(wrong_type.parent / "content")
    (wrong_type.parent / "content").write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        load_component_manifest(wrong_type)

    missing_schema = _copy_fixture(tmp_path / "missing-schema")
    (missing_schema.parent / "options.schema.json").unlink()
    with pytest.raises(FileNotFoundError):
        load_component_manifest(missing_schema)


def test_loader_rejects_symlink_escape_when_supported(tmp_path: Path) -> None:
    manifest_path = _copy_fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file.txt").write_text("outside", encoding="utf-8")
    shutil.rmtree(manifest_path.parent / "content")
    try:
        (manifest_path.parent / "content").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("creating directory symlinks is unavailable on this platform")

    with pytest.raises(ValueError, match="escapes component directory"):
        load_component_manifest(manifest_path)


def test_loader_rejects_missing_extension_point_and_contribution_files(
    tmp_path: Path,
) -> None:
    missing_point = _copy_fixture(tmp_path / "missing-point", "library")
    with missing_point.open("a", encoding="utf-8") as manifest_file:
        manifest_file.write(
            '\n[[extension_points]]\nid = "ci-steps"\ncontent = "content/absent.yml"\n'
        )
    with pytest.raises(FileNotFoundError):
        load_component_manifest(missing_point)

    missing_contribution = _copy_fixture(
        tmp_path / "missing-contribution", "documentation"
    )
    with missing_contribution.open("a", encoding="utf-8") as manifest_file:
        manifest_file.write(
            '\n[[contributions]]\ncomponent = "github"\n'
            'extension_point = "ci-steps"\ncontent = "extensions/absent.yml"\n'
        )
    with pytest.raises(FileNotFoundError):
        load_component_manifest(missing_contribution)


def test_extension_point_content_must_fall_inside_content_root() -> None:
    with pytest.raises(ValidationError, match="must fall inside content_root"):
        _manifest(
            "github",
            kind="platform",
            extension_points=({"id": "ci-steps", "content": "outside.yml"},),
        )


def test_contribution_content_must_fall_outside_content_root() -> None:
    with pytest.raises(ValidationError, match="must fall outside content_root"):
        _manifest(
            "documentation",
            contributions=(
                {
                    "component": "github",
                    "extension_point": "ci-steps",
                    "content": "content/inside.yml",
                },
            ),
        )


def test_extension_point_and_contribution_identifiers_must_be_unique() -> None:
    with pytest.raises(ValidationError, match="extension point identifiers"):
        _manifest(
            "github",
            kind="platform",
            extension_points=(
                {"id": "ci-steps", "content": "content/a.yml"},
                {"id": "ci-steps", "content": "content/b.yml"},
            ),
        )
    with pytest.raises(ValidationError, match="same extension point twice"):
        _manifest(
            "documentation",
            contributions=(
                {
                    "component": "github",
                    "extension_point": "ci-steps",
                    "content": "extensions/a.yml",
                },
                {
                    "component": "github",
                    "extension_point": "ci-steps",
                    "content": "extensions/b.yml",
                },
            ),
        )


def test_component_must_not_contribute_to_its_own_extension_point() -> None:
    with pytest.raises(ValidationError, match="must not contribute to its own"):
        _manifest(
            "github",
            kind="platform",
            extension_points=({"id": "ci-steps", "content": "content/ci.yml"},),
            contributions=(
                {
                    "component": "github",
                    "extension_point": "ci-steps",
                    "content": "extensions/step.yml",
                },
            ),
        )


def test_manifest_references_reject_duplicates_self_and_contradictions() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        _manifest(
            "example",
            requires=({"id": "library"}, {"id": "library", "version": ">=1"}),
        )
    with pytest.raises(ValidationError, match="reference itself"):
        _manifest("example", requires=({"id": "example"},))
    with pytest.raises(ValidationError, match="both required and conflicting"):
        _manifest(
            "example",
            requires=({"id": "library"},),
            conflicts=({"id": "library"},),
        )


def test_manifest_set_requires_unique_ids_and_resolvable_matching_references() -> None:
    library = _manifest("library", kind="archetype")
    duplicate = _manifest("library", kind="platform")
    with pytest.raises(ValueError, match="globally unique"):
        validate_manifest_set((library, duplicate))

    missing = _manifest("docs", requires=({"id": "missing"},))
    with pytest.raises(ValueError, match="missing component"):
        validate_manifest_set((library, missing))

    mismatched = _manifest("docs", requires=({"id": "library", "version": ">=2"},))
    with pytest.raises(ValueError, match=r"references.*found"):
        validate_manifest_set((library, mismatched))


def test_manifest_set_rejects_dependency_cycles() -> None:
    first = _manifest("first", requires=({"id": "second"},))
    second = _manifest("second", requires=({"id": "first"},))

    with pytest.raises(ValueError, match="cycle"):
        validate_manifest_set((second, first))


def test_manifest_set_rejects_contributions_to_missing_component_or_point() -> None:
    github = _manifest(
        "github",
        kind="platform",
        extension_points=({"id": "ci-steps", "content": "content/ci.yml"},),
    )

    unknown_component = _manifest(
        "documentation",
        contributions=(
            {
                "component": "missing",
                "extension_point": "ci-steps",
                "content": "extensions/step.yml",
            },
        ),
    )
    with pytest.raises(ValueError, match="contributes to missing component"):
        validate_manifest_set((github, unknown_component))

    unknown_point = _manifest(
        "documentation",
        contributions=(
            {
                "component": "github",
                "extension_point": "missing-point",
                "content": "extensions/step.yml",
            },
        ),
    )
    with pytest.raises(ValueError, match="undeclared extension point"):
        validate_manifest_set((github, unknown_point))

    known = _manifest(
        "documentation",
        contributions=(
            {
                "component": "github",
                "extension_point": "ci-steps",
                "content": "extensions/step.yml",
            },
        ),
    )
    validated = validate_manifest_set((github, known))
    assert [manifest.id for manifest in validated] == ["documentation", "github"]


def test_valid_project_spec_selection_uses_manifest_contract() -> None:
    selected = validate_manifest_selection(_project_spec(), _fixture_manifests())

    assert [manifest.id for manifest in selected] == [
        "documentation",
        "github",
        "library",
    ]


def test_selection_rejects_unknown_components_and_wrong_kinds() -> None:
    manifests = _fixture_manifests()
    with pytest.raises(ValueError, match="unknown component"):
        validate_manifest_selection(_project_spec(capabilities=("missing",)), manifests)
    with pytest.raises(ValueError, match="manifest kind is platform"):
        validate_manifest_selection(
            _project_spec(capabilities=("github",), platforms=()), manifests
        )


def test_selection_rejects_one_identifier_under_multiple_kinds() -> None:
    with pytest.raises(ValueError, match="multiple kinds"):
        validate_manifest_selection(
            _project_spec(capabilities=("github",)), _fixture_manifests()
        )


def test_selection_rejects_missing_dependencies_without_auto_selection() -> None:
    library, documentation, github = _fixture_manifests()
    project_shape = _manifest("project-shape", kind="archetype")

    with pytest.raises(ValueError, match=r"requires selected component.*library"):
        validate_manifest_selection(
            _project_spec(archetype="project-shape"),
            (library, documentation, github, project_shape),
        )


def test_selection_rejects_selected_conflicts() -> None:
    library, documentation, _github = _fixture_manifests()
    conflicting_github = _manifest(
        "github", kind="platform", conflicts=({"id": "documentation"},)
    )

    with pytest.raises(ValueError, match=r"conflicts with selected.*documentation"):
        validate_manifest_selection(
            _project_spec(), (library, documentation, conflicting_github)
        )


def test_selection_rejects_incompatible_python_range() -> None:
    library, _documentation, github = _fixture_manifests()
    newer_documentation = _manifest(
        "documentation",
        requires_python=">=3.12",
        requires=({"id": "library", "version": ">=1,<2"},),
    )

    with pytest.raises(ValueError, match="incompatible with this ProjectSpec"):
        validate_manifest_selection(
            _project_spec(), (library, newer_documentation, github)
        )


def test_reference_order_is_canonical_not_composition_order() -> None:
    first = _manifest("first")
    second = _manifest("second")
    consumer_a = _manifest(
        "consumer",
        requires=({"id": "second"}, {"id": "first"}),
    )
    consumer_b = _manifest(
        "consumer",
        requires=({"id": "first"}, {"id": "second"}),
    )

    assert consumer_a == consumer_b
    assert [reference.id for reference in consumer_a.requires] == ["first", "second"]
    assert validate_manifest_set((consumer_a, second, first)) == validate_manifest_set(
        (first, consumer_b, second)
    )


def _manifest_v2(
    identifier: str,
    *,
    kind: str = "capability",
    contributions: tuple[dict[str, object], ...] = (),
) -> ComponentManifest:
    payload = _manifest_payload(identifier, kind=kind, contributions=contributions)
    payload["manifest_version"] = 2
    return ComponentManifest.model_validate(payload)


def _foundation_source(*, points: tuple[dict[str, object], ...]) -> FoundationSource:
    return FoundationSource.model_validate(
        {"foundation_version": 1, "content_root": "content", "extension_points": points}
    )


def test_protocol_1_manifest_rejects_discriminated_target_table() -> None:
    payload = _manifest_payload(
        "example",
        contributions=(
            {
                "target": {"kind": "foundation"},
                "extension_point": "pyproject-build-system",
                "content": "extensions/build-system.toml.jinja",
            },
        ),
    )
    with pytest.raises(ValidationError, match="must use 'component', not 'target'"):
        ComponentManifest.model_validate(payload)


def test_protocol_2_manifest_rejects_legacy_component_key() -> None:
    payload = _manifest_payload(
        "example",
        contributions=(
            {
                "component": "github",
                "extension_point": "ci-steps",
                "content": "extensions/step.yml",
            },
        ),
    )
    payload["manifest_version"] = 2
    with pytest.raises(ValidationError, match="must use 'target', not 'component'"):
        ComponentManifest.model_validate(payload)


def test_component_may_contribute_to_foundation_without_self_contribution_error() -> (
    None
):
    """A component contributing to Foundation is never mistaken for a
    self-contribution -- Foundation is never ``self.id``."""
    manifest = _manifest_v2(
        "library-v2",
        kind="archetype",
        contributions=(
            {
                "target": {"kind": "foundation"},
                "extension_point": "pyproject-build-system",
                "content": "extensions/build-system.toml.jinja",
            },
        ),
    )
    assert manifest.contributions[0].target == FoundationTarget()


def test_foundation_target_is_unchecked_without_a_foundation_source() -> None:
    """Catalogue-wide validation defers a Foundation-targeted contribution's
    published-point check to whichever caller actually has the installed
    Foundation source (``forge_template.engine``); it is not an error by
    itself for ``validate_manifest_set`` to be called without one."""
    contributor = _manifest_v2(
        "library-v2",
        kind="archetype",
        contributions=(
            {
                "target": {"kind": "foundation"},
                "extension_point": "pyproject-build-system",
                "content": "extensions/build-system.toml.jinja",
            },
        ),
    )
    validated = validate_manifest_set((contributor,))
    assert [manifest.id for manifest in validated] == ["library-v2"]


def test_foundation_targeted_contribution_is_checked_against_a_supplied_source() -> (
    None
):
    contributor = _manifest_v2(
        "library-v2",
        kind="archetype",
        contributions=(
            {
                "target": {"kind": "foundation"},
                "extension_point": "pyproject-build-system",
                "content": "extensions/build-system.toml.jinja",
            },
        ),
    )

    matching = _foundation_source(
        points=(
            {"id": "pyproject-build-system", "content": "content/pyproject.toml.jinja"},
        )
    )
    validate_manifest_set((contributor,), matching)

    mismatched = _foundation_source(
        points=({"id": "readme-project-shape", "content": "content/README.md.jinja"},)
    )
    with pytest.raises(ValueError, match="undeclared extension point"):
        validate_manifest_set((contributor,), mismatched)
