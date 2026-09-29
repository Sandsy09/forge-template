"""Executable pin for docs/batch-archetype.md (FT-27.01 / ADR 0080).

The contract fixes the Batch archetype's shape ahead of any implementation.
It is only useful if it stays honest about the engine it is written against
and about how little of it exists yet. These tests:

* check the Foundation extension points the contract names -- used and
  deliberately unused -- against the live Foundation source, deriving them
  from the contract's own table rather than a second hard-coded copy;
* pin the normative "unused" claims, because a batch ``check`` that
  depended on a runtime dependency or hung on an aggregate task would break
  the no-Forge-runtime-dependency and terminating-``check`` guarantees every
  other archetype already gives; and
* assert that ``batch`` is **not yet** in the catalogue, and that no existing
  component, Foundation content or the direct-Copier template already names
  it.

This last assertion is deliberately a tripwire: a future implementation stage
that adds the ``batch`` component must update this file's catalogue
assertion (see ADR 0080's consequences), the same discipline
``test_streamlit_contract.py`` followed through FT-19.01 to FT-20.02.
"""

from __future__ import annotations

import re
from pathlib import Path

from forge_template import discover_components
from forge_template.foundation_source import load_foundation_source

_ROOT = Path(__file__).parents[1]
_DOCS = _ROOT / "docs"
_CONTRACT = _DOCS / "batch-archetype.md"
_FOUNDATION_TOML = _ROOT / "src" / "forge_template" / "foundation" / "foundation.toml"

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


def test_batch_is_not_yet_in_the_catalogue() -> None:
    """Fails deliberately once a future stage lands the ``batch`` component.

    That stage must replace this assertion with the positive form (as
    ``test_streamlit_contract.py`` did across FT-20.01/FT-20.02), not delete
    the tripwire.
    """
    components = {c.id: c.kind for c in discover_components()}
    assert "batch" not in components
    archetypes = {cid for cid, kind in components.items() if kind == "archetype"}
    assert archetypes == {"library", "cli", "data-science", "streamlit"}


def test_no_existing_content_names_batch_yet() -> None:
    """Foundation, the direct-Copier template and every component stay free
    of a ``batch``-specific reference until an accepted implementation adds
    one."""
    source = _ROOT / "src" / "forge_template"
    roots = [source / "foundation", _ROOT / "template", source / "components"]
    for root in roots:
        assert _content_files(root), f"{root} holds no files; the scan is vacuous"
    offenders = [
        str(path.relative_to(_ROOT))
        for root in roots
        for path in _content_files(root)
        if "batch" in path.read_text(encoding="utf-8", errors="ignore").lower()
        or "batch" in path.name.lower()
    ]
    assert not offenders, f"content already names batch: {offenders}"
