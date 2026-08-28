"""Tests for the public generated-project validation boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_template.engine as engine_module
from forge_template import (
    EngineErrorCode,
    ForgeEngineError,
    GenerationPlan,
    PlannedFile,
    ProjectSpec,
    RenderedFile,
    RenderedProject,
    parse_project_spec,
    render_project,
    validate_rendered_project,
)

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"


def _spec() -> ProjectSpec:
    return parse_project_spec(
        {
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
                "capabilities": [],
                "platforms": [],
            },
            "component_options": {"library": {"build_backend": "uv_build"}},
        }
    )


def _pyproject(
    *,
    name: object = "example-project",
    requires_python: object = ">=3.11",
) -> bytes:
    def toml_value(value: object) -> str:
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, list):
            return "[" + ", ".join(f'"{item}"' for item in value) + "]"
        return str(value)

    return (
        "[project]\n"
        f"name = {toml_value(name)}\n"
        f"requires-python = {toml_value(requires_python)}\n"
    ).encode()


def _rendered_project(
    *,
    planned_targets: tuple[str, ...] = ("pyproject.toml",),
    rendered_files: tuple[tuple[str, bytes], ...] | None = None,
) -> RenderedProject:
    if rendered_files is None:
        rendered_files = (("pyproject.toml", _pyproject()),)
    return RenderedProject(
        plan=GenerationPlan(
            component_order=("library",),
            files=tuple(
                PlannedFile(target=target, owner_component_id="library")
                for target in planned_targets
            ),
        ),
        files=tuple(
            RenderedFile(target=target, content=content)
            for target, content in rendered_files
        ),
    )


def _error(project: RenderedProject) -> ForgeEngineError:
    with pytest.raises(ForgeEngineError) as exc_info:
        validate_rendered_project(_spec(), project)
    error = exc_info.value
    assert error.code is EngineErrorCode.GENERATED_PROJECT_INVALID
    assert error.operation == "validate-output"
    assert error.as_dict()["code"] == "generated-project-invalid"
    return error


def test_valid_project_returns_the_same_immutable_result(tmp_path: Path) -> None:
    project = _rendered_project()

    assert validate_rendered_project(_spec(), project) is project
    assert list(tmp_path.iterdir()) == []


def test_render_project_invokes_public_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", FIXTURES)
    calls: list[RenderedProject] = []
    validator = validate_rendered_project

    def record_validation(
        spec: ProjectSpec,
        project: RenderedProject,
    ) -> RenderedProject:
        calls.append(project)
        return validator(spec, project)

    monkeypatch.setattr(engine_module, "validate_rendered_project", record_validation)

    rendered = render_project(_spec())

    assert calls == [rendered]


@pytest.mark.parametrize(
    ("project", "expected_code"),
    [
        (
            _rendered_project(
                planned_targets=("pyproject.toml", "pyproject.toml"),
            ),
            "duplicate-plan-target",
        ),
        (
            _rendered_project(
                planned_targets=("z.txt", "pyproject.toml"),
                rendered_files=(("pyproject.toml", _pyproject()), ("z.txt", b"z")),
            ),
            "unordered-plan-targets",
        ),
        (
            _rendered_project(
                rendered_files=(
                    ("pyproject.toml", _pyproject()),
                    ("pyproject.toml", _pyproject()),
                ),
            ),
            "duplicate-rendered-target",
        ),
        (
            _rendered_project(
                planned_targets=("pyproject.toml", "z.txt"),
                rendered_files=(("z.txt", b"z"), ("pyproject.toml", _pyproject())),
            ),
            "unordered-rendered-targets",
        ),
        (
            _rendered_project(
                planned_targets=("README.md", "pyproject.toml"),
            ),
            "missing-rendered-file",
        ),
        (
            _rendered_project(
                rendered_files=(
                    ("README.md", b"readme"),
                    ("pyproject.toml", _pyproject()),
                ),
            ),
            "unexpected-rendered-file",
        ),
    ],
)
def test_plan_and_rendered_targets_must_match_exactly(
    project: RenderedProject,
    expected_code: str,
) -> None:
    error = _error(project)

    assert expected_code in {detail.code for detail in error.details}


def test_pyproject_is_a_universal_required_output() -> None:
    project = _rendered_project(
        planned_targets=("README.md",),
        rendered_files=(("README.md", b"readme"),),
    )

    error = _error(project)

    assert [detail.code for detail in error.details] == ["missing-pyproject"]
    assert error.details[0].path == ("pyproject.toml",)


@pytest.mark.parametrize(
    ("content", "expected_code"),
    [
        (b"\xff", "invalid-pyproject-encoding"),
        (b"[project\n", "invalid-pyproject-toml"),
        (b'name = "example-project"\n', "invalid-project-table"),
        (b'[project]\nname = ""\nrequires-python = ">=3.11"\n', "invalid-project-name"),
        (
            b'[project]\nname = "not a valid name!"\nrequires-python = ">=3.11"\n',
            "invalid-project-name",
        ),
        (
            b'[project]\nname = "different"\nrequires-python = ">=3.11"\n',
            "project-name-mismatch",
        ),
        (
            b'[project]\nname = "example-project"\nrequires-python = ["3.11"]\n',
            "invalid-requires-python",
        ),
        (
            b'[project]\nname = "example-project"\nrequires-python = "not valid"\n',
            "invalid-requires-python",
        ),
    ],
)
def test_pyproject_structure_and_metadata_are_validated(
    content: bytes,
    expected_code: str,
) -> None:
    error = _error(_rendered_project(rendered_files=(("pyproject.toml", content),)))

    assert expected_code in {detail.code for detail in error.details}
    assert all(detail.path[0] == "pyproject.toml" for detail in error.details)


def test_distribution_name_uses_standard_normalisation() -> None:
    project = _rendered_project(
        rendered_files=(("pyproject.toml", _pyproject(name="example_project")),)
    )

    assert validate_rendered_project(_spec(), project) is project


@pytest.mark.parametrize(
    "requires_python",
    [">=3.12", ">=3.11,<4", ">=3.11,!=3.12", "~=3.11"],
)
def test_python_requirement_is_the_exact_selected_lower_bound(
    requires_python: str,
) -> None:
    project = _rendered_project(
        rendered_files=(
            ("pyproject.toml", _pyproject(requires_python=requires_python)),
        )
    )

    error = _error(project)

    assert "python-requires-mismatch" in {detail.code for detail in error.details}


def test_forge_markers_fail_but_literal_downstream_syntax_is_allowed() -> None:
    marker = _rendered_project(
        planned_targets=("README.md", "pyproject.toml"),
        rendered_files=(
            ("README.md", b"[[forge:extension owner-point]]\n"),
            ("pyproject.toml", _pyproject()),
        ),
    )
    error = _error(marker)
    assert error.details[0].code == "unresolved-extension-marker"
    assert error.details[0].path == ("README.md",)

    literal = _rendered_project(
        planned_targets=("README.md", "pyproject.toml"),
        rendered_files=(
            ("README.md", b"{{ downstream_variable }}\n{% downstream %}\n"),
            ("pyproject.toml", _pyproject()),
        ),
    )
    assert validate_rendered_project(_spec(), literal) is literal


def test_failures_are_aggregated_and_deterministically_ordered() -> None:
    project = _rendered_project(
        planned_targets=("z.txt", "pyproject.toml", "z.txt"),
        rendered_files=(
            ("z.txt", b"[[forge:extension point]]\n"),
            ("extra.txt", b"extra"),
            ("pyproject.toml", _pyproject(name="different")),
        ),
    )

    error = _error(project)
    keys = [
        (tuple(str(part) for part in detail.path), detail.code, detail.message)
        for detail in error.details
    ]

    assert keys == sorted(keys)
    assert len(error.details) >= 5
    assert error.as_dict()["details"] == [
        detail.model_dump(mode="json") for detail in error.details
    ]
