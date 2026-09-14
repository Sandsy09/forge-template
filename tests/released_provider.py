"""Shared harness for the released-provider cutover suites (FT-18.01).

`tests/test_released_client_compatibility.py` (row 338 of the acceptance
matrix, docs/cutover-compatibility-and-acceptance.md) and
`tests/test_released_provider_cutover.py` (row 339) both need the *published*
`forge-template` artefacts, digest-verified against the identities
FT-17.06 recorded in docs/cutover-provider-release.md -- never the working
tree and never a bare index resolution, which could silently accept a
re-uploaded or substituted file. That download-and-verify step, and (for row
339 only) building the candidate `create-forge` client from the sibling
working tree, are shared here.

Nothing in this module imports `forge_template` or `create_forge`: like
`../create-forge/tests/installed_client.py`, everything is read back through
subprocesses in the environment under test, never the pytest process's own
interpreter -- the same isolation boundary FT-14.02 (ADR 0057) established
for `tests/test_cross_repository_validation.py`.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from forge_template.schema import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# A generation (real `uv lock` resolution), a full `poe check` (pre-commit
# hook provisioning, a live Jupyter kernel), or a wheel build can legitimately
# take a while; this bounds a true hang without flaking on a slow machine or
# cold package cache -- the same value test_cross_repository_validation.py
# uses.
SUBPROCESS_TIMEOUT = 1800

# The reviewed, immutable release this issue pairs against. Both the version
# and the two artefact identities are pinned to
# docs/cutover-provider-release.md:67-70 -- FT-17.06's own published-artefact
# audit. A change to either value here must be a *new* record (a corrected
# `0.5.1`), never an edit of an existing one: see this issue's contingency
# for a provider defect,
# docs/adr/0067-validate-the-integrated-engine-default-cutover.md.
ENGINE_VERSION = "0.5.0"

# The candidate client this issue validates. Not on PyPI -- CF-18.07 left its
# publication gated on this issue -- so it can only be built from the sibling
# working tree, which is why row 339 (unlike row 338) cannot be hermetic.
CLIENT_VERSION = "0.4.0"
CLIENT_ENGINE_RANGE = ">=0.5,<0.6"

_PYPI_JSON_URL = "https://pypi.org/pypi/forge-template/{version}/json"
_DOWNLOAD_TIMEOUT = 60


@dataclass(frozen=True, slots=True)
class ArtefactIdentity:
    """One published artefact's expected name, size and SHA-256 digest."""

    filename: str
    size: int
    sha256: str


# docs/cutover-provider-release.md:69-70, verified against a live PyPI JSON
# API read during FT-18.01 planning and re-verified by
# test_the_published_artefacts_match_their_recorded_identities every run.
WHEEL = ArtefactIdentity(
    filename="forge_template-0.5.0-py3-none-any.whl",
    size=108_247,
    sha256="dffaad1eae884856a3828edc2a31f889fcb44f233b6e19c85dc7d2cc9fc6a023",
)
SDIST = ArtefactIdentity(
    filename="forge_template-0.5.0.tar.gz",
    size=738_075,
    sha256="4bcd49a43749d73b2c7bb38122211b1824078470276706d4aa3608d15fd612ba",
)


@dataclass(frozen=True, slots=True)
class VerifiedDownload:
    """One artefact downloaded from PyPI and confirmed byte-identical to its
    pinned identity -- the evidence for `docs/cutover-provider-release.md`'s
    published artefacts, re-collected rather than trusted.
    """

    identity: ArtefactIdentity
    path: Path


def _pypi_release_metadata(version: str) -> dict[str, object]:
    """Fetch PyPI's own JSON metadata for one `forge-template` release.

    Network-dependent by design -- see `download_verified_artefact`'s skip
    policy. Raised errors are caught by the caller, not here, so a caller
    that wants a hard failure (rather than a skip) can choose that.
    """
    url = _PYPI_JSON_URL.format(version=version)
    with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as response:
        payload: dict[str, object] = json.loads(response.read())
    return payload


