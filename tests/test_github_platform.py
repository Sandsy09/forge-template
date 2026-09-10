"""Fast render-level tests for the production GitHub platform.

FT-17.02 / ADR 0063 ships ``github`` as the first ``kind = "platform"``
component: one required ``organisation`` option, a four-job CI workflow,
``CODEOWNERS``, issue and pull-request templates, the ``ci-jobs`` / ``ci-steps``
points on its own CI content, and host-scoped contributions into Foundation's
``pyproject-project-urls`` / ``readme-project-shape`` / ``contributing-project-shape``
/ ``security-project-shape`` points.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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
from forge_template.component_manifest import load_component_manifest
from forge_template.github_actions import check_action_pins

_ORG = "reference-org"
_COMPONENTS_ROOT = Path(__file__).parents[1] / "src" / "forge_template" / "components"


def _payload(
    *,
    platforms: tuple[str, ...] = ("github",),
    github_options: dict[str, object] | None = None,
) -> dict[str, object]:
    options: dict[str, object] = {
        "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"}
    }
    if "github" in platforms:
        options["github"] = (
            github_options if github_options is not None else {"organisation": _ORG}
        )
    return {
        "protocol_version": 1,
        "project": {
            "name": "Reference Project",
            "package_name": "reference_project",
            "repository_name": "reference-project",
            "description": "GitHub platform fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User", "email": "test@example.invalid"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": "library",
            "capabilities": [],
            "platforms": list(platforms),
        },
        "component_options": options,
    }


def _rendered(payload: dict[str, object]) -> dict[str, bytes]:
    spec = parse_project_spec(payload)
    return {item.target: item.content for item in render_project(spec).files}


# --- discovery --------------------------------------------------------------


def test_discovery_exposes_github_as_a_platform_with_one_option() -> None:
    descriptors = {d.id: d for d in discover_components()}
    github = descriptors["github"]

    assert github.kind == "platform"
    assert github.version == "1.0.0"
    assert github.projectspec_protocols == (1,)
    assert github.requires_python == ">=3.11"
    assert github.requires == ()
    assert github.conflicts == ()
    assert [option.name for option in github.options] == ["organisation"]
    assert github.options[0].required is True

    serialised = github.model_dump_json()
    for leak in ("content_root", "options_schema", "extensions/", "content/", ".toml"):
        assert leak not in serialised, f"descriptor leaks {leak!r}"


# --- owned files -----------------------------------------------------------


def test_github_owns_the_ci_workflow_codeowners_and_templates() -> None:
    plan = plan_generation(parse_project_spec(_payload()))
    by_target = {item.target: item for item in plan.files}

    owned = {
        ".github/workflows/ci.yml",
        ".github/CODEOWNERS",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
    }
    for target in owned:
        assert target in by_target, f"{target} not planned"
        owner = by_target[target].owner
        assert isinstance(owner, ComponentOwner)
        assert owner.id == "github"


def test_no_github_files_without_the_platform() -> None:
    rendered = _rendered(_payload(platforms=(), github_options=None))
    assert not [target for target in rendered if target.startswith(".github/")]


# --- CI workflow content --------------------------------------------------


def test_ci_workflow_is_valid_yaml_with_the_expected_shape() -> None:
    ci = _rendered(_payload())[".github/workflows/ci.yml"].decode()
    document = yaml.safe_load(ci)

    assert list(document["jobs"]) == ["lint", "typecheck", "test", "build"]
    for job in document["jobs"].values():
        assert job["runs-on"] == "ubuntu-latest"
    assert document["jobs"]["test"]["strategy"]["matrix"]["python-version"] == [
        "3.11",
        "3.12",
        "3.13",
    ]
    # The generated poe tasks, not direct tool calls.
    run_steps = " ".join(
        step.get("run", "")
        for job in document["jobs"].values()
        for step in job["steps"]
    )
    assert "uv run poe lint" in run_steps
    assert "uv run poe typecheck" in run_steps
    assert "uv run poe test" in run_steps


def test_ci_workflow_action_pins_are_immutable_and_updater_readable(
    tmp_path: Path,
) -> None:
    ci = _rendered(_payload())[".github/workflows/ci.yml"]
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_bytes(ci)
    assert check_action_pins(workflows) == []


def test_matrix_follows_the_tested_python_range() -> None:
    payload = _payload()
    payload["python"] = {"minimum": "3.12", "development": "3.14"}
    ci = _rendered(payload)[".github/workflows/ci.yml"].decode()
    document = yaml.safe_load(ci)
    assert document["jobs"]["test"]["strategy"]["matrix"]["python-version"] == [
        "3.12",
        "3.13",
        "3.14",
    ]


# --- derived host identity ----------------------------------------------


def test_codeowners_is_derived_from_the_organisation_option() -> None:
    codeowners = _rendered(_payload())[".github/CODEOWNERS"].decode()
    assert f"* @{_ORG}/reference-project-maintainers" in codeowners


def test_host_links_land_only_when_github_is_selected() -> None:
    with_github = _rendered(_payload())
    without = _rendered(_payload(platforms=(), github_options=None))

    pyproject = with_github["pyproject.toml"].decode()
    assert "[project.urls]" in pyproject
    assert f"https://github.com/{_ORG}/reference-project" in pyproject
    assert "[project.urls]" not in without["pyproject.toml"].decode()

    assert "advisories/new" in with_github["SECURITY.md"].decode()
    assert "advisories/new" not in without["SECURITY.md"].decode()

    assert f"github.com/{_ORG}/reference-project" in with_github["README.md"].decode()
    assert f"github.com/{_ORG}/reference-project" in (
        with_github["CONTRIBUTING.md"].decode()
    )


# --- failure taxonomy --------------------------------------------------


def test_missing_organisation_option_rejects_as_validate() -> None:
    payload = _payload(github_options={})
    spec = parse_project_spec(payload)
    for call in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as caught:
            call(spec)
        assert caught.value.code is EngineErrorCode.INVALID_COMPONENT_OPTIONS
        assert caught.value.operation == "validate"


# --- own-published points ------------------------------------------------


def test_github_publishes_ci_jobs_and_ci_steps_on_its_own_content() -> None:
    manifest = load_component_manifest(_COMPONENTS_ROOT / "github" / "component.toml")
    published = {point.id for point in manifest.extension_points}
    assert published == {"ci-jobs", "ci-steps"}
    for point in manifest.extension_points:
        assert point.content == "content/.github/workflows/ci.yml.jinja"


def test_empty_ci_points_render_zero_bytes_and_stay_valid_yaml() -> None:
    ci = _rendered(_payload())[".github/workflows/ci.yml"].decode()
    assert "forge:extension" not in ci
    document = yaml.safe_load(ci)
    # The test job ends after `poe test`; no dangling `ci-steps` fragment.
    steps = document["jobs"]["test"]["steps"]
    assert steps[-1]["run"] == "uv run poe test"


def test_foundation_still_owns_the_extended_files() -> None:
    plan = plan_generation(parse_project_spec(_payload()))
    by_target = {item.target: item for item in plan.files}
    for target in ("pyproject.toml", "README.md", "CONTRIBUTING.md", "SECURITY.md"):
        assert isinstance(by_target[target].owner, FoundationOwner)
        contributors = {
            extension.component_id for extension in by_target[target].extensions
        }
        assert "github" in contributors
