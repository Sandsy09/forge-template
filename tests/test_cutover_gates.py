"""Executable pin for docs/cutover-compatibility-and-acceptance.md
(FT-15.04 / ADR 0061).

The contract classifies which versioned axes the engine-default cutover moves
and fixes the acceptance matrix that admits the cutover release. It is only
useful if it stays derivable from the engine and honest about what is still a
gap. These tests:

* check every "Current"/"Unchanged" axis claim against the live engine or the
  living compatibility-policy state table -- never against this document
  itself;
* check the acceptance matrix names only filed issues and that every provider
  child of Stages 17-18 owns at least one row;
* check FT-15.04's parity-row reconciliation actually landed -- no matrix row
  in engine-default-parity.md still carries the ``needs a bounded issue``
  marker, and every provider-owned ``gap`` row now cites a filed issue;
* and tripwire on each classified target: the package is still ``0.4.x``
  (FT-17.06 moves it) and ``copier.yml`` still carries no ``_migrations``
  block, while FT-17.01 / ADR 0062 has moved manifest protocols to
  ``(1, 2, 3)``, shipped the two generation-metadata error codes, published
  ``metadata_version`` on ``EngineInfo``, and grown the public facade
  additively -- the assertions below track the live state.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import forge_template
from forge_template import (
    SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS,
    SUPPORTED_PROJECTSPEC_PROTOCOLS,
    EngineErrorCode,
    EngineInfo,
    ForgeEngineError,
    discover_components,
    get_engine_info,
    parse_project_spec,
    plan_generation,
    render_project,
)
from forge_template.foundation_source import load_foundation_source

_ROOT = Path(__file__).parents[1]
_CONTRACT = _ROOT / "docs" / "cutover-compatibility-and-acceptance.md"
_PARITY = _ROOT / "docs" / "engine-default-parity.md"
_POLICY = _ROOT / "docs" / "compatibility-policy.md"
_COPIER = _ROOT / "copier.yml"
_FOUNDATION_TOML = _ROOT / "src" / "forge_template" / "foundation" / "foundation.toml"

_ISSUE_TOKEN = re.compile(r"(?:FT|CF)-(?:EPIC-)?\d{2}(?:\.\d{2})?")

# The provider children of Stages 17-18 that every acceptance matrix must
# collectively cover -- decision 7's second direction.
_PROVIDER_CHILDREN = {
    "FT-17.01",
    "FT-17.02",
    "FT-17.03",
    "FT-17.04",
    "FT-17.05",
    "FT-17.06",
    "FT-18.01",
}

# The seven EngineErrorCode values shipped through 0.4.1, plus the two
# generation-metadata codes FT-17.01 / ADR 0062 added. The whole set is the
# tripwire now: nothing else may join it in the cutover.
_ORIGINAL_ERROR_CODES = {
    "invalid-project-spec",
    "component-discovery-failed",
    "invalid-component-selection",
    "invalid-component-options",
    "generation-plan-failed",
    "template-render-failed",
    "generated-project-invalid",
}
_GENERATION_METADATA_ERROR_CODES = {
    "invalid-generation-metadata",
    "unsupported-generation-metadata",
}
_SHIPPED_ERROR_CODES = _ORIGINAL_ERROR_CODES | _GENERATION_METADATA_ERROR_CODES

# The public facade as of 0.4.1, plus the additive generation-metadata names
# FT-17.01 / ADR 0062 added, plus the additive reproducible-render names
# FT-17.04 / ADR 0065 added (AppliedRename, UpdatePlan, UpdateTarget,
# plan_update). The cutover renames and removes nothing; this set fails
# deliberately when any other name lands so the contract is revisited.
_FROZEN_PUBLIC_API = frozenset(
    {
        "DEFAULT_GENERATION_METADATA_TARGET",
        "GENERATION_METADATA_VERSION",
        "PROJECT_SPEC_PROTOCOL_VERSION",
        "SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS",
        "SUPPORTED_PROJECTSPEC_PROTOCOLS",
        "AppliedRename",
        "Author",
        "ComponentDescriptor",
        "ComponentOption",
        "ComponentOwner",
        "ComponentRelation",
        "ComponentSelection",
        "EngineErrorCode",
        "EngineErrorDetail",
        "EngineInfo",
        "ForgeEngineError",
        "FoundationOwner",
        "GenerationMetadata",
        "GenerationPlan",
        "MetadataProtocols",
        "OutputRecord",
        "PlannedExtension",
        "PlannedFile",
        "ProjectMetadata",
        "ProjectSpec",
        "ProviderIdentity",
        "PythonSelection",
        "RenderedFile",
        "RenderedProject",
        "ReproductionRecord",
        "SelectedComponent",
        "SelectionProvenance",
        "UpdatePlan",
        "UpdateTarget",
        "discover_components",
        "get_engine_info",
        "map_legacy_library_answers",
        "parse_generation_metadata",
        "parse_project_spec",
        "plan_generation",
        "plan_update",
        "render_project",
        "validate_project_spec",
        "validate_rendered_project",
        "verify_generation_metadata",
    }
)


# --- doc parsing -----------------------------------------------------------


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


def _axis_current() -> dict[str, str]:
    """``axis -> current value`` from the contract's classification table."""
    block = _section(
        _CONTRACT.read_text(encoding="utf-8"), "Every versioned axis is classified"
    )
    out: dict[str, str] = {}
    for cells in _table_rows(block, 4):
        axis, current, _cutover, _cls = cells
        if axis.lower() == "axis":
            continue
        out[axis] = _normalise(current)
    return out


