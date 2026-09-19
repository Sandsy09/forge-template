"""Executable tripwire for docs/streamlit-compatibility-and-acceptance.md
(FT-19.02 / ADR 0069).

The contract fixes the provider line, the four capability selections, the
bounds and the acceptance matrix. It is only useful if it stays derivable from
the engine. FT-20.01 landed the component, so these tests:

* read every number from the contract's own constants table -- never a second
  copy -- and check its axis table against the live engine: the unchanged axes
  and the package still on the decision baseline, and the component axes at the
  "Streamlit line" value now that ``streamlit`` is discovered;
* prove the four selections, the ``documentation`` rejection and the 2880
  composition count against the live catalogue and the engine's own selection
  rule;
* check the acceptance matrix names only filed issues and that each Stage 20
  provider child owns at least one row;
* check the contract's "no cutover implementation dependency" finding still
  holds in the filing manifest; and
* tripwire on the line: the package is still on ``0.5`` until FT-20.04
  publishes ``0.6.0``, so this fails deliberately at that bump and the contract
  and the implementation must be brought back into step.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from forge_template import (
    SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS,
    SUPPORTED_PROJECTSPEC_PROTOCOLS,
    discover_components,
    get_engine_info,
)
from forge_template.foundation_source import load_foundation_source
from tests.composition_matrix import (
    EXPECTED_COMPOSITION_COUNT,
    Composition,
    valid_compositions,
)

_ROOT = Path(__file__).parents[1]
_CONTRACT = _ROOT / "docs" / "streamlit-compatibility-and-acceptance.md"
_ADR = (
    _ROOT
    / "docs"
    / "adr"
    / "0069-streamlit-composition-compatibility-and-acceptance.md"
)
_COPIER = _ROOT / "copier.yml"
_FOUNDATION_TOML = _ROOT / "src" / "forge_template" / "foundation" / "foundation.toml"
_V4_MANIFEST = _ROOT / "docs" / "roadmap-v4" / "github-issues" / "filing-manifest.json"

_ISSUE_TOKEN = re.compile(r"(?:FT|CF)-(?:EPIC-)?\d{2}(?:\.\d{2})?")
_OBLIGATIONS = ("FT-ROADMAP-02-AC-01", "FT-ROADMAP-02-AC-04", "FT-ROADMAP-02-EX-03")

# The four selections FT-19.02 approves, as the sorted capability tuples the
# matrix derivation itself produces.
_FOUR_SELECTIONS = (
    (),
    ("jupyter",),
    ("scientific-python",),
    ("jupyter", "scientific-python"),
)
_STAGE_20_PROVIDER_CHILDREN = {"FT-20.01", "FT-20.02", "FT-20.03", "FT-20.04"}


# --- doc parsing -----------------------------------------------------------


def _text() -> str:
    return _CONTRACT.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """The body between ``## heading`` and the next ``## ``."""
    start = text.index(f"## {heading}")
    rest = text.index("\n## ", start + 1)
    return text[start:rest]


def _table_rows(block: str, width: int) -> list[list[str]]:
    """Every pipe row in ``block`` with exactly ``width`` cells, minus the
    header separator."""
    rows: list[list[str]] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != width:
            continue
        if set("".join(cells)) <= {"-", " ", ":"}:
            continue
        rows.append(cells)
    return rows


def _normalise(cell: str) -> str:
    """Strip backticks and parenthetical asides, collapse separators."""
    cell = re.sub(r"\([^)]*\)", "", cell)
    return cell.replace("`", "").replace(" ", "").strip(" ,")


def _join(protocols: tuple[int, ...]) -> str:
    return _normalise(", ".join(str(p) for p in protocols))


def _constants() -> dict[str, str]:
    """``NAME -> value`` from the contract's normative constants table."""
    block = _section(_text(), "Normative constants")
    return {
        cells[0].strip("`"): cells[1].strip("`")
        for cells in _table_rows(block, 2)
        if cells[0] != "Constant"
    }


def _axes() -> dict[str, tuple[str, str]]:
    """``axis -> (current, streamlit line)`` from the classification table."""
    block = _section(_text(), "Every versioned axis is classified")
    return {
        cells[0]: (_normalise(cells[1]), _normalise(cells[2]))
        for cells in _table_rows(block, 4)
        if cells[0] != "Axis"
    }


def _matrix_owner_tokens() -> list[str]:
    block = _section(_text(), "The acceptance matrix")
    tokens: list[str] = []
    for cells in _table_rows(block, 4):
        if cells[0] == "Check":
            continue
        tokens.extend(_ISSUE_TOKEN.findall(cells[1]))
    return tokens


def _filed_issue_ids() -> set[str]:
    ids: set[str] = set()
    for version in (3, 4):
        path = _ROOT / f"docs/roadmap-v{version}/github-issues/filing-manifest.json"
        manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        ids.update(entry["id"] for entry in manifest["issues"])
    return ids


def _v4_blocked_by() -> dict[str, list[str]]:
    manifest: dict[str, Any] = json.loads(_V4_MANIFEST.read_text(encoding="utf-8"))
    return {entry["id"]: entry["blocked_by"] for entry in manifest["issues"]}


# --- constants and axes ----------------------------------------------------


def test_contract_names_its_review_obligations_and_adr() -> None:
    text = _text()
    for obligation in _OBLIGATIONS:
        assert obligation in text, f"{obligation} is not named by the contract"
    assert _ADR.name in text
    assert _ADR.is_file()


