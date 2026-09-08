"""Executable guard for docs/dependency-updates.md and .github/dependabot.yml.

The `uv` ecosystem entry must stay bounded: every dependency in
``pyproject.toml`` that carries a deliberate strict upper bound needs a
matching ``version-update:semver-major`` ignore rule, and an ignore rule must
not exist for a dependency that has no upper bound (a gate with no bound is a
lie -- the bound is what actually stops resolution). The bounded set is
derived here at run time, so a bound added later without a gate fails the fast
suite. Follows ``tests/test_compatibility_policy.py``'s style: expected shape
written literally, drift surfaces as a failing assertion naming both sides.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

_ROOT = Path(__file__).parents[1]
_PYPROJECT = _ROOT / "pyproject.toml"
_DEPENDABOT = _ROOT / ".github" / "dependabot.yml"
_POLICY_DOC = _ROOT / "docs" / "dependency-updates.md"
_LINKING_DOCS = (
    _ROOT / "docs" / "README.md",
    _ROOT / "CONTRIBUTING.md",
    _ROOT / "CLAUDE.md",
)

_UPPER_BOUND_OPERATORS = ("<", "<=", "~=", "==", "===")


def _dependabot() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(_DEPENDABOT.read_text(encoding="utf-8"))
    return data


def _entry(ecosystem: str) -> dict[str, Any]:
    for entry in _dependabot()["updates"]:
        if entry.get("package-ecosystem") == ecosystem:
            result: dict[str, Any] = entry
            return result
    pytest.fail(f".github/dependabot.yml has no {ecosystem!r} update entry")


def _bounded_dependencies() -> dict[str, str]:
    """{canonical name: requirement string} for every dependency in
    ``[project.dependencies]`` or a ``[dependency-groups]`` list whose
    specifier set carries an upper bound."""
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    specs: list[str] = list(data["project"]["dependencies"])
    for group in data.get("dependency-groups", {}).values():
        specs += [item for item in group if isinstance(item, str)]

    bounded: dict[str, str] = {}
    for spec in specs:
        requirement = Requirement(spec)
        if any(s.operator in _UPPER_BOUND_OPERATORS for s in requirement.specifier):
            bounded[canonicalize_name(requirement.name)] = spec
    return bounded


def _semver_major_ignored() -> set[str]:
    """Canonical names the `uv` entry blocks semver-major updates for."""
    ignored: set[str] = set()
    for rule in _entry("uv").get("ignore", []):
        name = str(rule.get("dependency-name", ""))
        if "version-update:semver-major" in rule.get("update-types", []):
            ignored.add(canonicalize_name(name))
    return ignored


def test_uv_entry_matches_the_documented_policy() -> None:
    """docs/dependency-updates.md's "Scope": weekly Monday, chore prefix,
    type:chore + area:packaging, five open PRs, dev tooling grouped."""
    uv = _entry("uv")
    assert uv["directory"] == "/"
    assert uv["schedule"] == {"interval": "weekly", "day": "monday"}
    assert uv["open-pull-requests-limit"] == 5
    assert set(uv["labels"]) == {"type:chore", "area:packaging"}
    assert uv["commit-message"] == {"prefix": "chore"}
    group = uv["groups"]["dev-tooling"]
    assert group["dependency-type"] == "development"
    assert set(group["update-types"]) == {"minor", "patch"}


def test_every_bounded_dependency_is_gated_and_nothing_else_is() -> None:
    """The self-arming half: the semver-major ignore set equals the set of
    upper-bounded dependencies exactly, in both directions."""
    bounded = _bounded_dependencies()
    gated = _semver_major_ignored()

    missing = sorted(set(bounded) - gated)
    assert not missing, (
        "upper-bounded in pyproject.toml but no version-update:semver-major "
        f"ignore rule in .github/dependabot.yml's uv entry: {missing} "
        "(see docs/dependency-updates.md)"
    )
    spurious = sorted(gated - set(bounded))
    assert not spurious, (
        "semver-major ignore rule with no matching upper bound in "
        f"pyproject.toml: {spurious} -- a gate with no bound does nothing; "
        "remove the rule or add the bound"
    )


def test_the_three_engine_runtime_lines_are_among_the_gated_set() -> None:
    """The gated set is derived, so pin the three that matter most literally:
    the published wheel's resolvable range for every engine consumer."""
    gated = _semver_major_ignored()
    for name in ("jinja2", "packaging", "pydantic"):
        assert name in gated, f"{name} (engine runtime) is not semver-major gated"


def test_github_actions_entry_is_left_intact() -> None:
    """Acceptance criterion 6: the existing github-actions automation is
    unchanged -- still weekly Monday, type:chore + area:ci, ci prefix."""
    actions = _entry("github-actions")
    assert actions["directory"] == "/"
    assert actions["schedule"] == {"interval": "weekly", "day": "monday"}
    assert actions["labels"] == ["type:chore", "area:ci"]
    assert actions["commit-message"] == {"prefix": "ci"}


def test_policy_doc_exists_and_is_linked_from_the_canonical_entry_points() -> None:
    """A living policy nobody links to is dead documentation."""
    assert _POLICY_DOC.is_file()
    link = re.compile(r"\]\([^)]*dependency-updates\.md[^)]*\)")
    for path in _LINKING_DOCS:
        text = path.read_text(encoding="utf-8")
        assert link.search(text), f"{path.name} does not link dependency-updates.md"
