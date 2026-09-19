"""Executable tripwire for docs/streamlit-archetype.md (FT-19.01 / ADR 0068).

The contract fixes the Streamlit archetype's shape ahead of any implementation.
It is only useful if it stays honest about what does not exist yet and about
the engine it is written against. These tests:

* check the Foundation extension points the contract names -- used and
  deliberately unused -- against the live Foundation source, deriving them from
  the contract's own table rather than a second hard-coded copy;
* pin the two normative "unused" claims, because a Streamlit ``check`` that
  started a server would hang every generated project's quality gate;
* check the contract names its three review obligations verbatim and that every
  document ADR 0068 reconciled still points at it; and
* tripwire on the catalogue: ``streamlit`` is not yet a component and no
  Foundation, component or ``template/`` content mentions it, so these tests
  fail deliberately the moment FT-20.01 lands and the contract and the
  implementation must be brought back into step.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from forge_template import discover_components
from forge_template.foundation_source import load_foundation_source

_ROOT = Path(__file__).parents[1]
_DOCS = _ROOT / "docs"
_CONTRACT = _DOCS / "streamlit-archetype.md"
_FOUNDATION_TOML = _ROOT / "src" / "forge_template" / "foundation" / "foundation.toml"

_OBLIGATIONS = (
    "FT-ROADMAP-02-AC-01",
    "FT-ROADMAP-02-EX-01",
    "FT-ROADMAP-02-EX-04",
)

# ADR 0068 turned each of these documents' "reserved for another owner" note
# for the Streamlit layout into a pointer at the accepted contract.
_RECONCILED = (
    _DOCS / "cutover-compatibility-and-acceptance.md",
    _DOCS / "platform-and-tooling-parity.md",
    _DOCS / "engine-default-parity.md",
    _ROOT / "README.md",
)

# Claims the contract makes normatively and this pin must not let it drop.
_MUST_NOT_USE = {"pyproject-aggregate-check", "pyproject-entry-points"}
_MUST_USE = {"pyproject-task-definitions", "gitignore-project-shape"}

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


def test_contract_names_its_review_obligations_verbatim() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    for obligation in _OBLIGATIONS:
        assert obligation in text, f"{obligation} is not named by the contract"


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


@pytest.mark.parametrize("document", _RECONCILED, ids=lambda p: p.name)
def test_reconciled_documents_point_at_the_contract(document: Path) -> None:
    assert "streamlit-archetype.md" in document.read_text(encoding="utf-8")


def test_env_example_is_owned_by_the_dotenv_example_capability() -> None:
    """The contract must not attribute the tracked ``.env.example`` to Foundation."""
    foundation_content = _ROOT / "src" / "forge_template" / "foundation" / "content"
    assert not (foundation_content / ".env.example").exists()
    components = {c.id: c.kind for c in discover_components()}
    assert components.get("dotenv-example") == "capability"
    assert "dotenv-example" in _CONTRACT.read_text(encoding="utf-8")


def test_streamlit_is_not_yet_in_the_catalogue() -> None:
    """Tripwire: fails when FT-20.01 adds the component (contract-only stage)."""
    components = {c.id: c.kind for c in discover_components()}
    assert "streamlit" not in components
    archetypes = {cid for cid, kind in components.items() if kind == "archetype"}
    assert archetypes == {"library", "cli", "data-science"}


def test_no_generated_content_mentions_streamlit_yet() -> None:
    """Tripwire: FT-19.01 changes no generated content (its exclusion list)."""
    source = _ROOT / "src" / "forge_template"
    roots = (source / "components", source / "foundation", _ROOT / "template")
    for root in roots:
        assert _content_files(root), f"{root} holds no files; the scan is vacuous"
    offenders = [
        str(path.relative_to(_ROOT))
        for root in roots
        for path in _content_files(root)
        if "streamlit" in path.read_text(encoding="utf-8", errors="ignore").lower()
        or "streamlit" in path.name.lower()
    ]
    assert not offenders, f"generated content already mentions Streamlit: {offenders}"