def test_the_prose_repeats_the_constants_it_defines() -> None:
    """A number quoted in prose must equal the constants-table value."""
    text = _text()
    constants = _constants()
    smoke = constants["SMOKE_RUN_TIMEOUT_SECONDS"]
    project = constants["PROJECT_CHECK_TIMEOUT_SECONDS"]
    assert f"`SMOKE_RUN_TIMEOUT_SECONDS` ({smoke} seconds)" in text
    assert f"`PROJECT_CHECK_TIMEOUT_SECONDS` ({project} seconds)" in text
    assert constants["COMPOSITION_COUNT_WITH_STREAMLIT"] in text
    assert f"`{constants['PROVIDER_LINE']}`" in text


def test_axis_cells_match_the_live_engine_as_the_line_lands() -> None:
    """The table records the 19 September 2026 decision baseline (before ->
    after). The unchanged axes and the package still equal live; the component
    axes' "Streamlit line" value is now live, because FT-20.01 landed it."""
    axes = _axes()
    info = get_engine_info()

    # Moves at FT-20.04, which publishes `0.6.0`.
    assert axes["`forge-template` package"][0] == info.package_version
    assert axes["ProjectSpec protocol"][0] == _join(SUPPORTED_PROJECTSPEC_PROTOCOLS)
    assert axes["Component manifest protocol"][0] == _join(
        SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS
    )
    assert axes["Generation metadata `metadata_version`"][0] == str(
        info.metadata_version
    )
    foundation = load_foundation_source(_FOUNDATION_TOML)
    assert axes["Foundation extension points"][0] == str(
        len(foundation.extension_points)
    )
    assert axes["Discovered components"][1] == str(len(discover_components()))
    assert int(axes["Discovered components"][0]) + 1 == len(discover_components())


def test_the_streamlit_line_moves_exactly_the_two_axes_it_claims() -> None:
    """Only the package version and the component count differ; every other
    axis row states the same value before and after."""
    axes = _axes()
    moved = {axis for axis, (current, line) in axes.items() if current != line}
    assert moved == {
        "`forge-template` package",
        "Discovered components",
        "`streamlit` component",
    }
    current_count, line_count = axes["Discovered components"]
    assert int(line_count) == int(current_count) + 1
    assert axes["`streamlit` component"][1] == _constants()["COMPONENT_VERSION"]


def test_the_provider_line_is_the_next_minor_of_the_live_package() -> None:
    """Tripwire: fails when Stage 20 bumps the package."""
    live = get_engine_info().package_version.split(".")
    line = _constants()["PROVIDER_LINE"].split(".")
    assert live[:2] == ["0", "5"], "the package has moved; revisit the contract"
    assert line[:2] == ["0", str(int(live[1]) + 1)]


def test_python_endpoints_sit_inside_the_active_window() -> None:
    constants = _constants()
    match = re.search(
        r"python_all:.*?default:\s*'(\[[^\]]*\])'", _COPIER.read_text("utf-8"), re.S
    )
    assert match is not None, "python_all not found in copier.yml"
    window = json.loads(match.group(1))
    endpoints = [e.strip() for e in constants["PYTHON_ENDPOINTS"].split(",")]
    assert constants["PYTHON_FLOOR"] == window[0]
    assert endpoints == [window[0], window[-1]]


# --- the four selections, proven against the engine's own rule -------------


def test_the_four_selections_are_valid_and_documentation_is_not() -> None:
    accepted = set(valid_compositions())
    for capabilities in _FOUR_SELECTIONS:
        assert Composition("streamlit", capabilities, ()) in accepted, capabilities
    streamlit = [c for c in accepted if c.archetype == "streamlit"]
    assert streamlit, "no streamlit compositions derived"
    assert all("documentation" not in c.capabilities for c in streamlit)


def test_the_sweep_count_matches_the_contract_arithmetic() -> None:
    constants = _constants()
    live = valid_compositions()
    per_archetype = {
        archetype: sum(1 for c in live if c.archetype == archetype)
        for archetype in {c.archetype for c in live}
    }
    streamlit_count = per_archetype["streamlit"]

    assert streamlit_count == per_archetype["cli"], "streamlit is cli-shaped"
    assert len(live) == int(constants["COMPOSITION_COUNT_WITH_STREAMLIT"])
    assert len(live) == EXPECTED_COMPOSITION_COUNT
    assert str(streamlit_count) in _text()


# --- acceptance matrix and the no-new-dependency finding -------------------


def test_every_matrix_row_names_a_filed_issue() -> None:
    filed = _filed_issue_ids()
    tokens = _matrix_owner_tokens()
    assert tokens, "no owner tokens parsed from the acceptance matrix"
    for token in tokens:
        assert token in filed, f"acceptance matrix cites unfiled issue {token}"


def test_every_stage_20_provider_child_owns_at_least_one_matrix_row() -> None:
    owned = set(_matrix_owner_tokens())
    missing = sorted(_STAGE_20_PROVIDER_CHILDREN - owned)
    assert not missing, f"provider children with no acceptance row: {missing}"


def test_no_cutover_implementation_dependency_was_added() -> None:
    """The contract's finding: nothing Streamlit needs is unshipped, so the
    roadmap-v4 dependency edges are exactly the ones filed."""
    edges = _v4_blocked_by()
    assert edges["FT-19.02"] == ["FT-19.01"]
    assert edges["FT-20.01"] == ["FT-19.02"]
    assert edges["CF-21.01"] == ["FT-20.04"]
    assert not any("CF-18" in blockers for blockers in edges.values())


def test_the_discovered_component_carries_the_contracts_identity() -> None:
    streamlit = next(c for c in discover_components() if c.id == "streamlit")

    assert streamlit.kind == "archetype"
    assert streamlit.version == _constants()["COMPONENT_VERSION"]
    assert (streamlit.requires, streamlit.conflicts, streamlit.options) == ((), (), ())
