"""Executable pin for docs/engine-default-parity.md (FT-15.01 / ADR 0058).

The parity matrix is only useful if it stays complete. This module derives the
expected row set from source -- every ``copier.yml`` question and every
``template/**`` path -- and fails ``uv run poe check`` when one has no row. It
also checks that every row is well formed, that no row cites an issue number
absent from the filed roadmap manifests, and that each ``shipped`` file row
agrees with a real ``library`` render.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from forge_template import parse_project_spec, render_project

ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs" / "engine-default-parity.md"
COPIER = ROOT / "copier.yml"
TEMPLATE = ROOT / "template"

_STATUSES = {"shipped", "gap", "excluded", "n/a"}
_DISPOSITIONS = {"provider", "client", "excluded"}
_TIERS = {"cutover-blocking", "deferred", "n/a"}
_NEEDS_ISSUE = "needs a bounded issue"
_SHIPPED_OWNER_WORDS = ("Foundation", "archetype", "engine", "library")
_CROSS_CUTTING_KEYS = {
    "operating-systems",
    "packaging-modes",
    "conditional-filenames",
}
_ISSUE_TOKEN = re.compile(r"(?:FT|CF)-(?:EPIC-)?\d{2}(?:\.\d{2})?")

_REFERENCE_PACKAGE = "refproj"
_REFERENCE_PAYLOAD: dict[str, object] = {
    "protocol_version": 1,
    "project": {
        "name": "Reference Project",
        "package_name": _REFERENCE_PACKAGE,
        "repository_name": "reference-project",
        "description": "Engine-default parity inventory fixture.",
        "licence": "mit",
        "authors": [{"name": "Test User"}],
    },
    "python": {"minimum": "3.11", "development": "3.13"},
    "components": {"archetype": "library", "capabilities": [], "platforms": []},
    "component_options": {
        "library": {
            "packaging_mode": "uv-build-static",
            "initial_version": "0.1.0",
        }
    },
}


def _doc_rows() -> list[dict[str, str]]:
    """Parse every seven-column, code-span-keyed row from the matrix."""
    rows: list[dict[str, str]] = []
    for raw in DOC.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 7:
            continue
        key = re.fullmatch(r"`([^`]+)`", cells[0])
        if key is None:
            continue
        rows.append(
            {
                "key": key.group(1),
                "copier_source": cells[1],
                "status": cells[2],
                "disposition": cells[3],
                "tier": cells[4],
                "owner": cells[5],
                "validation": cells[6],
            }
        )
    return rows


def _copier_questions() -> set[str]:
    """Top-level, non-underscore question keys in copier.yml."""
    text = COPIER.read_text(encoding="utf-8")
    return set(re.findall(r"(?m)^([a-z][a-z0-9_]*):\s*$", text))


def _copier_top_level() -> set[str]:
    """Every column-zero key, including the underscore-prefixed mechanics."""
    text = COPIER.read_text(encoding="utf-8")
    return set(re.findall(r"(?m)^([A-Za-z_][A-Za-z0-9_]*):", text))


def _template_keys() -> set[str]:
    """Every template/** path, with Jinja conditionals and .jinja collapsed."""
    keys: set[str] = set()
    for path in TEMPLATE.rglob("*"):
        if not path.is_file():
            continue
        rel = re.sub(r"\{%[^%]*%\}", "", path.relative_to(ROOT).as_posix())
        rel = re.sub(r"/+", "/", rel)
        if rel.endswith(".jinja"):
            rel = rel.removesuffix(".jinja")
        keys.add(rel)
    return keys


def _filed_issue_ids() -> set[str]:
    """Every filed issue identifier across both roadmap-v3/v4 packs."""
    ids: set[str] = set()
    for version in (3, 4):
        manifest_path = (
            ROOT / f"docs/roadmap-v{version}/github-issues/filing-manifest.json"
        )
        text = manifest_path.read_text(encoding="utf-8")
        manifest: dict[str, Any] = json.loads(text)
        ids.update(entry["id"] for entry in manifest["issues"])
    return ids


def _library_render_targets() -> set[str]:
    spec = parse_project_spec(_REFERENCE_PAYLOAD)
    return {item.target for item in render_project(spec).files}


def _github_render_targets() -> set[str]:
    """Targets from a ``library`` + ``github`` render -- the `github`-owned
    ``template/.github/**`` rows are ``shipped`` against this, not the
    library-only render (FT-17.02 / ADR 0063)."""
    payload: dict[str, object] = {
        **_REFERENCE_PAYLOAD,
        "components": {
            "archetype": "library",
            "capabilities": [],
            "platforms": ["github"],
        },
        "component_options": {
            "library": {
                "packaging_mode": "uv-build-static",
                "initial_version": "0.1.0",
            },
            "github": {"organisation": "reference-org"},
        },
    }
    spec = parse_project_spec(payload)
    return {item.target for item in render_project(spec).files}


def test_every_copier_question_and_template_file_has_a_row() -> None:
    """A question or templated file with no disposition fails the suite."""
    required = _copier_questions() | _template_keys()
    documented = {row["key"] for row in _doc_rows()}
    missing = sorted(required - documented)
    assert not missing, f"undocumented default-Copier surfaces: {missing}"


def test_no_row_describes_a_removed_surface() -> None:
    """A row keyed like a question or a template path must name a real one."""
    questions = _copier_top_level()
    templates = _template_keys()
    for row in _doc_rows():
        key = row["key"]
        if key.startswith("template/"):
            assert key in templates, f"stale template row: {key}"
        elif re.fullmatch(r"_?[a-z][a-z0-9_]*", key):
            assert key in questions or key in _CROSS_CUTTING_KEYS, (
                f"stale question row: {key}"
            )
        else:
            assert key in _CROSS_CUTTING_KEYS, f"unrecognised row key: {key}"


def test_every_row_is_well_formed() -> None:
    """Each row carries a valid status, disposition, tier, owner and check."""
    filed = _filed_issue_ids()
    rows = _doc_rows()
    assert len(rows) >= len(_copier_questions()) + len(_template_keys())
    for row in rows:
        key = row["key"]
        assert row["status"] in _STATUSES, f"{key}: bad status {row['status']!r}"
        assert row["disposition"] in _DISPOSITIONS, f"{key}: bad disposition"
        assert row["tier"] in _TIERS, f"{key}: bad tier {row['tier']!r}"
        assert row["validation"], f"{key}: empty validation requirement"

        owner = row["owner"]
        assert owner, f"{key}: empty implementation owner"
        cited = _ISSUE_TOKEN.findall(owner)
        for token in cited:
            assert token in filed, f"{key}: cites unfiled issue {token}"
        if not cited:
            assert _NEEDS_ISSUE in owner or any(
                word in owner for word in _SHIPPED_OWNER_WORDS
            ), f"{key}: owner names neither an issue, a component, nor the marker"

        if row["status"] == "gap":
            assert row["tier"] in {"cutover-blocking", "deferred"}, (
                f"{key}: a gap must carry a real tier"
            )


def test_shipped_file_rows_match_a_real_library_render() -> None:
    """Every template/** row's status agrees with what the engine produces."""
    targets = _library_render_targets() | _github_render_targets()
    checked = 0
    for row in _doc_rows():
        key = row["key"]
        if not key.startswith("template/"):
            continue
        mapped = key.removeprefix("template/").replace(
            "{{package_name}}", _REFERENCE_PACKAGE
        )
        produced = mapped in targets
        if row["status"] == "shipped":
            assert produced, f"{key} marked shipped but no library render target"
        elif row["status"] == "gap":
            assert not produced, f"{key} marked gap but render emits {mapped}"
        checked += 1
    assert checked == len(_template_keys())


def test_known_input_gaps_and_deliveries_are_classified() -> None:
    """The questions with and without a ProjectSpec route are marked right."""
    # FT-17.02 / ADR 0063 shipped the `github` platform, moving github_org,
    # repo_url, codeowners_team and python_matrix out of this set.
    gap_questions = {
        "type_checking",
        "coverage_fail_under",
        "dependency_updates",
        "use_docs",
        "changelog_tool",
    }
    shipped_questions = _copier_questions() - gap_questions
    by_key = {row["key"]: row for row in _doc_rows()}
    for question in gap_questions:
        assert by_key[question]["status"] == "gap", question
    for question in shipped_questions:
        assert by_key[question]["status"] == "shipped", question
