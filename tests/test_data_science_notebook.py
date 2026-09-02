"""Fast proofs for the Data Science starter notebook and artefact layout.

The real kernel execution lives in the slow ``archetype``-marked
``tests/test_data_science_build.py`` (its generated ``poe check`` now runs
``notebook:check`` over this notebook). This module carries the checks that
need ``nbformat`` or ``ruff`` rather than a running kernel -- see
docs/notebook-data-and-model-safeguards.md and ADR 0054.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import cast

import nbformat
import pytest

from forge_template import parse_project_spec, render_project

_ROOT = Path(__file__).parents[1]
_DATA_SCIENCE = _ROOT / "src" / "forge_template" / "components" / "data-science"
_NOTEBOOK_TARGET = "notebooks/getting-started.ipynb"
_VALIDATOR = (
    _DATA_SCIENCE.parent / "jupyter" / "content" / "scripts" / "check_notebooks.py"
)

_PACKAGE_NAME = "churn_model"

# Nothing in a tracked example may look like a key, an embedded blob, or a
# hard-coded credential -- docs/notebook-data-and-model-safeguards.md.
_PAYLOAD_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"data:[^;]+;base64,"),
    re.compile(r"(?i)\b(password|secret|token|api[_-]?key)\b\s*=\s*['\"][^'\"]+['\"]"),
)


def _payload(*, capabilities: list[str] | None = None) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Churn Model",
            "package_name": _PACKAGE_NAME,
            "repository_name": "churn-model",
            "description": "Churn prediction work.",
            "licence": "mit",
            "authors": [{"name": "Test User", "email": "test@example.invalid"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": "data-science",
            "capabilities": ["jupyter"] if capabilities is None else capabilities,
            "platforms": [],
        },
        "component_options": {},
    }


def _render(capabilities: list[str] | None = None) -> dict[str, bytes]:
    spec = parse_project_spec(_payload(capabilities=capabilities))
    return {item.target: item.content for item in render_project(spec).files}


def _stage(root: Path, files: dict[str, bytes]) -> None:
    for target, content in files.items():
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _load_validator(tmp_path: Path) -> ModuleType:
    # Load a copy, never the source-tree file -- executing it there would leave
    # a __pycache__ entry inside the jupyter component and trip
    # test_jupyter_capability.py::test_jupyter_component_owns_no_notebook.
    copy = tmp_path / "check_notebooks.py"
    shutil.copyfile(_VALIDATOR, copy)
    spec = importlib.util.spec_from_file_location("_ds_notebook_validator", copy)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _notebook(files: dict[str, bytes]) -> nbformat.NotebookNode:
    parsed = nbformat.reads(  # type: ignore[no-untyped-call]
        files[_NOTEBOOK_TARGET].decode(), as_version=4
    )
    return cast(nbformat.NotebookNode, parsed)


def _code_source(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")


def test_notebook_is_structurally_valid_and_output_free() -> None:
    """The three cleanliness assertions check_notebooks.py makes, run without
    a kernel: no execution count, no stored output, no stored widget state."""
    notebook = _notebook(_render())
    nbformat.validate(notebook)

    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code_cells, "the starter notebook must exercise the package"
    for cell in code_cells:
        assert cell.execution_count is None
        assert cell.outputs == []
    assert "widgets" not in notebook.metadata


@pytest.mark.parametrize(
    "capabilities",
    [
        pytest.param(["jupyter"], id="jupyter-only"),
        pytest.param(["jupyter", "scientific-python"], id="with-scientific-python"),
    ],
)
def test_rendered_project_passes_ruff(capabilities: list[str], tmp_path: Path) -> None:
    """Acceptance criterion 2: the notebook passes Ruff -- and does so without
    Scientific Python selected. Ruff reads the generated pyproject.toml, so
    this is the generated project's own rule set, over its .ipynb by default."""
    _stage(tmp_path, _render(capabilities=capabilities))

    for command in (
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
    ):
        result = subprocess.run(
            command, cwd=tmp_path, capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_notebook_imports_only_the_package_and_the_standard_library() -> None:
    """docs/notebook-data-and-model-safeguards.md: the starter notebook uses
    only the generated package and modules that ship with Python."""
    notebook = _notebook(_render())
    tree = ast.parse(_code_source(notebook))

    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots
    allowed = {_PACKAGE_NAME} | set(sys.stdlib_module_names)
    assert imported_roots <= allowed, imported_roots - allowed


def test_notebook_and_fragments_carry_no_payload() -> None:
    """Acceptance criterion 4: no generated example contains a secret,
    credential, binary model, or embedded dataset."""
    authored = (
        _DATA_SCIENCE / "content" / "notebooks" / "getting-started.ipynb.jinja",
        _DATA_SCIENCE / "extensions" / "readme-project-shape.md.jinja",
        _DATA_SCIENCE / "extensions" / "gitignore-project-shape.jinja",
    )
    for path in authored:
        text = path.read_text(encoding="utf-8")
        for pattern in _PAYLOAD_PATTERNS:
            assert not pattern.search(text), (path.name, pattern.pattern)

    # No binary model or embedded dataset anywhere in the component tree.
    for path in sorted(_DATA_SCIENCE.rglob("*")):
        if not path.is_file():
            continue
        path.read_text(encoding="utf-8")  # raises if it is not UTF-8 text
        assert path.stat().st_size < 8192, path


def test_notebook_discovery_excludes_the_ignored_working_trees(
    tmp_path: Path,
) -> None:
    """A stray notebook saved into an ignored tree is never discovered, so it
    is never validated or executed -- docs/notebook-data-and-model-safeguards.md."""
    project = tmp_path / "project"
    project.mkdir()
    _stage(project, _render())
    for stray in ("data/raw/scratch.ipynb", "artifacts/report.ipynb"):
        path = project / stray
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    validator = _load_validator(tmp_path)
    discovered = validator.discover_notebooks(project)

    assert [path.relative_to(project).as_posix() for path in discovered] == [
        _NOTEBOOK_TARGET
    ]