def _policy_current() -> dict[str, str]:
    """``axis -> current value`` from compatibility-policy.md's living
    "Current compatibility state" table."""
    block = _section(_POLICY.read_text(encoding="utf-8"), "Current compatibility state")
    out: dict[str, str] = {}
    for cells in _table_rows(block, 2):
        axis, current = cells
        if axis.lower() == "axis":
            continue
        out[axis] = _normalise(current)
    return out


def _normalise(cell: str) -> str:
    """Strip backticks and parenthetical asides, collapse separators."""
    cell = re.sub(r"\([^)]*\)", "", cell)
    cell = cell.replace("`", "").replace(" ", "")
    return cell.strip(" ,")


def _matrix_owner_tokens() -> list[str]:
    block = _section(_CONTRACT.read_text(encoding="utf-8"), "The acceptance matrix")
    tokens: list[str] = []
    for cells in _table_rows(block, 4):
        if cells[0].lower() == "check":
            continue
        tokens.extend(_ISSUE_TOKEN.findall(cells[1]))
    return tokens


def _parity_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in _PARITY.read_text(encoding="utf-8").splitlines():
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
                "status": cells[2],
                "disposition": cells[3],
                "owner": cells[5],
            }
        )
    return rows


def _filed_issue_ids() -> set[str]:
    ids: set[str] = set()
    for version in (3, 4):
        manifest_path = (
            _ROOT / f"docs/roadmap-v{version}/github-issues/filing-manifest.json"
        )
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        ids.update(entry["id"] for entry in manifest["issues"])
    return ids


# --- derived axis checks --------------------------------------------------


def test_engine_published_axes_match_the_recorded_current_values() -> None:
    """Package, ProjectSpec protocol and manifest protocol "Current" cells
    are the live engine's own, not literals in the doc."""
    axis = _axis_current()
    info = get_engine_info()

    assert axis["`forge-template` package"] == info.package_version
    assert axis["ProjectSpec protocol"] == _join(SUPPORTED_PROJECTSPEC_PROTOCOLS)
    assert axis["Component manifest protocol"] == _join(
        SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS
    )
    assert info.projectspec_protocols == SUPPORTED_PROJECTSPEC_PROTOCOLS
    assert info.component_manifest_protocols == SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS


def test_component_current_versions_match_discovery() -> None:
    axis = _axis_current()
    for component in discover_components():
        row = f"`{component.id}` component"
        assert row in axis, f"{row}: not classified"
        assert axis[row] == component.version


def test_foundation_source_protocol_current_value_is_live() -> None:
    axis = _axis_current()
    foundation = load_foundation_source(_FOUNDATION_TOML)
    assert axis["Foundation source protocol"] == str(foundation.foundation_version)


def test_unpublished_protocol_axes_agree_with_the_policy_state_table() -> None:
    """Option-schema and organisation-policy protocols are not engine-published;
    the contract's "Current" cell must match compatibility-policy.md's living
    state table rather than drift from it."""
    contract = _axis_current()
    policy = _policy_current()
    shared = set(contract) & set(policy)
    assert {"Option-schema protocol", "Organisation-policy protocol"} <= shared
    for axis in shared:
        assert contract[axis] == policy[axis], (
            f"{axis}: contract says {contract[axis]!r}, "
            f"policy table says {policy[axis]!r}"
        )


def _join(protocols: tuple[int, ...]) -> str:
    return _normalise(", ".join(str(p) for p in protocols))


# --- acceptance matrix ---------------------------------------------------


def test_every_matrix_row_names_a_filed_issue() -> None:
    filed = _filed_issue_ids()
    tokens = _matrix_owner_tokens()
    assert tokens, "no owner tokens parsed from the acceptance matrix"
    for token in tokens:
        assert token in filed, f"acceptance matrix cites unfiled issue {token}"