def download_verified_artefact(
    identity: ArtefactIdentity, dest_dir: Path
) -> VerifiedDownload:
    """Download one published `forge-template` artefact and verify it three
    ways against `identity`: PyPI's own reported size and digest (before a
    single byte is downloaded -- catches a re-upload or yank immediately),
    then the downloaded bytes' own size and re-computed SHA-256.

    A transport failure (network unavailable, PyPI unreachable) skips the
    test -- the same convention `../create-forge/tests/test_e2e_installed_cutover.py`
    uses for a real external dependency. A digest mismatch is never a skip:
    it means the identity pinned in `docs/cutover-provider-release.md` no
    longer matches what PyPI serves, which is exactly the defect this harness
    exists to catch.
    """
    try:
        metadata = _pypi_release_metadata(ENGINE_VERSION)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.skip(f"PyPI unreachable: {exc}")

    urls = metadata.get("urls")
    assert isinstance(urls, list), f"malformed PyPI response for {ENGINE_VERSION}"
    matches = [entry for entry in urls if entry.get("filename") == identity.filename]
    assert len(matches) == 1, (
        f"expected exactly one {identity.filename} release file, found "
        f"{len(matches)}: {[m.get('filename') for m in urls]}"
    )
    entry = matches[0]

    reported_size = entry["size"]
    reported_sha256 = entry["digests"]["sha256"]
    assert reported_size == identity.size, (
        f"{identity.filename}: PyPI reports {reported_size} bytes, "
        f"docs/cutover-provider-release.md pins {identity.size}"
    )
    assert reported_sha256 == identity.sha256, (
        f"{identity.filename}: PyPI reports sha256:{reported_sha256}, "
        f"docs/cutover-provider-release.md pins sha256:{identity.sha256}"
    )

    download_url = entry["url"]
    try:
        with urllib.request.urlopen(
            download_url, timeout=_DOWNLOAD_TIMEOUT
        ) as response:
            data = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.skip(f"PyPI download unreachable: {exc}")

    dest = dest_dir / identity.filename
    dest.write_bytes(data)

    actual_size = len(data)
    actual_sha256 = hashlib.sha256(data).hexdigest()
    assert actual_size == identity.size, (
        f"{identity.filename}: downloaded {actual_size} bytes, "
        f"pinned identity is {identity.size}"
    )
    assert actual_sha256 == identity.sha256, (
        f"{identity.filename}: downloaded sha256:{actual_sha256}, "
        f"pinned identity is sha256:{identity.sha256}"
    )

    return VerifiedDownload(identity=identity, path=dest)


def run(
    cmd: Sequence[str],
    cwd: Path,
    *,
    env: Mapping[str, str] | None = None,
    timeout: int = SUBPROCESS_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def assert_success(result: subprocess.CompletedProcess[str], *, context: str) -> None:
    assert result.returncode == 0, (
        f"{context} failed (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )


def is_windows_venv(venv: Path) -> bool:
    return (venv / "Scripts").is_dir()


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if is_windows_venv(venv) else "bin/python")


def venv_console_script(venv: Path, name: str) -> Path:
    if is_windows_venv(venv):
        return venv / "Scripts" / f"{name}.exe"
    return venv / "bin" / name


def make_venv(venv: Path, *, python: str = "3.13") -> Path:
    """Create an isolated venv at `venv` and return its interpreter path."""
    created = run(["uv", "venv", "--python", python, str(venv)], REPO_ROOT)
    assert_success(created, context=f"uv venv --python {python} {venv}")
    return venv_python(venv)


def child_env(config_home: Path, *, extra_path: Path | None = None) -> dict[str, str]:
    """Subprocess environment for a real `create-forge`/`uv` invocation.

    Strips `FORGE_*` (create-forge's own env-config prefix) and points
    `XDG_CONFIG_HOME` at a throwaway directory so no config on this machine
    can change what gets generated. Strips the venv-leak variables `uv run`
    sets for *this* pytest process so they cannot redirect the child
    invocations into this repository's own environment -- the same shape
    `test_cross_repository_validation.py`'s `child_env` fixture uses.

    `extra_path`, when given, is prepended to `PATH` -- needed once a
    generation must find the paired venv's own `uv` before any other `uv` on
    the machine (CF-18.03's `new` lifecycle shells out to `uv` for the
    lockfile and, when selected, pre-commit hook installation).
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("FORGE_")}
    for leak in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONHOME", "PYTHONPATH"):
        env.pop(leak, None)
    env["XDG_CONFIG_HOME"] = str(config_home)
    if extra_path is not None:
        env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"
    # CF-18.03's post-rename lifecycle runs `git init` + an initial commit;
    # a bare CI runner (or this harness's own throwaway HOME/XDG isolation)
    # may have no git identity configured, unlike tests/conftest.py's
    # `_git_identity` autouse fixture, which only sets the *global* config
    # this harness's isolated environment does not necessarily inherit.
    env.setdefault("GIT_AUTHOR_NAME", "Released Provider Cutover")
    env.setdefault("GIT_AUTHOR_EMAIL", "released-provider-cutover@example.invalid")
    env.setdefault("GIT_COMMITTER_NAME", "Released Provider Cutover")
    env.setdefault("GIT_COMMITTER_EMAIL", "released-provider-cutover@example.invalid")
    return env


def site_packages(python: Path, cwd: Path = REPO_ROOT) -> Path:
    result = run(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        cwd,
    )
    assert_success(result, context=f"{python} -c sysconfig.get_path")
    return Path(result.stdout.strip())


def direct_url(site_packages_dir: Path, dist_info_glob: str) -> dict[str, object]:
    matches = sorted(site_packages_dir.glob(dist_info_glob))
    assert len(matches) == 1, (dist_info_glob, matches)
    payload_path = matches[0] / "direct_url.json"
    assert payload_path.is_file(), payload_path
    payload: dict[str, object] = json.loads(payload_path.read_text(encoding="utf-8"))
    return payload
