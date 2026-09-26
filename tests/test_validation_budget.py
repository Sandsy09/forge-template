"""The approved validation budgets, tiers and escalation, executably.

`.github/validation-budgets.toml` is the machine-readable half of
`docs/validation-budget.md` (FT-26.01, ADR 0076). This module derives what it
can from the repository -- the catalogue, the workflows, the registered pytest
markers, the wheel's exclusion list -- so the file cannot drift from any of them
silently, and holds a **growth guard**: the catalogue's projected sweep cost
must stay under each sweep's approved failure limit, so the next capability
(which roughly doubles the composition count) fails the fast suite until a
tiering decision and a re-baseline are made deliberately.
"""

from __future__ import annotations

import importlib.util
import math
import re
import sys
import tomllib
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import pytest
import yaml

from forge_template import discover_components
from tests.composition_matrix import EXPECTED_COMPOSITION_COUNT, valid_compositions

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = tomllib.loads(
    (ROOT / ".github" / "validation-budgets.toml").read_text(encoding="utf-8")
)
_WORKFLOWS = (
    "test-template.yml",
    "linux-checks.yml",
    "runner-canary.yml",
    "release.yml",
)
_SWEEPS = {
    "linux-checks.yml:sweep-independence": "independent_seconds_per_composition",
    "linux-checks.yml:sweep-composition": "direct_seconds_per_composition",
}


def _workflow(name: str) -> dict[Any, Any]:
    text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    assert isinstance(document, dict)
    return document


def _job_ids() -> set[str]:
    return {f"{name}:{job}" for name in _WORKFLOWS for job in _workflow(name)["jobs"]}


def _display_names() -> set[str]:
    names: set[str] = set()
    for name in _WORKFLOWS:
        for job in _workflow(name)["jobs"].values():
            matrix = job.get("strategy", {}).get("matrix", {}).get("include", [])
            names.update(entry["name"] for entry in matrix)
            if "name" in job and "${{" not in job["name"]:
                names.add(job["name"])
    return names


def ceil_to_step(value: float, step: float) -> float:
    """Round up to a multiple of `step`, tolerating float noise."""
    return round(math.ceil(round(value / step, 9)) * step, 6)


def approved_limits(baseline_p90: float) -> tuple[float, float]:
    """The (warn, fail) minutes the approved rule gives a baseline p90."""
    rule = BUDGETS["rule"]
    warn = max(
        rule["floor_warn_minutes"],
        ceil_to_step(rule["warn_factor"] * baseline_p90, rule["step_minutes"]),
    )
    fail = max(
        rule["floor_fail_minutes"],
        ceil_to_step(rule["fail_factor"] * baseline_p90, rule["step_minutes"]),
    )
    return warn, fail


def projected_minutes(valid: int, seconds_per_composition: float) -> float:
    """A sweep's projected wall time for a catalogue of `valid` compositions."""
    return valid * seconds_per_composition / 60


# ---------------------------------------------------------------------------
# The rule and the approved numbers
# ---------------------------------------------------------------------------


def test_the_file_has_the_expected_shape() -> None:
    assert BUDGETS["schema"] == 1
    assert BUDGETS["baseline"]["runs"] >= BUDGETS["rule"]["min_baseline_runs"]
    assert {"critical_path", "cost", "rule", "escalation"} <= set(BUDGETS)


@pytest.mark.parametrize("entry", BUDGETS["job"], ids=lambda entry: entry["id"])
def test_every_job_limit_follows_the_approved_rule(entry: dict[str, Any]) -> None:
    warn, fail = approved_limits(entry["baseline_p90"])
    assert (entry["warn_minutes"], entry["fail_minutes"]) == (warn, fail), entry["id"]
    assert entry["warn_minutes"] < entry["fail_minutes"]
    assert entry["baseline_p50"] <= entry["baseline_p90"]


def test_the_approved_examples_in_the_contract_hold() -> None:
    """The figures quoted in ADR 0076 and the contract."""
    assert approved_limits(10.6) == (13.5, 16.0)
    assert approved_limits(5.3) == (7.0, 8.0)
    assert approved_limits(3.9) == (5.0, 6.0)
    assert approved_limits(2.6) == (3.5, 4.0)
    assert approved_limits(0.3) == (1.5, 2.0)


def test_the_critical_path_budget_is_the_approved_16_and_20_minutes() -> None:
    path = BUDGETS["critical_path"]
    assert (path["warn_minutes"], path["fail_minutes"]) == (16.0, 20.0)
    assert path["baseline_p90_minutes"] < path["warn_minutes"]


def test_a_single_job_can_never_exceed_the_critical_path_budget() -> None:
    """The slowest job's own failure limit must sit under the critical-path
    failure limit, or the per-job limit could never be the one that trips."""
    slowest = max(job["fail_minutes"] for job in BUDGETS["job"])
    assert slowest <= BUDGETS["critical_path"]["fail_minutes"]


