"""Ported from scripts/test-combos.sh: scaffolds every meaningful answer
combination, asserts the render is clean, and runs the same checks CI runs.

Failures accumulate into one list per combo rather than stopping at the
first, matching the bash script's `FAILURES` counter -- one broken step
should not mask the rest.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

import pytest
from copier import run_copy

from forge_template import render
from tests.conftest import resolve_src, run_cmd

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.combos

# 1-3 are the build_backend x versioning pairs. 4 flips every remaining
# conditional at once, so no branch is untested -- matches test-combos.sh.
COMBOS: dict[str, dict[str, Any]] = {
    "c1-uvbuild-static": {"build_backend": "uv_build"},
    "c2-hatch-static": {"build_backend": "hatchling", "versioning": "static"},
    "c3-hatch-vcs": {"build_backend": "hatchling", "versioning": "vcs"},
    "c4-kitchen-sink": {
        "build_backend": "hatchling",
        "versioning": "vcs",
        "type_checking": "both",
        "use_docs": True,
        "coverage_fail_under": 80,
        "changelog_tool": "manual",
        "dependency_updates": "dependabot",
    },
}


@pytest.mark.parametrize("name", sorted(COMBOS), ids=sorted(COMBOS))
def test_combo(
    name: str,
    combos_workdir: Path,
    request: pytest.FixtureRequest,
    from_git: bool,
) -> None:
    errors: list[str] = []
    out = combos_workdir / name
    shutil.rmtree(out, ignore_errors=True)
    src, vcs_ref = resolve_src(from_git, request)

    run_copy(
        src_path=src,
        dst_path=out,
        vcs_ref=vcs_ref,
        data={
            "project_name": f"Test {name}",
            "github_org": "test-org",
            "author_name": "Test User",
            "author_email": "test@example.com",
            **COMBOS[name],
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )

    errors += render.check_all(out, require_commit=from_git)

    uses_hatch_vcs = "hatch-vcs" in (out / "pyproject.toml").read_text(encoding="utf-8")
    if uses_hatch_vcs:
        tag = run_cmd(["git", "tag", "v0.1.0"], out)
        if tag.returncode != 0:
            errors.append(f"could not tag (is there a commit?): {tag.stderr}")

    # ---- CI-equivalent checks, same order as test-combos.sh -----------------
    checks: list[tuple[list[str], str]] = [
        (["uv", "lock", "--check"], "lockfile stale"),
        (["uv", "run", "ruff", "format", "--check", "."], "format"),
        (["uv", "run", "ruff", "check", "."], "lint"),
        (["uv", "run", "poe", "typecheck"], "typecheck"),
        (["uv", "run", "pytest", "-q"], "tests"),
    ]
    for cmd, label in checks:
        result = run_cmd(cmd, out)
        if result.returncode != 0:
            errors.append(f"{label}:\n{result.stdout}\n{result.stderr}")

    build = run_cmd(["uv", "build"], out)
    if build.returncode != 0:
        errors.append(f"build:\n{build.stdout}\n{build.stderr}")
    else:
        dist_dir = out / "dist"
        if uses_hatch_vcs:
            errors += render.check_version_resolved(dist_dir)
        wheel = next(dist_dir.glob("*.whl"), None)
        if wheel is None:
            errors.append("build: no wheel produced")
        else:
            errors += render.check_wheel_contents(wheel)

    if (out / "mkdocs.yml").is_file():
        docs = run_cmd(["uv", "run", "mkdocs", "build", "--strict"], out)
        if docs.returncode != 0:
            errors.append(f"docs build:\n{docs.stdout}\n{docs.stderr}")

    errors += render.check_tree_clean(out)
    errors += render.check_env_example_tracked(out)

    assert not errors, "\n\n".join(errors)
