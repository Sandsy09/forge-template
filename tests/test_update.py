"""Ported from scripts/test-update.sh: validates `copier update` -- local
edits survive, template changes arrive, conflicts surface rather than
silently clobbering.

`test_local_edits_survive_update` is the ported scenario. `test_latest_tag_to_head`
is what CI's separate `update-compat` job checked (today's HEAD against the
last real release) -- not a duplicate of the first test, a different
scenario, kept distinct so neither gets lost in the merge.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
from copier import run_copy, run_update

from forge_template.schema import REPO_ROOT
from tests.conftest import latest_tag, run_cmd

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.update

_CONFLICT_SUFFIXES = {".md", ".toml", ".yml", ".yaml", ".py"}


def _resolve_conflicts(root: Path) -> None:
    """Strip `<<<<<<<`/`=======`/`>>>>>>>` markers, keeping the incoming
    (template) side, so a conflicted merge can still be verified end-to-end.
    """
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in _CONFLICT_SUFFIXES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            continue
        if not any(line.startswith("<<<<<<<") for line in lines):
            continue
        kept, skip = [], False
        for line in lines:
            if line.startswith("<<<<<<<"):
                continue
            if line.startswith("======="):
                skip = True
                continue
            if line.startswith(">>>>>>>"):
                skip = False
                continue
            if not skip:
                kept.append(line)
        path.write_text("".join(kept), encoding="utf-8")


def test_local_edits_survive_update(tmp_path: Path) -> None:
    """Clone the template, scaffold from its latest tag, make local edits a
    real user would make, release a new template version, update, and
    confirm both sides of the merge survived.
    """
    errors: list[str] = []
    tmpl = tmp_path / "template"
    proj = tmp_path / "project"
    subprocess.run(["git", "clone", "-q", str(REPO_ROOT), str(tmpl)], check=True)

    base_tag = latest_tag(tmpl)
    if base_tag is None:
        pytest.skip("template has no tags yet -- run: git tag v0.1.0")

    run_copy(
        src_path=str(tmpl),
        dst_path=proj,
        vcs_ref=base_tag,
        data={
            "project_name": "Update Test",
            "github_org": "test-org",
            "build_backend": "hatchling",
            "versioning": "static",
        },
        defaults=True,
        unsafe=True,
        quiet=True,
    )

    answers = (proj / ".copier-answers.yml").read_text(encoding="utf-8")
    if f"_commit: {base_tag}" not in answers:
        errors.append(f"answers file missing or wrong _commit (expected {base_tag})")

    # ---- local edits a real user would make ----------------------------------
    # (a) edit a templated file -- the hard case.
    pyproject = proj / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            "dependencies = []", 'dependencies = ["httpx>=0.28"]'
        ),
        encoding="utf-8",
    )
    # (b) add a file the template knows nothing about.
    local_pkg = proj / "src" / "update_test"
    local_pkg.mkdir(parents=True, exist_ok=True)
    (local_pkg / "client.py").write_text(
        '"""Local module the template has never seen."""\n\n\n'
        'def fetch() -> str:\n    """Return a greeting."""\n    return "local"\n',
        encoding="utf-8",
    )
    # (c) edit a templated doc.
    readme = proj / "README.md"
    marker = "## Development"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            marker,
            "## Local section\n\nAdded by the project team, not the template.\n\n"
            + marker,
            1,
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(
        ["git", "commit", "-q", "--no-verify", "-m", "feat: local customisations"],
        cwd=proj,
        check=True,
    )

    # ---- change the template and release a new version -----------------------
    # (a) new file every project should receive.
    (tmpl / "template" / "CODE_OF_CONDUCT.md.jinja").write_text(
        "# Code of Conduct\n\nContact {{ author_email or 'the maintainers' }} to "
        "report an issue.\n",
        encoding="utf-8",
    )
    # (b) change an existing templated file -- the same file the project edited.
    pyproject_tmpl = tmpl / "template" / "pyproject.toml.jinja"
    pyproject_tmpl.write_text(
        pyproject_tmpl.read_text(encoding="utf-8").replace(
            '"RUF",       # ruff-specific',
            '"RUF",       # ruff-specific\n    "TID",       # flake8-tidy-imports',
        ),
        encoding="utf-8",
    )
    # (c) change a file the project also edited -- should conflict.
    readme_tmpl = tmpl / "template" / "README.md.jinja"
    with readme_tmpl.open("a", encoding="utf-8") as fh:
        fh.write("\n## Support\n\nRaise an issue on the repository.\n")
    subprocess.run(["git", "add", "-A"], cwd=tmpl, check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-q",
            "-m",
            "feat: add code of conduct, TID lint rules, support section",
        ],
        cwd=tmpl,
        check=True,
    )
    new_tag = "v0.2.0"
    subprocess.run(["git", "tag", new_tag], cwd=tmpl, check=True)

    # ---- update ----------------------------------------------------------------
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=proj,
        capture_output=True,
        text=True,
        check=True,
    )
    if status.stdout.strip():
        errors.append(
            "working tree dirty before update (update would refuse otherwise)"
        )

    run_update(
        dst_path=proj,
        vcs_ref=new_tag,
        defaults=True,
        # The `copier update` CLI always passes overwrite=True (its own
        # rationale: only git-tracked subprojects can be updated, so the
        # user can review the diff before committing -- see copier/cli.py's
        # CopierUpdateSubApp). The Python API defaults to False and raises
        # "Enable overwrite to update a subproject" otherwise.
        overwrite=True,
        unsafe=True,
        quiet=True,
        conflict="inline",
    )

    # ---- assertions --------------------------------------------------------------
    answers = (proj / ".copier-answers.yml").read_text(encoding="utf-8")
    if f"_commit: {new_tag}" not in answers:
        errors.append(f"answers file did not advance to {new_tag}")
    if not (proj / "CODE_OF_CONDUCT.md").is_file():
        errors.append("new template file did not arrive")

    new_pyproject = pyproject.read_text(encoding="utf-8")
    if '"TID"' not in new_pyproject:
        errors.append("template change to pyproject.toml was lost")
    if "httpx" not in new_pyproject:
        errors.append("LOCAL edit to pyproject.toml was CLOBBERED")

    if not (local_pkg / "client.py").is_file():
        errors.append("untemplated local file was removed")

    new_readme = readme.read_text(encoding="utf-8")
    if "Local section" not in new_readme:
        errors.append("local README section was lost")

    conflicted = "<<<<<<<" in new_readme
    if not conflicted and "Support" not in new_readme:
        errors.append("template README change was lost")

    # ---- project still works, after resolving any conflict -----------------------
    if conflicted:
        _resolve_conflicts(proj)

    sync = run_cmd(["uv", "sync", "--all-groups"], proj)
    if sync.returncode != 0:
        errors.append(f"sync failed after update:\n{sync.stdout}\n{sync.stderr}")

    check = run_cmd(["uv", "run", "poe", "check"], proj)
    if check.returncode != 0:
        errors.append(f"checks FAILED after update:\n{check.stdout}\n{check.stderr}")

    assert not errors, "\n\n".join(errors)


def test_latest_tag_to_head(tmp_path: Path) -> None:
    """What CI's `update-compat` job checks: updating a project scaffolded
    from the last release up to HEAD must not explode. Skipped on the very
    first run, when no tag exists yet.
    """
    tag = latest_tag(REPO_ROOT)
    if tag is None:
        pytest.skip("no tags yet -- update-compat has nothing to compare against")

    proj = tmp_path / "project"
    run_copy(
        src_path=str(REPO_ROOT),
        dst_path=proj,
        vcs_ref=tag,
        data={"project_name": "Update Test", "github_org": "test-org"},
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "chore: baseline", "--allow-empty"],
        cwd=proj,
        check=True,
    )

    run_update(
        dst_path=proj,
        vcs_ref="HEAD",
        defaults=True,
        overwrite=True,
        unsafe=True,
        quiet=True,
        conflict="inline",
    )

    sync = run_cmd(["uv", "sync", "--all-groups"], proj)
    assert sync.returncode == 0, sync.stdout + sync.stderr

    check = run_cmd(["uv", "run", "poe", "check"], proj)
    assert check.returncode == 0, check.stdout + check.stderr
