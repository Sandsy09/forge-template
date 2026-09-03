"""Render-level validation for the Data Science capability compositions.

FT-12.03 / ADR 0055. The slow build/install/notebook checks live in the
``archetype``-marked ``tests/test_data_science_endpoints.py``; this module
carries the fast proofs -- deterministic planning and rendering across both
valid compositions, the documented rejections with an archetype in play, no
Forge dependency in any generated project, and a byte-level regression pin on
``library`` and ``cli`` output. See docs/data-science-validation.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

import forge_template.engine as engine_module
from forge_template import (
    ComponentOwner,
    EngineErrorCode,
    ForgeEngineError,
    FoundationOwner,
    parse_project_spec,
    plan_generation,
    render_project,
)

_ROOT = Path(__file__).parents[1]
_PRODUCTION_COMPONENTS = _ROOT / "src" / "forge_template" / "components"
_DIGESTS = Path(__file__).parent / "fixtures" / "archetype_regression" / "digests.json"

_VALID_COMPOSITIONS = [
    pytest.param(("jupyter",), id="jupyter"),
    pytest.param(("jupyter", "scientific-python"), id="jupyter+scientific-python"),
]
_REGRESSION_SELECTIONS: list[tuple[str, ...]] = [
    (),
    ("jupyter",),
    ("scientific-python",),
    ("jupyter", "scientific-python"),
]


def _payload(
    *,
    archetype: str = "data-science",
    capabilities: tuple[str, ...] = ("jupyter",),
    component_options: dict[str, Any] | None = None,
) -> dict[str, object]:
    options: dict[str, Any] = dict(component_options or {})
    if archetype == "library" and "library" not in options:
        options["library"] = {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        }
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
            "archetype": archetype,
            "capabilities": list(capabilities),
            "platforms": [],
        },
        "component_options": options,
    }


def _render_map(payload: dict[str, object]) -> dict[str, bytes]:
    spec = parse_project_spec(payload)
    return {item.target: item.content for item in render_project(spec).files}


def _digest_map(files: dict[str, bytes]) -> dict[str, str]:
    return {
        target: hashlib.sha256(content).hexdigest()
        for target, content in sorted(files.items())
    }


# --- Both valid compositions plan and render deterministically --------------


@pytest.mark.parametrize("capabilities", _VALID_COMPOSITIONS)
def test_valid_composition_plans_with_selected_owners_only(
    capabilities: tuple[str, ...],
) -> None:
    spec = parse_project_spec(_payload(capabilities=capabilities))
    plan = plan_generation(spec)

    assert plan.component_order == ("data-science", *sorted(capabilities))

    selected = {"data-science", *capabilities}
    for item in plan.files:
        assert isinstance(item.owner, FoundationOwner) or (
            isinstance(item.owner, ComponentOwner) and item.owner.id in selected
        ), item.target

    by_target = {item.target: item for item in plan.files}
    assert by_target["notebooks/getting-started.ipynb"].owner == ComponentOwner(
        id="data-science"
    )

    files = _render_map(_payload(capabilities=capabilities))
    tomllib.loads(files["pyproject.toml"].decode())
    assert ("scripts/check_notebooks.py" in files) is ("jupyter" in capabilities)
    assert ("tests/test_scientific_python.py" in files) is (
        "scientific-python" in capabilities
    )


@pytest.mark.parametrize("capabilities", _VALID_COMPOSITIONS)
def test_render_is_invariant_to_repetition_and_capability_order(
    capabilities: tuple[str, ...],
) -> None:
    first = _render_map(_payload(capabilities=capabilities))
    again = _render_map(_payload(capabilities=capabilities))
    reversed_order = _render_map(_payload(capabilities=tuple(reversed(capabilities))))

    assert first == again == reversed_order


@pytest.mark.parametrize("capabilities", _VALID_COMPOSITIONS)
def test_render_is_invariant_to_catalogue_filesystem_layout(
    capabilities: tuple[str, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The engine sorts ``component.toml`` paths before loading them
    (engine.py ``_load_catalogue``). Rendering against a fresh copy of the
    production catalogue -- a different on-disk inode order -- must produce
    byte-identical output. Only the private test seam moves; the installed
    Foundation source stays live."""
    installed = _render_map(_payload(capabilities=capabilities))

    overlay = tmp_path / "components"
    shutil.copytree(_PRODUCTION_COMPONENTS, overlay)
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", overlay)
    monkeypatch.setattr(engine_module, "_FOUNDATION_ROOT_OVERRIDE", None)

    assert _render_map(_payload(capabilities=capabilities)) == installed


