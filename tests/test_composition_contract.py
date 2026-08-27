"""Composition contract tests: golden fixtures, invalid catalogues, and the
determinism guarantee composition-order.md states.

See docs/composition-fixtures.md for what these fixtures prove and how to
regenerate them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from forge_template.component_manifest import load_component_manifest
from forge_template.composition import composition_plan
from forge_template.file_conflicts import resolve_output_plan
from forge_template.schema import REPO_ROOT
from tests.composition_contract import FIXTURES, SCENARIOS, compose, project_spec

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
INVALID_FIXTURES = Path(__file__).parent / "fixtures" / "invalid_components"


def _invalid_manifest_paths(*identifiers: str) -> list[Path]:
    return [
        INVALID_FIXTURES / identifier / "component.toml" for identifier in identifiers
    ]


# -----------------------------------------------------------------------------
# Golden fixtures
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_composed_output_matches_golden(scenario: str, update_goldens: bool) -> None:
    spec, manifest_paths = SCENARIOS[scenario]
    actual = compose(spec, manifest_paths)
    golden_path = GOLDEN_DIR / f"{scenario}.json"

    if update_goldens:
        golden_path.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        pytest.skip(f"updated golden fixture: {golden_path}")

    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    assert actual == expected


# -----------------------------------------------------------------------------
# Invalid catalogues -- each rejected at a different validation layer, before
# any output is produced
# -----------------------------------------------------------------------------


def test_cyclic_catalogue_is_rejected_before_any_output() -> None:
    manifest_paths = [
        FIXTURES / "library" / "component.toml",
        *_invalid_manifest_paths("cycle-a", "cycle-b"),
    ]
    spec = project_spec(archetype="library", capabilities=("cycle-a", "cycle-b"))

    with pytest.raises(ValueError, match="cycle"):
        composition_plan(spec, manifest_paths)


def test_conflicting_selection_is_rejected_before_any_output() -> None:
    manifest_paths = [
        FIXTURES / "library" / "component.toml",
        *_invalid_manifest_paths("conflicting-first", "conflicting-second"),
    ]
    spec = project_spec(
        archetype="library",
        capabilities=("conflicting-first", "conflicting-second"),
    )

    with pytest.raises(ValueError, match="conflicts with selected"):
        composition_plan(spec, manifest_paths)


def test_colliding_output_targets_are_rejected_before_any_file_operation() -> None:
    manifest_paths = [
        FIXTURES / "library" / "component.toml",
        *_invalid_manifest_paths("colliding-first", "colliding-second"),
    ]
    spec = project_spec(
        archetype="library",
        capabilities=("colliding-first", "colliding-second"),
    )

    # Each manifest loads and selects cleanly on its own -- the collision
    # only exists once both components' output plans are resolved together.
    plan = composition_plan(spec, manifest_paths)
    with pytest.raises(
        ValueError, match=r"colliding-first.*colliding-second.*shared\.txt"
    ):
        resolve_output_plan(plan)


def test_invalid_catalogue_fixtures_load_individually() -> None:
    """Each invalid-catalogue fixture is individually well-formed: rejection
    comes from composing it with others, not from a malformed manifest.
    """
    for identifier in (
        "cycle-a",
        "cycle-b",
        "conflicting-first",
        "conflicting-second",
        "colliding-first",
        "colliding-second",
    ):
        load_component_manifest(INVALID_FIXTURES / identifier / "component.toml")


# -----------------------------------------------------------------------------
# Determinism
# -----------------------------------------------------------------------------


def test_composed_output_is_invariant_to_manifest_input_order() -> None:
    spec, manifest_paths = SCENARIOS["full"]

    forward = compose(spec, manifest_paths)
    reversed_result = compose(spec, dict(reversed(manifest_paths.items())))

    assert forward == reversed_result


def test_composed_output_is_invariant_to_pythonhashseed() -> None:
    """Exercises composition-order.md's determinism guarantee, which names
    PYTHONHASHSEED explicitly. A single pytest process has one fixed seed,
    so this spawns fresh subprocesses to actually vary it.
    """
    script = (
        "from tests.composition_contract import scenario_result;"
        "import hashlib, json;"
        "print(hashlib.sha256("
        "json.dumps(scenario_result('full'), sort_keys=True).encode()"
        ").hexdigest())"
    )
    hashes = set()
    for seed in ("0", "1", "42", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        hashes.add(result.stdout.strip())

    assert len(hashes) == 1
