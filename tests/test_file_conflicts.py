"""Tests for output target, disposition, and collision rules."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from forge_template.component_manifest import ComponentManifest, load_component_manifest
from forge_template.composition import ComponentPlacement, composition_plan
from forge_template.file_conflicts import (
    ComponentOwner,
    FoundationOwner,
    OutputContribution,
    OutputFile,
    component_targets,
    output_target,
    render_output_path,
    resolve_output_plan,
)
from forge_template.foundation_source import foundation_placement
from forge_template.project_spec import ProjectSpec

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"
FOUNDATION_FIXTURE = (
    Path(__file__).parent / "fixtures" / "foundation" / "foundation.toml"
)


def _manifest_payload(
    identifier: str,
    *,
    kind: str = "capability",
    manifest_version: int = 1,
    extension_points: tuple[dict[str, object], ...] = (),
    contributions: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    return {
        "manifest_version": manifest_version,
        "id": identifier,
        "name": identifier.replace("-", " ").title(),
        "description": f"The {identifier} component.",
        "kind": kind,
        "version": "1.0.0",
        "content_root": "content",
        "compatibility": {
            "projectspec_protocols": (1,),
            "requires_python": ">=3.11",
        },
        "extension_points": extension_points,
        "contributions": contributions,
    }


def _manifest(
    identifier: str,
    *,
    kind: str = "capability",
    manifest_version: int = 1,
    extension_points: tuple[dict[str, object], ...] = (),
    contributions: tuple[dict[str, object], ...] = (),
) -> ComponentManifest:
    return ComponentManifest.model_validate(
        _manifest_payload(
            identifier,
            kind=kind,
            manifest_version=manifest_version,
            extension_points=extension_points,
            contributions=contributions,
        )
    )


def _placement(
    manifest: ComponentManifest, content_paths: tuple[str, ...]
) -> ComponentPlacement:
    return ComponentPlacement(manifest=manifest, content_paths=content_paths)


def _project_spec(
    *,
    archetype: str = "library",
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
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
            "python": {"minimum": "3.11", "development": "3.13"},
            "components": {
                "archetype": archetype,
                "capabilities": capabilities,
                "platforms": platforms,
            },
        }
    )


def _fixture_manifests(*identifiers: str) -> tuple[ComponentManifest, ...]:
    return tuple(
        load_component_manifest(FIXTURES / identifier / "component.toml")
        for identifier in identifiers
    )


def test_output_target_strips_trailing_jinja_suffix() -> None:
    assert output_target("ci.yml.jinja") == "ci.yml"


def test_output_target_keeps_non_template_paths_literal() -> None:
    assert output_target(".coveragerc") == ".coveragerc"


def test_render_output_path_substitutes_template_variables() -> None:
    rendered = render_output_path(
        "src/{{ project.package_name }}/py.typed",
        {"project": {"package_name": "widget"}},
    )
    assert rendered == "src/widget/py.typed"


def test_render_output_path_is_strict_undefined() -> None:
    with pytest.raises(ValueError, match="failed to render"):
        render_output_path("src/{{ missing }}/py.typed", {})


@pytest.mark.parametrize(
    "rendered_path",
    ["/absolute", "../outside", "content/../outside", "a\\b"],
)
def test_render_output_path_rejects_an_unsafe_rendered_result(
    rendered_path: str,
) -> None:
    with pytest.raises(ValueError, match="resource paths"):
        render_output_path("{{ path }}", {"path": rendered_path})


def test_component_targets_rejects_within_component_clash() -> None:
    manifest = _manifest("duplicate")
    placement = _placement(manifest, ("foo.txt", "foo.txt.jinja"))

    with pytest.raises(ValueError, match="same target"):
        component_targets(placement, {})


def test_resolve_output_plan_rejects_two_components_creating_same_target() -> None:
    first = _placement(_manifest("first", kind="archetype"), ("shared.txt",))
    second = _placement(_manifest("second"), ("shared.txt",))

    with pytest.raises(ValueError, match=r"first.*second.*shared\.txt"):
        resolve_output_plan((first, second))


def test_resolve_output_plan_attaches_extensions_in_composition_order() -> None:
    owner = _manifest(
        "github",
        kind="platform",
        extension_points=({"id": "ci-steps", "content": "content/ci.yml"},),
    )
    first_contributor = _manifest(
        "coverage",
        contributions=(
            {
                "component": "github",
                "extension_point": "ci-steps",
                "content": "extensions/coverage-step.yml",
            },
        ),
    )
    second_contributor = _manifest(
        "linting",
        contributions=(
            {
                "component": "github",
                "extension_point": "ci-steps",
                "content": "extensions/lint-step.yml",
            },
        ),
    )
    placements = (
        _placement(first_contributor, ("coverage.txt",)),
        _placement(second_contributor, ("lint.txt",)),
        _placement(owner, ("ci.yml",)),
    )

    output_files = resolve_output_plan(placements)
    assert [output_file.target for output_file in output_files] == [
        "ci.yml",
        "coverage.txt",
        "lint.txt",
    ]

    output_file = next(
        output_file for output_file in output_files if output_file.target == "ci.yml"
    )
    assert output_file.base == OutputContribution(
        owner=ComponentOwner(id="github"), disposition="create", source_path="ci.yml"
    )
    assert output_file.extensions == (
        OutputContribution(
            owner=ComponentOwner(id="coverage"),
            disposition="extend",
            source_path="extensions/coverage-step.yml",
            extension_point="ci-steps",
        ),
        OutputContribution(
            owner=ComponentOwner(id="linting"),
            disposition="extend",
            source_path="extensions/lint-step.yml",
            extension_point="ci-steps",
        ),
    )


def test_resolve_output_plan_skips_contribution_when_owner_not_selected() -> None:
    contributor = _manifest(
        "coverage",
        contributions=(
            {
                "component": "github",
                "extension_point": "ci-steps",
                "content": "extensions/coverage-step.yml",
            },
        ),
    )
    placements = (_placement(contributor, ("other.txt",)),)

    output_files = resolve_output_plan(placements)

    assert [output_file.target for output_file in output_files] == ["other.txt"]
    assert output_files[0].extensions == ()


def test_resolve_output_plan_rejects_extension_point_missing_from_owner_placement() -> (
    None
):
    owner = _manifest(
        "github",
        kind="platform",
        extension_points=({"id": "ci-steps", "content": "content/ci.yml"},),
    )
    contributor = _manifest(
        "coverage",
        contributions=(
            {
                "component": "github",
                "extension_point": "ci-steps",
                "content": "extensions/coverage-step.yml",
            },
        ),
    )
    # The owner's placement omits "ci.yml" -- a malformed plan a caller built
    # by hand rather than through composition_plan.
    placements = (
        _placement(owner, ("other.yml",)),
        _placement(contributor, ("other.txt",)),
    )

    with pytest.raises(ValueError, match="does not include"):
        resolve_output_plan(placements)


def test_resolve_output_plan_rejects_contribution_to_undeclared_point() -> None:
    owner = _manifest("github", kind="platform")
    contributor = _manifest(
        "coverage",
        contributions=(
            {
                "component": "github",
                "extension_point": "missing-point",
                "content": "extensions/coverage-step.yml",
            },
        ),
    )
    placements = (
        _placement(owner, ("ci.yml",)),
        _placement(contributor, ("other.txt",)),
    )

    with pytest.raises(ValueError, match="undeclared extension point"):
        resolve_output_plan(placements)


def test_resolve_output_plan_orders_targets_ascending() -> None:
    placements = (_placement(_manifest("app", kind="archetype"), ("z.txt", "a.txt")),)

    output_files = resolve_output_plan(placements)

    assert [output_file.target for output_file in output_files] == ["a.txt", "z.txt"]


def test_output_models_are_strict_and_frozen() -> None:
    contribution = OutputContribution(
        owner=ComponentOwner(id="github"), disposition="create", source_path="ci.yml"
    )
    output_file = OutputFile(target="ci.yml", base=contribution)

    with pytest.raises(ValidationError, match="frozen"):
        output_file.target = "changed.yml"
    with pytest.raises(ValidationError):
        OutputContribution.model_validate(
            {
                "owner": {"kind": "component", "id": "github"},
                "disposition": "merge",
                "source_path": "ci.yml",
            }
        )
    with pytest.raises(ValidationError):
        OutputFile.model_validate(
            {"target": "ci.yml", "base": contribution, "unexpected": True}
        )


def test_resolve_output_plan_end_to_end_with_real_fixtures() -> None:
    manifest_paths = [
        FIXTURES / identifier / "component.toml"
        for identifier in ("library", "coverage", "github")
    ]
    spec = _project_spec(capabilities=("coverage",), platforms=("github",))

    plan = composition_plan(spec, manifest_paths)
    output_files = resolve_output_plan(plan)

    ci_file = next(
        output_file for output_file in output_files if output_file.target == "ci.yml"
    )
    assert ci_file.base.owner == ComponentOwner(id="github")
    assert [extension.owner for extension in ci_file.extensions] == [
        ComponentOwner(id="coverage")
    ]
    assert ci_file.extensions[0].source_path == "extensions/ci-step.yml.jinja"


# --- Foundation-aware resolution (FT-08.02) ---------------------------------


def _foundation_owner_manifest(
    *, extension_point: str, content: str
) -> ComponentManifest:
    return _manifest(
        "library-v2",
        kind="archetype",
        manifest_version=2,
        contributions=(
            {
                "target": {"kind": "foundation"},
                "extension_point": extension_point,
                "content": content,
            },
        ),
    )


def test_resolve_output_plan_claims_foundation_content_first() -> None:
    foundation = foundation_placement(FOUNDATION_FIXTURE)

    output_files = resolve_output_plan((), foundation=foundation)

    assert [output_file.target for output_file in output_files] == ["pyproject.toml"]
    assert output_files[0].base.owner == FoundationOwner()


def test_resolve_output_plan_splices_a_foundation_targeted_contribution() -> None:
    foundation = foundation_placement(FOUNDATION_FIXTURE)
    contributor = _foundation_owner_manifest(
        extension_point="pyproject-build-system",
        content="extensions/build-system.toml.jinja",
    )
    placements = (_placement(contributor, ("other.txt",)),)

    output_files = resolve_output_plan(placements, foundation=foundation)

    pyproject = next(
        output_file
        for output_file in output_files
        if output_file.target == "pyproject.toml"
    )
    assert pyproject.base.owner == FoundationOwner()
    assert pyproject.extensions == (
        OutputContribution(
            owner=ComponentOwner(id="library-v2"),
            disposition="extend",
            source_path="extensions/build-system.toml.jinja",
            extension_point="pyproject-build-system",
        ),
    )


def test_resolve_output_plan_rejects_foundation_target_without_a_source() -> None:
    contributor = _foundation_owner_manifest(
        extension_point="pyproject-build-system",
        content="extensions/build-system.toml.jinja",
    )
    placements = (_placement(contributor, ("other.txt",)),)

    with pytest.raises(ValueError, match="none is available"):
        resolve_output_plan(placements)


def test_resolve_output_plan_rejects_component_and_foundation_target_collision() -> (
    None
):
    foundation = foundation_placement(FOUNDATION_FIXTURE)
    colliding = _manifest("colliding", kind="archetype")
    placements = (_placement(colliding, ("pyproject.toml.jinja",)),)

    with pytest.raises(ValueError, match=r"Foundation.*colliding.*pyproject\.toml"):
        resolve_output_plan(placements, foundation=foundation)


def test_resolve_output_plan_renders_a_templated_content_path() -> None:
    contributor = _manifest("library-v2", kind="archetype", manifest_version=2)
    placement = _placement(contributor, ("src/{{ project.package_name }}/py.typed",))

    output_files = resolve_output_plan(
        (placement,), {"project": {"package_name": "widget"}}
    )

    assert [output_file.target for output_file in output_files] == [
        "src/widget/py.typed"
    ]
