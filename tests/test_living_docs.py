"""Guards the living provider documentation against the shipped catalogue.

`tests/test_compatibility_policy.py` pins the "Current compatibility state"
table in `docs/compatibility-policy.md`. Nothing else stopped the rest of the
living documentation from describing the released Data Science line as future
work -- exactly the drift issue #136 reconciled.

This module scans the *living* set only: every `*.md` directly under `docs/`
plus `README.md`, `CONTRIBUTING.md`, and `CLAUDE.md`. `docs/adr/`,
`docs/roadmap-v1/`, and `docs/roadmap-v2/` are immutable historical records
and are deliberately out of scope. Every expected value comes from the real
`discover_components()` / `get_engine_info()`, so the guard self-updates at
the next release rather than hard-coding a number that will itself go stale.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from forge_template import discover_components, get_engine_info
from forge_template.engine import ComponentDescriptor

_ROOT = Path(__file__).parents[1]
_DOCS = _ROOT / "docs"
_EXCLUDED_DIRS = ("adr", "roadmap-v1", "roadmap-v2")
_ROOT_GUIDES = ("README.md", "CONTRIBUTING.md", "CLAUDE.md")


def _living_docs() -> list[Path]:
    docs = sorted(p for p in _DOCS.glob("*.md"))
    docs += [_ROOT / name for name in _ROOT_GUIDES]
    return docs


_LIVING_DOCS = _living_docs()
_DOC_TEXT: dict[Path, str] = {p: p.read_text(encoding="utf-8") for p in _LIVING_DOCS}

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}

# Nouns that name a whole-catalogue count, mapped to the axis whose size they
# must match.
_CATALOGUE_NOUNS = {
    "component": "component",
    "components": "component",
    "descriptor": "component",
    "descriptors": "component",
    "manifest": "component",
    "manifests": "component",
    "archetype": "archetype",
    "archetypes": "archetype",
    "capability": "capability",
    "capabilities": "capability",
}

# Historical narration is allowed to quote an old version: a block that names
# an FT-/CF- issue, a v-prefixed tag, or an explicit "baseline"/"at the time"
# marker is reporting what a past change did, not the current contract.
_HISTORICAL = re.compile(
    r"(?:FT|CF)-\d|\bv0\.\d|at the time|then\)|baseline|pre-rollout|"
    r"when this .{0,40}was written",
    re.IGNORECASE,
)


def _blocks(text: str) -> list[str]:
    """Blank-line-separated blocks, each with internal whitespace collapsed."""
    raw = re.split(r"\n[ \t]*\n", text)
    return [re.sub(r"\s+", " ", block).strip() for block in raw if block.strip()]


def _catalogue_counts() -> dict[str, int]:
    components = discover_components()
    archetypes = [c for c in components if c.kind == "archetype"]
    capabilities = [c for c in components if c.kind == "capability"]
    return {
        "component": len(components),
        "archetype": len(archetypes),
        "capability": len(capabilities),
    }


def _tokens_for_component(component: ComponentDescriptor) -> list[str]:
    return [re.escape(component.id), re.escape(component.name)]


def test_living_doc_set_is_every_root_doc_and_no_historical_record() -> None:
    """The scan covers every ``docs/*.md`` plus the root guides, and never
    reaches an ADR or a roadmap record -- those are immutable and legitimately
    describe past state."""
    for name in _EXCLUDED_DIRS:
        assert (_DOCS / name).is_dir(), f"expected docs/{name}/ to exist"
        for record in (_DOCS / name).glob("*.md"):
            assert record not in _LIVING_DOCS, f"{record} is a historical record"

    for path in _LIVING_DOCS:
        assert path.is_file(), f"{path} in the living set does not exist"
        parts = set(path.relative_to(_ROOT).parts)
        assert parts.isdisjoint(_EXCLUDED_DIRS), f"{path} is a historical record"

    assert set(_DOCS.glob("*.md")) <= set(_LIVING_DOCS), "a docs/*.md is unscanned"


def test_no_living_doc_states_a_stale_catalogue_total() -> None:
    """A phrase like "all four shipped components" must agree with the real
    catalogue size. Only the whole-catalogue qualifiers
    (shipped/production/discovered/published) are checked, so "the three new
    components" and "all four capability selections" are left alone."""
    counts = _catalogue_counts()
    pattern = re.compile(
        r"\b(one|two|three|four|five|six|\d+)\s+"
        r"(?:shipped|production|discovered|published)\s+"
        r"(component|components|descriptor|descriptors|manifest|manifests|"
        r"archetype|archetypes|capability|capabilities)\b",
        re.IGNORECASE,
    )
    failures: list[str] = []
    for path, text in _DOC_TEXT.items():
        for match in pattern.finditer(text):
            word = match.group(1).lower()
            stated = _NUMBER_WORDS.get(word, int(word) if word.isdigit() else 0)
            axis = _CATALOGUE_NOUNS[match.group(2).lower()]
            if stated != counts[axis]:
                rel = path.relative_to(_ROOT).as_posix()
                failures.append(
                    f"{rel}: '{match.group(0)}' but the catalogue has "
                    f"{counts[axis]} {axis}(s)"
                )
    assert not failures, "\n".join(failures)


def test_no_living_doc_calls_a_shipped_component_future() -> None:
    """Every discovered component is shipped. No living doc may describe one as
    future / planned / awaiting implementation."""
    banned = re.compile(
        r"for later stage \d+ implementation|awaiting stage \d+|"
        r"still awaiting implementation|the components are unbuilt",
        re.IGNORECASE,
    )
    matchers: list[re.Pattern[str]] = []
    for component in discover_components():
        for token in _tokens_for_component(component):
            matchers.append(
                re.compile(
                    rf"\bfuture\s+`?{token}`?\s+"
                    rf"(?:archetype|capability|component|line|catalogue|"
                    rf"release|shape|owner|manifest|descriptor)",
                    re.IGNORECASE,
                )
            )
            matchers.append(
                re.compile(
                    rf"`?{token}`?\s+(?:is|are|remains?|stays?|will\s+be)\s+"
                    rf"(?:(?:still|not)\s+)?(?:yet\s+)?"
                    rf"(?:un(?:built|shipped|released|implemented)|"
                    rf"future\s+work|awaiting|planned|"
                    rf"not\s+yet\s+(?:built|shipped|implemented|available))",
                    re.IGNORECASE,
                )
            )

    failures: list[str] = []
    for path, text in _DOC_TEXT.items():
        rel = path.relative_to(_ROOT).as_posix()
        for rx in (*matchers, banned):
            hit = rx.search(text)
            if hit:
                failures.append(f"{rel}: '{hit.group(0).strip()}'")
    assert not failures, "\n".join(failures)


def test_no_living_doc_claims_a_stale_current_package_version() -> None:
    """Check "package version `X`" against the installed engine.

    A stale claim passes only when its block is clearly historical -- it names
    an FT-/CF- issue, a v-tag, or an explicit baseline marker.
    """
    current = get_engine_info().package_version
    # Only full X.Y.Z versions are staleable claims; "package version `0.4.x`"
    # names the compatibility *line* and is left alone.
    pattern = re.compile(
        r"package\s+version\s*\(?\s*[`(]?(\d+\.\d+\.\d+)\b",
        re.IGNORECASE,
    )
    failures: list[str] = []
    for path, text in _DOC_TEXT.items():
        rel = path.relative_to(_ROOT).as_posix()
        for block in _blocks(text):
            for match in pattern.finditer(block):
                if match.group(1) == current or _HISTORICAL.search(block):
                    continue
                failures.append(
                    f"{rel}: 'package version {match.group(1)}' "
                    f"(installed engine is {current})"
                )
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("path", _LIVING_DOCS, ids=lambda p: p.name)
def test_living_doc_is_readable_utf8(path: Path) -> None:
    """Sanity: every file the scan claims to cover is decodable, so a silently
    unreadable doc cannot pass the guards by contributing no text."""
    assert path.read_text(encoding="utf-8").strip()
