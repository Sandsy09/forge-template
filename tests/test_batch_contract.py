"""Executable pin for docs/batch-archetype.md (FT-27.01 / ADR 0080).

The contract fixed the Batch archetype's shape; FT-28.01 / ADR 0082 has now
implemented it. It is only useful if it stays honest about the engine it is
written against and about how much of it exists. These tests:

* check the Foundation extension points the contract names -- used and
  deliberately unused -- against the live Foundation source, deriving them
  from the contract's own table rather than a second hard-coded copy;
* pin the normative "unused" claims, because a batch ``check`` that
  depended on a runtime dependency or hung on an aggregate task would break
  the no-Forge-runtime-dependency and terminating-``check`` guarantees every
  other archetype already gives;
* check the live manifest contributes exactly the points the contract marks
  used; and
* assert that ``batch`` **is** in the catalogue, and that no other component,
  Foundation content or the direct-Copier template names it.

This file was updated in step with the implementation that landed the
``batch`` component (FT-28.01), the same discipline ``test_streamlit_contract.py``
followed through FT-20.01/FT-20.02, rather than being deleted.
"""

from __future__ import annotations

import re
from pathlib import Path

from forge_template import discover_components
from forge_template.component_manifest import load_component_manifest
from forge_template.foundation_source import load_foundation_source

_ROOT = Path(__file__).parents[1]
_DOCS = _ROOT / "docs"
_CONTRACT = _DOCS / "batch-archetype.md"
_FOUNDATION_TOML = _ROOT / "src" / "forge_template" / "foundation" / "foundation.toml"
_COMPONENTS = _ROOT / "src" / "forge_template" / "components"

# Claims the contract makes normatively and this pin must not let it drop.
_MUST_NOT_USE = {
    "pyproject-runtime-dependencies",
    "pyproject-aggregate-check",
    "pyproject-development-dependencies",
}
_MUST_USE = {
    "pyproject-build-system",
    "pyproject-archetype-metadata",
    "pyproject-build-configuration",
    "pyproject-classifiers",
    "pyproject-entry-points",
    "pyproject-task-definitions",
    "readme-project-shape",
    "gitignore-project-shape",
}

_ROW = re.compile(r"^\| `(?P<point>[a-z-]+)` \| (?P<used>yes|no) \|", re.MULTILINE)


def _extension_requirements() -> dict[str, bool]:
    """Return ``{point: used}`` from the contract's Foundation table."""
    text = _CONTRACT.read_text(encoding="utf-8")
    section = text.split("## Foundation extension requirements", 1)[1]
    section = section.split("\n## ", 1)[0]
    return {m["point"]: m["used"] == "yes" for m in _ROW.finditer(section)}


def _published_points() -> set[str]:
    foundation = load_foundation_source(_FOUNDATION_TOML)
    return {point.id for point in foundation.extension_points}


def _content_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ]


def test_every_extension_point_the_contract_names_is_published() -> None:
    published = _published_points()
    named = _extension_requirements()
    assert named, "the contract's extension-point table was not found"
    unpublished = set(named) - published
    assert not unpublished, f"contract names unpublished points: {sorted(unpublished)}"


def test_the_contract_adds_no_new_extension_point() -> None:
    """Every concern is served by the points Foundation already publishes."""
    published = _published_points()
    assert len(published) == 16


def test_normative_used_and_unused_points_are_pinned() -> None:
    named = _extension_requirements()
    for point in _MUST_NOT_USE:
        assert named.get(point) is False, f"{point} must be listed as unused"
    for point in _MUST_USE:
        assert named.get(point) is True, f"{point} must be listed as used"


def test_batch_is_the_fifth_archetype_in_the_catalogue() -> None:
    """FT-28.01 landed the component; this replaces the pre-implementation
    "not yet" tripwire with its positive form."""
    components = {c.id: c.kind for c in discover_components()}
    assert components.get("batch") == "archetype"
    archetypes = {cid for cid, kind in components.items() if kind == "archetype"}
    assert archetypes == {"library", "cli", "data-science", "streamlit", "batch"}


def test_the_live_manifest_contributes_the_points_the_contract_marks_used() -> None:
    manifest = load_component_manifest(_COMPONENTS / "batch" / "component.toml")
    contributed = {item.extension_point for item in manifest.contributions}
    used = {point for point, is_used in _extension_requirements().items() if is_used}

    assert contributed == used
    assert not contributed & {
        point for point, is_used in _extension_requirements().items() if not is_used
    }


def test_foundation_the_template_and_sibling_components_stay_batch_free() -> None:
    """Foundation stays runtime-free, the direct-Copier path stays
    Library-only, and no sibling archetype reads or names batch."""
    source = _ROOT / "src" / "forge_template"
    roots = [source / "foundation", _ROOT / "template"]
    roots += [
        path
        for path in sorted((source / "components").iterdir())
        if (path / "component.toml").is_file() and path.name != "batch"
    ]
    for root in roots:
        assert _content_files(root), f"{root} holds no files; the scan is vacuous"
    offenders = [
        str(path.relative_to(_ROOT))
        for root in roots
        for path in _content_files(root)
        if "batch" in path.read_text(encoding="utf-8", errors="ignore").lower()
        or "batch" in path.name.lower()
    ]
    assert not offenders, f"content outside the archetype names batch: {offenders}"
