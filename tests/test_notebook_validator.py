"""Executable contract tests for Jupyter's generated notebook validator."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import cast

import nbformat
import pytest
from nbclient.exceptions import CellExecutionError, CellTimeoutError

_VALIDATOR = (
    Path(__file__).parents[1]
    / "src"
    / "forge_template"
    / "components"
    / "jupyter"
    / "content"
    / "scripts"
    / "check_notebooks.py"
)


@pytest.fixture
def validator(tmp_path: Path) -> Iterator[ModuleType]:
    validator_path = tmp_path / "check_notebooks.py"
    shutil.copyfile(_VALIDATOR, validator_path)
    spec = importlib.util.spec_from_file_location(
        "jupyter_notebook_validator", validator_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def _write_notebook(path: Path, cells: list[object] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    notebook = nbformat.v4.new_notebook(  # type: ignore[no-untyped-call]
        cells=cells or []
    )
    nbformat.write(notebook, path)  # type: ignore[no-untyped-call]


def test_empty_project_passes_without_creating_temporary_state(
    validator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected_temporary_directory(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("empty notebook set must not create a temporary directory")

    monkeypatch.setattr(
        validator.tempfile, "TemporaryDirectory", unexpected_temporary_directory
    )

    assert validator.validate_notebooks(tmp_path) == ()


def test_discovery_prunes_only_the_accepted_paths(
    validator: ModuleType, tmp_path: Path
) -> None:
    included = (
        "examples/two.ipynb",
        "nested/models/three.ipynb",
        "notebooks/one.ipynb",
    )
    excluded = (
        ".git/ignored.ipynb",
        ".venv/ignored.ipynb",
        "notebooks/.ipynb_checkpoints/ignored.ipynb",
        "data/raw/ignored.ipynb",
        "data/interim/ignored.ipynb",
        "data/processed/ignored.ipynb",
        "models/ignored.ipynb",
        "artifacts/ignored.ipynb",
    )
    for relative in (*included, *excluded):
        _write_notebook(tmp_path / relative)

    discovered = validator.discover_notebooks(tmp_path)

    assert (
        tuple(path.relative_to(tmp_path).as_posix() for path in discovered) == included
    )


def test_structural_failures_are_complete_safe_and_deterministic(
    validator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "c.ipynb").write_bytes(b"\xff")
    (tmp_path / "b.ipynb").write_text("not json", encoding="utf-8")
    (tmp_path / "a.ipynb").write_text(
        json.dumps({"nbformat": 4, "nbformat_minor": 5, "cells": "invalid"}),
        encoding="utf-8",
    )
    dirty = nbformat.v4.new_notebook(  # type: ignore[no-untyped-call]
        cells=[
            nbformat.v4.new_code_cell(  # type: ignore[no-untyped-call]
                "print('DO NOT LEAK')",
                execution_count=7,
                outputs=[
                    nbformat.v4.new_output(  # type: ignore[no-untyped-call]
                        "stream", text="DO NOT LEAK"
                    )
                ],
            )
        ],
        metadata={"widgets": {"DO NOT LEAK": {}}},
    )
    nbformat.write(dirty, tmp_path / "d.ipynb")  # type: ignore[no-untyped-call]

    monkeypatch.setattr(
        validator,
        "_execute_copy",
        lambda *args, **kwargs: pytest.fail("dirty notebooks must not execute"),
    )
    failures = validator.validate_notebooks(tmp_path)

    assert [(item.path, item.cell_index, item.code) for item in failures] == [
        ("a.ipynb", None, "invalid-notebook-schema"),
        ("b.ipynb", None, "invalid-notebook-json"),
        ("c.ipynb", None, "unreadable-notebook"),
        ("d.ipynb", None, "widget-state-present"),
        ("d.ipynb", 0, "cell-output-present"),
        ("d.ipynb", 0, "execution-count-present"),
    ]
    rendered = "\n".join(item.render() for item in failures)
    assert "DO NOT LEAK" not in rendered
    assert str(tmp_path) not in rendered


def test_clean_notebook_executes_without_changing_source(
    validator: ModuleType, tmp_path: Path
) -> None:
    notebook = tmp_path / "notebooks" / "clean.ipynb"
    _write_notebook(
        notebook,
        [
            nbformat.v4.new_code_cell(  # type: ignore[no-untyped-call]
                "value = 1 + 1\nassert value == 2"
            )
        ],
    )
    before = notebook.read_bytes()

    assert validator.validate_notebooks(tmp_path) == ()
    assert notebook.read_bytes() == before


def test_cell_failure_is_safe_and_preserves_source(
    validator: ModuleType, tmp_path: Path
) -> None:
    notebook = tmp_path / "failure.ipynb"
    _write_notebook(
        notebook,
        [
            nbformat.v4.new_code_cell(  # type: ignore[no-untyped-call]
                "raise ValueError('DO NOT LEAK')"
            )
        ],
    )
    before = notebook.read_bytes()

    failures = validator.validate_notebooks(tmp_path)

    assert len(failures) == 1
    failure = failures[0]
    assert (failure.path, failure.cell_index, failure.code) == (
        "failure.ipynb",
        0,
        "cell-execution-failed",
    )
    assert failure.exception_type == "ValueError"
    assert "DO NOT LEAK" not in failure.render()
    assert notebook.read_bytes() == before


@pytest.mark.parametrize(
    ("error", "expected_code", "starts_cell"),
    [
        (RuntimeError("unsafe kernel detail"), "kernel-unavailable", False),
        (CellTimeoutError("unsafe timeout detail"), "cell-execution-timeout", True),
        (
            CellExecutionError("unsafe traceback", "RuntimeError", "unsafe detail"),
            "cell-execution-failed",
            True,
        ),
    ],
)
def test_execution_failures_use_only_the_safe_surface(
    validator: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_code: str,
    starts_cell: bool,
) -> None:
    notebook = tmp_path / "execution.ipynb"
    _write_notebook(
        notebook,
        [nbformat.v4.new_code_cell("pass")],  # type: ignore[no-untyped-call]
    )
    copy = tmp_path / "copy.ipynb"
    copy.write_bytes(notebook.read_bytes())

    class FailingClient:
        def __init__(self, document: object, **kwargs: object) -> None:
            del document
            self.on_cell_start = cast(Callable[..., None], kwargs["on_cell_start"])

        def execute(self, **kwargs: object) -> None:
            del kwargs
            if starts_cell:
                self.on_cell_start(cell={}, cell_index=0)
            raise error

    monkeypatch.setattr(validator, "NotebookClient", FailingClient)

    failure = validator._execute_copy(copy, notebook, "execution.ipynb")

    assert failure is not None
    assert failure.code == expected_code
    assert failure.cell_index == (0 if starts_cell else None)
    assert "unsafe" not in failure.render()


def test_temporary_copy_failure_is_safe(
    validator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    notebook = tmp_path / "notebook.ipynb"
    _write_notebook(notebook)
    monkeypatch.setattr(
        validator.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: (_ for _ in ()).throw(OSError("unsafe absolute path")),
    )

    failures = validator.validate_notebooks(tmp_path)

    assert len(failures) == 1
    assert failures[0].code == "temporary-copy-failed"
    assert "unsafe" not in failures[0].render()


def test_temporary_cleanup_failure_is_safe(
    validator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    notebook = tmp_path / "notebook.ipynb"
    _write_notebook(notebook)
    temporary = tmp_path.parent / "cleanup-failure"

    class CleanupFailure:
        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def __enter__(self) -> str:
            temporary.mkdir(exist_ok=True)
            return str(temporary)

        def __exit__(self, *args: object) -> None:
            del args
            shutil.rmtree(temporary)
            raise OSError("unsafe cleanup detail")

    monkeypatch.setattr(validator.tempfile, "TemporaryDirectory", CleanupFailure)
    monkeypatch.setattr(validator, "_execute_copy", lambda *args: None)

    failures = validator.validate_notebooks(tmp_path)

    assert len(failures) == 1
    assert failures[0].code == "temporary-copy-failed"
    assert "unsafe" not in failures[0].render()


def test_first_execution_failure_stops_the_run(
    validator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("a.ipynb", "b.ipynb"):
        _write_notebook(tmp_path / name)
    executed: list[str] = []

    def fail_first(copy: Path, tracked: Path, relative: str) -> object:
        del copy, tracked
        executed.append(relative)
        return validator.Failure(relative, "kernel-unavailable")

    monkeypatch.setattr(validator, "_execute_copy", fail_first)

    failures = validator.validate_notebooks(tmp_path)

    assert executed == ["a.ipynb"]
    assert [(item.path, item.code) for item in failures] == [
        ("a.ipynb", "kernel-unavailable")
    ]


def test_diagnostic_control_characters_are_escaped(validator: ModuleType) -> None:
    failure = validator.Failure(
        "notebooks/bad\nname.ipynb",
        "cell-execution-failed",
        2,
        "Unsafe\nType",
    )

    rendered = failure.render()

    assert rendered.count("\n") == 0
    assert "\\u000a" in rendered
    assert "Unsafe" not in rendered
