"""Tests for forge_template.schema against the real copier.yml and template/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from forge_template.schema import (
    check_all,
    check_computed,
    check_layout,
    check_versioning_indirection,
    load_schema,
    render_default,
)


@pytest.fixture(scope="module")
def cfg() -> dict[str, Any]:
    return load_schema()


def test_real_schema_has_no_errors(cfg: dict[str, Any]) -> None:
    """The actual copier.yml must pass every check -- this is what CI runs."""
    assert check_all(cfg) == []


def test_check_layout_passes_on_real_schema(cfg: dict[str, Any]) -> None:
    assert check_layout(cfg) == []


def test_check_layout_flags_wrong_subdirectory() -> None:
    errors = check_layout({"_subdirectory": "not-template", "_answers_file": "x"})
    assert any("_subdirectory" in e for e in errors)


def test_check_layout_flags_missing_answers_file() -> None:
    errors = check_layout({"_subdirectory": "template"})
    assert any("_answers_file" in e for e in errors)


def test_check_computed_passes_on_real_schema(cfg: dict[str, Any]) -> None:
    assert check_computed(cfg) == []


def test_check_computed_flags_missing_default() -> None:
    errors = check_computed({"some_computed_value": {"type": "str", "when": False}})
    assert len(errors) == 1
    assert "some_computed_value" in errors[0]


def test_check_computed_ignores_conditional_when_strings() -> None:
    # `when: "{{ ... }}"` (a real conditional, not a computed value) must
    # not be treated as a computed-value question.
    errors = check_computed(
        {
            "initial_version": {
                "type": "str",
                "when": "{{ versioning_resolved == 'static' }}",
            }
        }
    )
    assert errors == []


def test_check_versioning_indirection_passes_on_real_template() -> None:
    assert check_versioning_indirection() == []


def test_check_versioning_indirection_flags_bare_reference(tmp_path: Path) -> None:
    bad = tmp_path / "pyproject.toml.jinja"
    bad.write_text(
        "{% if versioning == 'vcs' %}\ndynamic = [\"version\"]\n{% endif %}\n"
    )
    errors = check_versioning_indirection(tmp_path)
    assert len(errors) == 1
    assert "pyproject.toml.jinja:1" in errors[0]


def test_check_versioning_indirection_allows_resolved_reference(tmp_path: Path) -> None:
    ok = tmp_path / "pyproject.toml.jinja"
    ok.write_text(
        "{% if versioning_resolved == 'vcs' %}\ndynamic = [\"version\"]\n{% endif %}\n"
    )
    assert check_versioning_indirection(tmp_path) == []


# -----------------------------------------------------------------------------
# The computed defaults themselves, not just that they exist.
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("python_min_version", "python_version", "expected"),
    [
        ("3.11", "3.13", ["3.11", "3.12", "3.13"]),
        ("3.13", "3.13", ["3.13"]),
        ("3.11", "3.14", ["3.11", "3.12", "3.13", "3.14"]),
    ],
)
def test_python_matrix_slices_correctly(
    cfg: dict[str, Any],
    python_min_version: str,
    python_version: str,
    expected: list[str],
) -> None:
    rendered = render_default(
        cfg["python_matrix"],
        {
            "python_all": ["3.11", "3.12", "3.13", "3.14"],
            "python_min_version": python_min_version,
            "python_version": python_version,
        },
    )
    assert rendered == str(expected).replace("'", '"')


@pytest.mark.parametrize(
    ("build_backend", "versioning", "expected"),
    [
        ("uv_build", "static", "static"),
        ("uv_build", "vcs", "static"),  # the invalid pair -- must collapse
        ("hatchling", "static", "static"),
        ("hatchling", "vcs", "vcs"),
    ],
)
def test_versioning_resolved_collapses_uv_build_to_static(
    cfg: dict[str, Any], build_backend: str, versioning: str, expected: str
) -> None:
    rendered = render_default(
        cfg["versioning_resolved"],
        {"build_backend": build_backend, "versioning": versioning},
    )
    assert rendered == expected
