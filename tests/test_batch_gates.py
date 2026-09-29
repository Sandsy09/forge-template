"""Executable tripwire for docs/batch-compatibility-and-acceptance.md
(FT-27.02 / ADR 0081).

The contract fixes the provider line, the capability matrix, the bounds and
the acceptance matrix, ahead of any implementation. It is only useful if it
stays derivable from the engine and honest about how little of it exists
yet. These tests:

* read every number from the contract's own constants table -- never a
  second copy -- and check its axis table against the live engine at their
  unchanged, pre-implementation baseline;
* prove the projected 640-composition growth and the ``documentation``
  rejection against the live catalogue and the engine's own selection rule,
  using a synthetic ``batch`` descriptor exactly as the contract's own
  Context section derives it;
* check the acceptance matrix names only filed issues and that each Stage 28
  provider child owns at least one row; and
* tripwire on the line: this must be updated, not deleted, once FT-28.01
  lands the component and FT-28.03 publishes the line, the same discipline
  ``test_streamlit_gates.py`` followed through Stage 20.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forge_template import (
    SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS,
    SUPPORTED_PROJECTSPEC_PROTOCOLS,
    discover_components,
    get_engine_info,
)
from forge_template.foundation_source import load_foundation_source
from tests.composition_matrix import EXPECTED_COMPOSITION_COUNT, valid_compositions

_ROOT = Path(__file__).parents[1]
_CONTRACT = _ROOT / "docs" / "batch-compatibility-and-acceptance.md"
_ADR = _ROOT / "docs" / "adr" / "0081-batch-composition-compatibility-and-acceptance.md"
_FOUNDATION_TOML = _ROOT / "src" / "forge_template" / "foundation" / "foundation.toml"
_V5_MANIFEST = _ROOT / "docs" / "roadmap-v5" / "github-issues" / "filing-manifest.json"

_ISSUE_TOKEN = re.compile(r"(?:FT|CF)-(?:EPIC-)?\d{2}(?:\.\d{2})?")
_STAGE_28_PROVIDER_CHILDREN = {"FT-28.01", "FT-28.02", "FT-28.03"}


@dataclass(frozen=True)
class _SyntheticComposition:
    archetype: str
    capabilities: tuple[str, ...]
    platforms: tuple[str, ...]


# --- doc parsing -------------------------------------------------------


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
    """``axis -> (current, batch line)`` from the classification table."""
    block = _section(_text(), "Every versioned axis is classified")
    return {
        cells[0]: (_normalise(cells[1]), _normalise(cells[2]))
        for cells in _table_rows(block, 4)
        if cells[0] != "Axis"
    }


def _subsection(text: str, heading: str) -> str:
    """The body between ``### heading`` and the next ``#`` heading of any
    level."""
    start = text.index(f"### {heading}")
    rest = re.search(r"\n#{1,6} ", text[start + 1 :])
    end = start + 1 + rest.start() if rest else len(text)
    return text[start:end]


def _matrix_owner_tokens() -> list[str]:
    text = _text()
    tokens: list[str] = []
    for heading in (
        "Engine and catalogue checks",
        "Generated-project checks",
        "Python endpoint checks",
        "Client and end-to-end checks",
        "Regression checks",
    ):
        block = _subsection(text, heading)
        for cells in _table_rows(block, 4):
            if cells[0] == "Check":
                continue
            tokens.extend(_ISSUE_TOKEN.findall(cells[1]))
    return tokens


def _filed_issue_ids() -> set[str]:
    manifest: dict[str, Any] = json.loads(_V5_MANIFEST.read_text(encoding="utf-8"))
    return {entry["id"] for entry in manifest["issues"]}


# --- constants and axes, at the pre-implementation baseline -------------


def test_contract_names_the_adr() -> None:
    text = _text()
    assert _ADR.name in text
    assert _ADR.is_file()


def test_the_prose_repeats_the_constants_it_defines() -> None:
    """A number quoted in prose must equal the constants-table value."""
    text = _text()
    constants = _constants()
    job = constants["JOB_RUN_TIMEOUT_SECONDS"]
    project = constants["PROJECT_CHECK_TIMEOUT_SECONDS"]
    assert f"`JOB_RUN_TIMEOUT_SECONDS` ({job} seconds)" in text
    assert f"`PROJECT_CHECK_TIMEOUT_SECONDS` ({project} seconds)" in text
    assert constants["COMPOSITION_COUNT_WITH_BATCH"] in text
    assert f"`{constants['PROVIDER_LINE']}`" in text


def test_axis_cells_match_the_live_engine_at_the_decision_baseline() -> None:
    """Batch has not landed: every axis's "Current" cell must equal the live
    engine today. FT-28.01/FT-28.03 will make the "Batch line" cells live."""
    axes = _axes()
    info = get_engine_info()

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
    assert axes["Discovered components"][0] == str(len(discover_components()))
    assert "batch" not in {c.id for c in discover_components()}


def test_the_batch_line_moves_exactly_the_two_axes_it_claims() -> None:
    """Only the package version and the component count differ; every other
    axis row states the same value before and after."""
    axes = _axes()
    moved = {axis for axis, (current, line) in axes.items() if current != line}
    assert moved == {
        "`forge-template` package",
        "Discovered components",
        "`batch` component",
    }
    current_count, line_count = axes["Discovered components"]
    assert int(line_count) == int(current_count) + 1
    assert axes["`batch` component"][1] == _constants()["COMPONENT_VERSION"]


def test_the_provider_line_is_one_minor_past_the_live_package() -> None:
    """Fails deliberately at the next unrelated minor bump, forcing the
    contract to be revisited, exactly as test_streamlit_gates.py's
    equivalent tripwire did through Stage 19/20."""
    live = get_engine_info().package_version
    line = _constants()["PROVIDER_LINE"]
    baseline = _axes()["`forge-template` package"][0].split(".")
    assert baseline == live.split(".")
    assert line.split(".")[:2] == ["0", str(int(baseline[1]) + 1)]


# --- the projected composition growth, proven against the engine's rule -


def test_the_projected_growth_matches_the_contract_arithmetic() -> None:
    """A synthetic no-edge ``batch`` descriptor, added to the live catalogue,
    must add exactly the contract's claimed count. This is the same
    technique ADR 0069 (Streamlit) used before FT-20.01 landed."""
    live = discover_components()
    synthetic = live[0].model_copy(
        update={
            "id": "batch",
            "name": "Batch Job",
            "kind": "archetype",
            "requires": (),
            "conflicts": (),
            "options": (),
        }
    )
    projected = valid_compositions((*live, synthetic))
    current = valid_compositions(live)

    added = len(projected) - len(current)
    assert added == 640, "batch should add exactly cli/streamlit's 640"
    assert len(projected) == int(_constants()["COMPOSITION_COUNT_WITH_BATCH"])
    assert len(current) == EXPECTED_COMPOSITION_COUNT

    batch_only = [c for c in projected if c.archetype == "batch"]
    assert batch_only, "no batch compositions derived"
    assert all("documentation" not in c.capabilities for c in batch_only)


# --- acceptance matrix ---------------------------------------------------


def test_every_matrix_row_names_a_filed_issue() -> None:
    filed = _filed_issue_ids()
    tokens = _matrix_owner_tokens()
    assert tokens, "no owner tokens parsed from the acceptance matrix"
    for token in tokens:
        assert token in filed, f"acceptance matrix cites unfiled issue {token}"


def test_every_stage_28_provider_child_owns_at_least_one_matrix_row() -> None:
    owned = set(_matrix_owner_tokens())
    missing = sorted(_STAGE_28_PROVIDER_CHILDREN - owned)
    assert not missing, f"provider children with no acceptance row: {missing}"


def test_batch_is_not_yet_a_discovered_component() -> None:
    """Fails deliberately once FT-28.01 lands the component; that stage must
    replace this assertion with the positive form."""
    assert "batch" not in {c.id for c in discover_components()}