# ---------------------------------------------------------------------------
# Counts derived from the catalogue
# ---------------------------------------------------------------------------


def test_composition_counts_match_the_catalogue() -> None:
    catalogue = discover_components()
    kinds = [component.kind for component in catalogue]
    raw = (
        kinds.count("archetype")
        * 2 ** kinds.count("capability")
        * 2 ** kinds.count("platform")
    )
    valid = valid_compositions()
    cost = BUDGETS["cost"]
    assert cost["valid_compositions"] == len(valid) == EXPECTED_COMPOSITION_COUNT
    assert cost["raw_candidates"] == raw
    assert cost["rejected_candidates"] == raw - len(valid)


def test_enumeration_is_deterministic_sorted_and_unique() -> None:
    first = valid_compositions()
    assert first == valid_compositions()
    assert list(first) == sorted(first)
    assert len(set(first)) == len(first)


# ---------------------------------------------------------------------------
# The growth guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("job_id", "cost_key"), sorted(_SWEEPS.items()))
def test_the_catalogue_stays_inside_each_sweeps_budget(
    job_id: str, cost_key: str
) -> None:
    """The next capability roughly doubles the count; when the projection
    reaches the approved failure limit, tier the work and re-baseline
    deliberately (docs/validation-budget.md, "Growth guard") rather than raising
    the limit to make this pass."""
    entry = next(job for job in BUDGETS["job"] if job["id"] == job_id)
    valid = len(valid_compositions())
    projected = projected_minutes(valid, BUDGETS["cost"][cost_key])
    assert projected < entry["fail_minutes"], (
        f"{job_id}: {valid} compositions project to {projected:.1f} min, at or "
        f"over the {entry['fail_minutes']} min failure limit"
    )


def test_a_doubled_catalogue_would_trip_the_guard_for_the_independent_sweep() -> None:
    """The guard has teeth at today's approved numbers: the independent-client
    sweep, at double the compositions, is over its failure limit."""
    entry = next(
        job
        for job in BUDGETS["job"]
        if job["id"] == "linux-checks.yml:sweep-independence"
    )
    doubled = projected_minutes(
        2 * len(valid_compositions()),
        BUDGETS["cost"]["independent_seconds_per_composition"],
    )
    assert doubled > entry["fail_minutes"]


# ---------------------------------------------------------------------------
# Accounting: no job, marker or display name can join unbudgeted
# ---------------------------------------------------------------------------


def _tier_jobs() -> dict[str, str]:
    owners: dict[str, str] = {}
    for tier in BUDGETS["tier"]:
        for job in tier["jobs"]:
            assert job not in owners, f"{job} is in two tiers"
            owners[job] = tier["id"]
    return owners


def test_every_workflow_job_is_in_exactly_one_tier_or_is_structural() -> None:
    tiered = set(_tier_jobs())
    structural = set(BUDGETS["structural"]["jobs"])
    assert tiered.isdisjoint(structural)
    assert tiered | structural == _job_ids()


def test_every_timed_job_names_its_tier_and_a_real_display_name() -> None:
    owners = _tier_jobs()
    names = _display_names()
    seen = set()
    for entry in BUDGETS["job"]:
        assert owners[entry["id"]] == entry["tier"], entry["id"]
        assert set(entry["display"]) <= names, entry["id"]
        seen.add(entry["id"])
    assert seen == set(owners), "every tiered job has an approved limit"


def _registered_markers() -> set[str]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers = pyproject["tool"]["pytest"]["ini_options"]["markers"]
    return {re.split(r"[:(]", marker, maxsplit=1)[0].strip() for marker in markers}


def test_every_registered_pytest_marker_belongs_to_a_tier() -> None:
    tiered = {marker for tier in BUDGETS["tier"] for marker in tier["markers"]}
    assert _registered_markers() <= tiered
    assert "fast" in tiered, "the unmarked default suite is tier T0"


def test_tier_ids_are_unique_and_ordered() -> None:
    ids = [tier["id"] for tier in BUDGETS["tier"]]
    assert ids == ["T0", "T1", "T2", "T3", "T4"]


# ---------------------------------------------------------------------------
# Guarantees
# ---------------------------------------------------------------------------


def test_every_guarantee_has_a_real_tier_and_real_pins() -> None:
    tiers = {tier["id"] for tier in BUDGETS["tier"]}
    ids = [item["id"] for item in BUDGETS["guarantee"]]
    assert len(ids) == len(set(ids))
    for item in BUDGETS["guarantee"]:
        assert item["tier"] in tiers, item["id"]
        assert item["pinned_by"], item["id"]
        for path in item["pinned_by"]:
            assert (ROOT / path).is_file(), f"{item['id']}: {path} does not exist"