@pytest.mark.parametrize("floor", ["3.11", "3.14"])
def test_rendered_python_content_is_ruff_format_clean_at_every_floor(
    floor: str, tmp_path: Path
) -> None:
    """Invariant 1 for the richest composition, whatever supported floor the
    owner picks. 3.14 in particular flips ``target-version`` to ``py314``,
    which changes how ruff formats ``except`` groups (PEP 758) -- generated
    content must stay clean at that target too."""
    payload = _payload(capabilities=("jupyter", "scientific-python"))
    payload["python"] = {"minimum": floor, "development": floor}
    for target, content in _render_map(payload).items():
        path = tmp_path / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_render_is_invariant_to_pythonhashseed() -> None:
    """docs/composition-order.md names PYTHONHASHSEED explicitly. A single
    pytest process has one fixed seed, so vary it across subprocesses that
    each render the richest composition and hash the file map."""
    script = (
        "import hashlib, json;"
        "from forge_template import parse_project_spec, render_project;"
        "spec = parse_project_spec({"
        "'protocol_version': 1,"
        "'project': {'name': 'Churn Model', 'package_name': 'churn_model',"
        " 'repository_name': 'churn-model', 'description': 'x', 'licence': 'mit',"
        " 'authors': [{'name': 'Test User'}]},"
        "'python': {'minimum': '3.11', 'development': '3.13'},"
        "'components': {'archetype': 'data-science',"
        " 'capabilities': ['jupyter', 'scientific-python'], 'platforms': []},"
        "'component_options': {}});"
        "files = {i.target: i.content.hex() for i in render_project(spec).files};"
        "print(hashlib.sha256("
        "json.dumps(files, sort_keys=True).encode()).hexdigest())"
    )
    hashes = set()
    for seed in ("0", "1", "42", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=_ROOT,
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        )
        hashes.add(result.stdout.strip())

    assert len(hashes) == 1, hashes


# --- The documented rejections fail closed, with an archetype in play -------

_REJECTIONS: list[tuple[str, dict[str, Any], EngineErrorCode, str]] = [
    (
        "data-science-without-jupyter",
        {"capabilities": ()},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "data-science-with-scientific-python-only",
        {"capabilities": ("scientific-python",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "jupyter-listed-twice",
        {"capabilities": ("jupyter", "jupyter")},
        EngineErrorCode.INVALID_PROJECT_SPEC,
        "parse",
    ),
    (
        "second-archetype-as-capability",
        {"capabilities": ("jupyter", "library")},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "unknown-component-alongside-jupyter",
        {"capabilities": ("jupyter", "does-not-exist")},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "data-science-given-as-a-capability",
        {"archetype": "library", "capabilities": ("data-science",)},
        EngineErrorCode.INVALID_COMPONENT_SELECTION,
        "validate",
    ),
    (
        "options-for-optionless-data-science",
        {"component_options": {"data-science": {"anything": "x"}}},
        EngineErrorCode.INVALID_COMPONENT_OPTIONS,
        "validate",
    ),
]


@pytest.mark.parametrize(
    ("_name", "kwargs", "code", "operation"),
    _REJECTIONS,
    ids=[row[0] for row in _REJECTIONS],
)
def test_documented_rejection_fails_closed_before_rendering(
    _name: str,
    kwargs: dict[str, Any],
    code: EngineErrorCode,
    operation: str,
) -> None:
    for sink in (plan_generation, render_project):
        with pytest.raises(ForgeEngineError) as exc_info:
            sink(parse_project_spec(_payload(**kwargs)))
        error = exc_info.value
        assert error.code is code
        assert error.operation == operation
        assert error.operation != "render"
        assert error.details
        json.dumps(error.as_dict())


# --- No valid composition needs a Forge repository -------------------------


@pytest.mark.parametrize("capabilities", _VALID_COMPOSITIONS)
def test_no_valid_composition_declares_a_forge_dependency(
    capabilities: tuple[str, ...],
) -> None:
    files = _render_map(_payload(capabilities=capabilities))
    pyproject = tomllib.loads(files["pyproject.toml"].decode())

    declared = [
        *pyproject["project"].get("dependencies", []),
        *(
            requirement
            for group in pyproject.get("dependency-groups", {}).values()
            for requirement in group
            if isinstance(requirement, str)
        ),
    ]
    assert all(
        not requirement.lower().startswith(("forge-template", "create-forge"))
        for requirement in declared
    ), declared

    for target, content in files.items():
        if target.endswith((".py", ".ipynb")):
            assert b"forge_template" not in content, target
            assert b"forge-template" not in content, target


# --- Library and CLI output is byte-pinned across capability selections ----


def test_library_and_cli_output_matches_recorded_digests(update_goldens: bool) -> None:
    """FT-12.03 regression pin: every ``library`` and ``cli`` target, across
    all four capability selections, hashes to a recorded value. Regenerate
    with ``--update-goldens`` and review the diff -- see
    docs/composition-fixtures.md."""
    actual = {
        f"{archetype}:{'+'.join(capabilities) or 'none'}": _digest_map(
            _render_map(_payload(archetype=archetype, capabilities=capabilities))
        )
        for archetype in ("library", "cli")
        for capabilities in _REGRESSION_SELECTIONS
    }

    if update_goldens:
        _DIGESTS.parent.mkdir(parents=True, exist_ok=True)
        # write_bytes, not write_text: keep the fixture LF on every platform so
        # a Windows regeneration produces no spurious CRLF diff.
        _DIGESTS.write_bytes(
            (json.dumps(actual, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
        pytest.skip(f"updated regression digests: {_DIGESTS}")

    expected = json.loads(_DIGESTS.read_text(encoding="utf-8"))
    assert actual == expected
