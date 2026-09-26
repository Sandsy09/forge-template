"""Regression tests for scripts/labels.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("labels", ROOT / "scripts/labels.py")
assert _SPEC is not None
assert _SPEC.loader is not None
labels = importlib.util.module_from_spec(_SPEC)
# Registered first: dataclasses looks the module up by name.
sys.modules["labels"] = labels
_SPEC.loader.exec_module(labels)


def test_current_labels_decode_gh_output_as_utf8(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`gh` emits UTF-8; a locale decode turned an em dash into mojibake."""
    payload = json.dumps(
        [{"name": "roadmap:22", "color": "AABBCC", "description": "Stage — 22"}],
        ensure_ascii=False,
    )
    seen: dict[str, Any] = {}

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout=payload, stderr="")

    monkeypatch.setattr(labels.subprocess, "run", fake_run)
    result = labels.current_labels(None)
    assert seen["encoding"] == "utf-8"
    assert result["roadmap:22"].description == "Stage — 22"
    assert result["roadmap:22"].color == "aabbcc"


def test_manifest_declares_every_roadmap_stage_label() -> None:
    """Stages 22 to 29 each have a shared `roadmap:N` label."""
    desired = labels.desired_labels(labels.load_manifest())
    for stage in range(15, 30):
        assert f"roadmap:{stage}" in desired