def test_full_composition_coverage_is_mapped_to_the_exhaustive_tiers() -> None:
    by_id = {item["id"]: item["tier"] for item in BUDGETS["guarantee"]}
    assert by_id["every-valid-composition-renders"] == "T2"
    assert by_id["client-independence"] == "T3"


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------


def _check_only_modules() -> set[str]:
    path = ROOT / "scripts" / "check_wheel.py"
    spec = importlib.util.spec_from_file_location("check_wheel_for_budgets", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_wheel_for_budgets"] = module
    spec.loader.exec_module(module)
    return {f"src/{item}" for item in module._MUST_NOT_CONTAIN}


def is_sensitive(path: str) -> bool:
    """The escalation rule FT-26.02 implements: does a change to this path
    require the exhaustive sweeps on a pull request?"""
    escalation = BUDGETS["escalation"]
    if path in escalation["excluded_paths"]:
        return False
    return any(fnmatch(path, pattern) for pattern in escalation["sensitive_paths"])


def test_excluded_paths_are_exactly_the_wheels_check_only_modules() -> None:
    excluded = set(BUDGETS["escalation"]["excluded_paths"])
    assert excluded == _check_only_modules()
    for path in excluded:
        assert (ROOT / path).is_file(), path


def test_every_sensitive_pattern_matches_a_tracked_file() -> None:
    for pattern in BUDGETS["escalation"]["sensitive_paths"]:
        base = pattern.split("**")[0].rstrip("/") if "**" in pattern else pattern
        target = ROOT / base
        assert target.exists(), f"{pattern} matches nothing in the repository"


def test_every_engine_and_content_file_is_sensitive_except_check_only_modules() -> None:
    package = ROOT / "src" / "forge_template"
    excluded = set(BUDGETS["escalation"]["excluded_paths"])
    for path in package.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        assert is_sensitive(relative) == (relative not in excluded), relative


@pytest.mark.parametrize(
    ("path", "sensitive"),
    [
        ("src/forge_template/engine.py", True),
        ("src/forge_template/composition.py", True),
        ("src/forge_template/components/library/manifest.toml", True),
        ("src/forge_template/foundation/foundation.toml", True),
        ("src/forge_template/adr.py", False),
        ("src/forge_template/schema.py", False),
        ("tests/composition_matrix.py", True),
        ("tests/test_composition_sweep.py", True),
        ("uv.lock", True),
        (".github/workflows/linux-checks.yml", True),
        ("docs/dependency-audit.md", False),
        ("CONTRIBUTING.md", False),
        ("README.md", False),
        ("tests/test_living_docs.py", False),
        ("template/README.md.jinja", False),
    ],
)
def test_the_escalation_rule_classifies_representative_paths(
    path: str, sensitive: bool
) -> None:
    assert is_sensitive(path) is sensitive


def test_nothing_in_ci_changes_in_ft_26_01() -> None:
    """FT-26.01 approves budgets and a design; every protected check stays
    until FT-26.02's replacement coverage is approved. The required aggregate
    still needs the sweeps unconditionally."""
    jobs = _workflow("test-template.yml")["jobs"]
    assert jobs["linux"]["uses"] == "./.github/workflows/linux-checks.yml"
    assert "if" not in jobs["linux"], "the Linux call must not be conditional yet"
    linux = _workflow("linux-checks.yml")["jobs"]
    for sweep in ("sweep-composition", "sweep-independence"):
        assert "if" not in linux[sweep], f"{sweep} must still run on every pull request"


# ---------------------------------------------------------------------------
# The living contract stays in step with the budgets file
# ---------------------------------------------------------------------------

_CONTRACT = (ROOT / "docs" / "validation-budget.md").read_text(encoding="utf-8")


def test_the_contract_names_every_tier_and_guarantee() -> None:
    for tier in BUDGETS["tier"]:
        assert f"| {tier['id']} |" in _CONTRACT, tier["id"]
    for item in BUDGETS["guarantee"]:
        assert f"`{item['id']}`" in _CONTRACT, item["id"]


def test_the_contract_quotes_the_approved_numbers() -> None:
    path = BUDGETS["critical_path"]
    quoted = (
        f"warn {path['warn_minutes']:.0f} minutes, "
        f"fail {path['fail_minutes']:.0f} minutes"
    )
    assert quoted in _CONTRACT
    counts = BUDGETS["cost"]
    for figure in ("valid_compositions", "raw_candidates", "rejected_candidates"):
        assert f"{counts[figure]:,}" in _CONTRACT, figure


def test_the_contract_links_its_adr_and_the_budgets_file() -> None:
    assert "adr/0076-approve-validation-budgets-and-tiers.md" in _CONTRACT
    assert ".github/validation-budgets.toml" in _CONTRACT
    assert (
        ROOT / "docs" / "adr" / "0076-approve-validation-budgets-and-tiers.md"
    ).is_file()