def test_every_provider_child_owns_at_least_one_matrix_row() -> None:
    owned = set(_matrix_owner_tokens())
    missing = sorted(_PROVIDER_CHILDREN - owned)
    assert not missing, f"provider children with no acceptance row: {missing}"


# --- FT-15.04 parity-row reconciliation (AC-3) --------------------------


def test_no_parity_matrix_row_still_needs_a_bounded_issue() -> None:
    offenders = [
        row["key"] for row in _parity_rows() if "needs a bounded issue" in row["owner"]
    ]
    assert not offenders, (
        f"engine-default-parity.md rows still unreconciled: {offenders}"
    )


def test_every_provider_owned_parity_gap_cites_a_filed_issue() -> None:
    filed = _filed_issue_ids()
    for row in _parity_rows():
        if row["status"] != "gap" or row["disposition"] != "provider":
            continue
        cited = _ISSUE_TOKEN.findall(row["owner"])
        assert cited, f"{row['key']}: provider gap row cites no issue"
        for token in cited:
            assert token in filed, f"{row['key']}: cites unfiled issue {token}"


# --- failure taxonomy --------------------------------------------------


def test_invalid_selection_rejects_as_validate_from_plan_and_render() -> None:
    """The failure table says `invalid-component-selection` carries
    `operation="validate"`; confirm it at runtime through both entry points,
    never `operation="render"`."""
    payload = {
        "protocol_version": 1,
        "project": {
            "name": "Cutover Gates Fixture",
            "package_name": "cutover_gates_fixture",
            "repository_name": "cutover-gates-fixture",
            "description": "FT-15.04 failure-taxonomy fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        # data-science requires jupyter; omitting it is an unsatisfied edge.
        "components": {
            "archetype": "data-science",
            "capabilities": [],
            "platforms": [],
        },
        "component_options": {},
    }
    spec = parse_project_spec(payload)
    for call in (plan_generation, render_project):
        try:
            call(spec)
        except ForgeEngineError as error:
            assert error.code is EngineErrorCode.INVALID_COMPONENT_SELECTION
            assert error.operation == "validate"
        else:  # pragma: no cover - defensive
            raise AssertionError(f"{call.__name__} did not reject the bad selection")


def test_contract_names_its_exclusions_literally() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "FT-ROADMAP-01-EX-02" in text
    assert "FT-ROADMAP-01-EX-04" in text
    assert "FT-ROADMAP-01-AC-04" in text
    assert "FT-ROADMAP-01-AC-05" in text


# --- axis state: FT-17.01 has moved two of the three, FT-17.06 moves the last


def test_package_is_still_on_the_0_4_line() -> None:
    assert get_engine_info().package_version.startswith("0.4."), (
        "package version moved -- FT-17.06 releases 0.5.0; revisit "
        "docs/cutover-compatibility-and-acceptance.md and this pin"
    )


def test_manifest_protocol_three_is_published_and_backward_compatible() -> None:
    assert SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS == (1, 2, 3), (
        "manifest protocol 3 (FT-17.01 / ADR 0062) is expected published; a "
        "protocol-1 or protocol-2 manifest must still be accepted"
    )
    assert get_engine_info().component_manifest_protocols == (1, 2, 3)


def test_generation_metadata_error_codes_are_shipped() -> None:
    shipped = {code.value for code in EngineErrorCode}
    assert shipped == _SHIPPED_ERROR_CODES, (
        "the EngineErrorCode set is the seven original values plus exactly the "
        "two generation-metadata codes; nothing else may join it in the cutover"
    )
    for code in (
        EngineErrorCode.INVALID_GENERATION_METADATA,
        EngineErrorCode.UNSUPPORTED_GENERATION_METADATA,
    ):
        assert code.value in _GENERATION_METADATA_ERROR_CODES


def test_engine_info_publishes_metadata_version() -> None:
    assert "metadata_version" in EngineInfo.model_fields, (
        "EngineInfo.metadata_version is expected published -- FT-17.01 / ADR 0062"
    )
    assert get_engine_info().metadata_version == 1


def test_public_facade_grows_only_additively() -> None:
    assert set(forge_template.__all__) == _FROZEN_PUBLIC_API, (
        "forge_template.__all__ changed -- the cutover adds names additively "
        "and renames or removes nothing; update _FROZEN_PUBLIC_API only for a "
        "reviewed additive change"
    )


def test_tripwire_copier_has_no_migrations_block() -> None:
    """Decision 3: the direct-Copier path is retained and not restructured, so
    no `_migrations` block is introduced by the cutover."""
    text = _COPIER.read_text(encoding="utf-8")
    assert not re.search(r"(?m)^_migrations:", text), (
        "copier.yml gained a _migrations block -- a template path moved; "
        "decision 3 (retain, do not restructure) needs revisiting"
    )
