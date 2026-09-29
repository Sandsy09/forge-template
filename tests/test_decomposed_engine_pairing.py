"""Verify the decomposed engine as installed artefacts -- FT-25.03.

``pairing``-marked (``uv run poe pairing``): network-dependent and slow, a
deliberate local check like ``crossrepo``. Everything runs in fresh virtual
environments through subprocesses, never in this pytest interpreter, and
compares the candidate with the immutable published ``forge-template 0.6.0``
(downloaded from PyPI and digest-verified against
docs/streamlit-provider-release.md):

1. **Artefacts.** The candidate wheel, and a wheel built from the candidate
   sdist, each install cleanly; the public facade, the private engine
   modules and the package resources are present, and the check-only
   modules are absent.
2. **A minimal independent client** (``tests/independent_client_probe.py``,
   standard library + top-level ``forge_template`` only) observes exactly
   the same catalogue, output fingerprints, update plans and structured
   failures from all three installations -- and the fingerprints equal the
   checked-in baseline.
3. **The supported released client.** ``create-forge 0.5.0`` from PyPI
   (``forge-template>=0.6,<0.7``) generates byte-identical projects whether
   it resolves the published ``0.6.0`` or has the candidate wheel installed
   in its place.

See docs/engine-internals.md#validation-evidence.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from forge_template.schema import REPO_ROOT
from tests.composition_fingerprints import load_fingerprints, sweep_payload
from tests.composition_matrix import Composition, valid_compositions
from tests.released_provider import (
    ArtefactIdentity,
    assert_success,
    child_env,
    download_verified_artefact,
    make_venv,
    run,
    venv_console_script,
    venv_python,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

pytestmark = pytest.mark.pairing

PUBLISHED_VERSION = "0.6.0"
# docs/streamlit-provider-release.md, the FT-20.04 published-artefact audit.
PUBLISHED_WHEEL = ArtefactIdentity(
    filename="forge_template-0.6.0-py3-none-any.whl",
    size=115_232,
    sha256="cf21152242a81b6a19d5298521a77f504063091759b5cca721b3f527c64ac742",
)
RELEASED_CLIENT = "create-forge==0.5.0"

PROBE = Path(__file__).parent / "independent_client_probe.py"

_PRIVATE_MODULES = (
    "_discovery",
    "_errors",
    "_legacy_answers",
    "_models",
    "_provenance",
    "_rendering",
)
_CHECK_ONLY_MODULES = ("adr", "render", "schema", "github_actions")

_ANSWERS: Mapping[str, str] = {
    "project_description": "FT-25.03 decomposed-engine pairing fixture.",
    "license": "mit",
    "author_name": "Engine Pairing",
    "author_email": "engine-pairing@example.invalid",
}


@dataclass(frozen=True)
class Installation:
    label: str
    venv: Path
    python: Path


def _archetypes() -> tuple[str, ...]:
    return tuple(sorted({c.archetype for c in valid_compositions()}))


def _smallest(archetype: str) -> Composition:
    return min(
        (
            c
            for c in valid_compositions()
            if c.archetype == archetype and not c.platforms
        ),
        key=lambda c: (len(c.capabilities), c),
    )


def _largest(archetype: str, *, without: frozenset[str] = frozenset()) -> Composition:
    return max(
        (
            c
            for c in valid_compositions()
            if c.archetype == archetype and not without & set(c.capabilities)
        ),
        key=lambda c: (len(c.capabilities) + len(c.platforms), c),
    )


def _probe_request() -> tuple[dict[str, Any], dict[str, Composition]]:
    """Per archetype: the smallest, smallest+github and the largest accepted
    composition, plus four update transitions between them."""
    chosen: dict[str, Composition] = {}
    transitions: dict[str, list[str]] = {}
    for archetype in _archetypes():
        small = _smallest(archetype)
        hosted = Composition(archetype, small.capabilities, ("github",))
        large = _largest(archetype)
        for composition in (small, hosted, large):
            chosen[composition.slug] = composition
        transitions[f"{archetype}:no-op"] = [small.slug, small.slug]
        transitions[f"{archetype}:grow"] = [small.slug, large.slug]
        transitions[f"{archetype}:shrink"] = [large.slug, small.slug]
        transitions[f"{archetype}:host"] = [small.slug, hosted.slug]
    request = {
        "payloads": {slug: sweep_payload(c) for slug, c in chosen.items()},
        "transitions": transitions,
    }
    return request, chosen


# --- installations -------------------------------------------------------------


@pytest.fixture(scope="module")
def candidate_artefacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    out = tmp_path_factory.mktemp("candidate-dist")
    built = run(["uv", "build", "--out-dir", str(out)], REPO_ROOT)
    assert_success(built, context="uv build (candidate wheel and sdist)")
    wheels = sorted(out.glob("forge_template-*.whl"))
    sdists = sorted(out.glob("forge_template-*.tar.gz"))
    assert len(wheels) == 1 and len(sdists) == 1, (wheels, sdists)
    return {"wheel": wheels[0], "sdist": sdists[0]}


@pytest.fixture(scope="module")
def published_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dest = tmp_path_factory.mktemp("published-dist")
    return download_verified_artefact(
        PUBLISHED_WHEEL, dest, version=PUBLISHED_VERSION
    ).path


def _install(root: Path, label: str, *requirements: str) -> Installation:
    venv = root / label
    python = make_venv(venv)
    installed = run(
        ["uv", "pip", "install", "--python", str(python), *requirements], REPO_ROOT
    )
    assert_success(installed, context=f"install {label}: {requirements}")
    return Installation(label=label, venv=venv, python=python)


@pytest.fixture(scope="module")
def installations(
    tmp_path_factory: pytest.TempPathFactory,
    candidate_artefacts: dict[str, Path],
    published_wheel: Path,
) -> dict[str, Installation]:
    root = tmp_path_factory.mktemp("engine-installations")
    return {
        "candidate-wheel": _install(
            root, "candidate-wheel", str(candidate_artefacts["wheel"])
        ),
        # Installing the sdist builds a wheel from it: the path a
        # downstream packager (or a platform with no usable wheel) takes.
        "candidate-sdist": _install(
            root, "candidate-sdist", str(candidate_artefacts["sdist"])
        ),
        "published": _install(root, "published", str(published_wheel)),
    }


# --- 1. artefacts --------------------------------------------------------------

_CONTENTS_PROBE = """
import importlib.util, json, sys
from importlib import resources
import forge_template
root = resources.files("forge_template")
print(json.dumps({
    "file": forge_template.__file__,
    "private": {m: importlib.util.find_spec("forge_template." + m) is not None
                for m in sys.argv[1].split(",")},
    "check_only": {m: importlib.util.find_spec("forge_template." + m) is not None
                   for m in sys.argv[2].split(",")},
    "foundation": root.joinpath("foundation", "foundation.toml").is_file(),
    "py_typed": root.joinpath("py.typed").is_file(),
    "manifests": sorted(
        p.name for p in root.joinpath("components").iterdir()
        if p.joinpath("component.toml").is_file()
    ),
}))
"""


@pytest.mark.parametrize("label", ["candidate-wheel", "candidate-sdist"])
def test_candidate_installs_ship_the_facade_and_exclude_check_only_modules(
    label: str, installations: dict[str, Installation], tmp_path: Path
) -> None:
    installation = installations[label]
    result = run(
        [
            str(installation.python),
            "-c",
            _CONTENTS_PROBE,
            ",".join(_PRIVATE_MODULES),
            ",".join(_CHECK_ONLY_MODULES),
        ],
        tmp_path,
    )
    assert_success(result, context=f"{label} contents probe")
    contents = json.loads(result.stdout)
    assert str(installation.venv) in contents["file"], contents["file"]
    assert all(contents["private"].values()), contents["private"]
    assert not any(contents["check_only"].values()), contents["check_only"]
    assert contents["foundation"] and contents["py_typed"]
    assert contents["manifests"] == sorted(
        {c.archetype for c in valid_compositions()}
        | {cap for c in valid_compositions() for cap in c.capabilities}
        | {p for c in valid_compositions() for p in c.platforms}
    )


# --- 2. the minimal independent client ------------------------------------------


def _observe(installation: Installation, request: dict[str, Any], cwd: Path) -> Any:
    """Run the probe as a standalone script in ``installation``'s interpreter,
    from a directory holding nothing but the script and its request."""
    cwd.mkdir()
    script = cwd / "probe.py"
    shutil.copyfile(PROBE, script)
    request_path = cwd / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    driver = (
        "import sys, runpy; "
        f"sys.stdin = open({str(request_path)!r}, encoding='utf-8'); "
        f"runpy.run_path({str(script)!r}, run_name='__main__')"
    )
    observed = run([str(installation.python), "-c", driver], cwd)
    assert_success(observed, context=f"independent client on {installation.label}")
    return json.loads(observed.stdout)


def test_independent_client_observes_identical_behaviour(
    installations: dict[str, Installation], tmp_path: Path
) -> None:
    request, chosen = _probe_request()
    observations = {
        label: _observe(installation, request, tmp_path / label)
        for label, installation in installations.items()
    }

    published = observations["published"]
    for label in ("candidate-wheel", "candidate-sdist"):
        candidate = observations[label]
        # Which private modules happen to be loaded is the one thing the
        # decomposition changes, and it is not client-observable behaviour.
        for key in sorted(set(published) | set(candidate)):
            if key == "modules":
                continue
            assert candidate[key] == published[key], f"{label}: {key} differs"
        loaded = set(candidate["modules"])
        assert not loaded & {f"forge_template.{m}" for m in _CHECK_ONLY_MODULES}

    recorded = load_fingerprints()
    assert published["compositions"] == {slug: recorded[slug] for slug in chosen}
    assert published["engine_info"]["package_version"] == PUBLISHED_VERSION
    assert all(
        entry["code"] != "did-not-raise" for entry in published["failures"].values()
    )


# --- 3. the supported released client -------------------------------------------


def _client_compositions() -> tuple[Composition, ...]:
    # The largest library cell drops `pre-commit`: its hook installation
    # fetches hook repositories, which is not what this pairing compares.
    return (
        *(_smallest(archetype) for archetype in _archetypes()),
        _largest("library", without=frozenset({"pre-commit"})),
    )


def _generate(installation: Installation, composition: Composition, dest: Path) -> None:
    scripts = venv_python(installation.venv).parent
    env = child_env(dest.parent / ".config", extra_path=scripts)
    args: list[str] = [
        str(venv_console_script(installation.venv, "create-forge")),
        "new",
        "Engine Pairing Fixture",
        "--archetype",
        composition.archetype,
        "--yes",
        "--path",
        str(dest),
    ]
    for key, value in _ANSWERS.items():
        args += ["--data", f"{key}={value}"]
    for capability in composition.capabilities:
        args += ["--capability", capability]
    if not composition.capabilities:
        args.append("--no-capabilities")
    for platform in composition.platforms:
        args += ["--platform", platform]
    if not composition.platforms:
        args.append("--no-platforms")
    if "github" in composition.platforms:
        args += ["--component-option", "github.organisation=pairing-org"]
    if "coverage" in composition.capabilities:
        args += ["--component-option", "coverage.fail_under=80"]
    result = run(args, dest.parent, env=env)
    assert_success(
        result, context=f"{installation.label}: create-forge new {composition.slug}"
    )


def _tree(root: Path) -> dict[str, bytes]:
    ignored = {".git", ".venv"}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not ignored & set(path.relative_to(root).parts)
    }


@pytest.fixture(scope="module")
def released_clients(
    tmp_path_factory: pytest.TempPathFactory, candidate_artefacts: dict[str, Path]
) -> dict[str, Installation]:
    root = tmp_path_factory.mktemp("released-clients")
    published = _install(root, "client-published", RELEASED_CLIENT)
    candidate = _install(root, "client-candidate", RELEASED_CLIENT)
    swapped = run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(candidate.python),
            "--reinstall-package",
            "forge-template",
            str(candidate_artefacts["wheel"]),
        ],
        REPO_ROOT,
    )
    assert_success(swapped, context="replace forge-template with the candidate wheel")
    return {"published": published, "candidate": candidate}


def _engine_origin(installation: Installation, cwd: Path) -> str:
    result = run(
        [
            str(installation.python),
            "-c",
            "import forge_template, importlib.util as u; "
            "print(u.find_spec('forge_template._discovery') is not None)",
        ],
        cwd,
    )
    assert_success(result, context=f"{installation.label}: engine origin")
    return result.stdout.strip()


def test_released_client_generates_identically_on_the_candidate(
    released_clients: dict[str, Installation], tmp_path: Path
) -> None:
    assert _engine_origin(released_clients["published"], tmp_path) == "False"
    assert _engine_origin(released_clients["candidate"], tmp_path) == "True"

    for composition in _client_compositions():
        trees = {}
        for label, installation in released_clients.items():
            parent = tmp_path / label / composition.slug
            parent.mkdir(parents=True)
            dest = parent / "project"
            _generate(installation, composition, dest)
            trees[label] = _tree(dest)
        assert trees["candidate"].keys() == trees["published"].keys(), composition.slug
        differing = sorted(
            target
            for target in trees["published"]
            if trees["candidate"][target] != trees["published"][target]
        )
        assert differing == [], f"{composition.slug}: {differing}"
        assert ".forge/generation.json" in trees["candidate"]


def test_released_client_doctor_accepts_the_candidate(
    released_clients: dict[str, Installation], tmp_path: Path
) -> None:
    installation = released_clients["candidate"]
    env = child_env(
        tmp_path / ".config", extra_path=venv_python(installation.venv).parent
    )
    result = run(
        [
            str(venv_console_script(installation.venv, "create-forge")),
            "doctor",
            "--json",
        ],
        tmp_path,
        env=env,
    )
    assert_success(result, context="create-forge doctor --json on the candidate")
    report = json.loads(result.stdout)
    integration = report["integration"]
    assert report["ok"] is True
    assert integration["engine_package"] == PUBLISHED_VERSION
    assert integration["projectspec_protocol"]["detected"] == "1"
    assert integration["component_manifest_protocol"]["detected"] == "1,2,3"
    assert integration["metadata_version"]["detected"] == 1
    checks = {check["name"]: check["ok"] for check in report["checks"]}
    assert checks["engine"] is True
    assert checks["engine negotiation"] is True
