"""Tests for forge_template.schema against the real copier.yml and template/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from forge_template.schema import (
    check_all,
    check_computed,
    check_conditional_filenames,
    check_layout,
    check_question_usage,
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
# Question <-> template/** cross-reference.
# -----------------------------------------------------------------------------


def test_check_question_usage_passes_on_real_tree(cfg: dict[str, Any]) -> None:
    assert check_question_usage(cfg) == []


def test_check_question_usage_flags_unreferenced_question(tmp_path: Path) -> None:
    cfg = {"never_used": {"type": "str", "default": ""}}
    (tmp_path / "file.txt.jinja").write_text("no jinja here\n")
    errors = check_question_usage(cfg, tmp_path)
    assert any("never_used" in e and "never referenced" in e for e in errors)


def test_check_question_usage_flags_undeclared_reference(tmp_path: Path) -> None:
    (tmp_path / "file.txt.jinja").write_text("{{ mystery_var }}\n")
    errors = check_question_usage({}, tmp_path)
    assert any("mystery_var" in e and "not declared" in e for e in errors)


def test_check_question_usage_ignores_loop_and_set_locals(tmp_path: Path) -> None:
    # `v` and `py_target` are loop/set-scoped locals, not real questions --
    # mirrors the real `{% for v in python_matrix %}` / `{% set py_target ...`
    # usage in template/pyproject.toml.jinja.
    cfg = {"python_matrix": {"type": "json", "when": False, "default": "[]"}}
    (tmp_path / "file.txt.jinja").write_text(
        "{%- set py_target = 'x' -%}\n{{ py_target }}\n"
        "{%- for v in python_matrix %}{{ v }}{% endfor -%}\n"
    )
    assert check_question_usage(cfg, tmp_path) == []


def test_check_question_usage_ignores_computed_inputs(tmp_path: Path) -> None:
    # python_all and versioning feed computed defaults but are never read
    # directly by template/** -- see _COMPUTED_INPUTS.
    cfg = {
        "python_all": {"type": "json", "when": False, "default": "[]"},
        "versioning": {"type": "str", "default": "static"},
    }
    (tmp_path / "file.txt.jinja").write_text("no jinja here\n")
    assert check_question_usage(cfg, tmp_path) == []


# -----------------------------------------------------------------------------
# Conditional filenames.
# -----------------------------------------------------------------------------


def test_check_conditional_filenames_passes_on_real_tree(cfg: dict[str, Any]) -> None:
    assert check_conditional_filenames(cfg) == []


def test_check_conditional_filenames_flags_partial_render(tmp_path: Path) -> None:
    cfg = {"toggle": {"type": "bool", "default": False}}
    (tmp_path / "{% if toggle %} bad name {% endif %}.jinja").write_text("x")
    errors = check_conditional_filenames(cfg, tmp_path)
    assert len(errors) == 1
    assert "neither a valid filename nor empty" in errors[0]


def test_check_conditional_filenames_allows_clean_toggle(tmp_path: Path) -> None:
    cfg = {"toggle": {"type": "bool", "default": False}}
    (tmp_path / "{% if toggle %}name.txt{% endif %}.jinja").write_text("x")
    assert check_conditional_filenames(cfg, tmp_path) == []


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
