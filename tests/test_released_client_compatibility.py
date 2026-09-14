"""Row 338 of the acceptance matrix (FT-18.01):
`docs/cutover-compatibility-and-acceptance.md#regression` -- a `create-forge`
still pinned to `forge-template>=0.4.1,<0.5` continues to resolve, install
and generate after `0.5.0` publishes.

``cutover``-marked (``uv run poe cutover``, or narrowly
``uv run pytest -m cutover tests/test_released_client_compatibility.py``).
Hermetic: every fixture here resolves from the public PyPI index by exact
pinned version, never a sibling checkout, which is what makes this module --
unlike ``tests/test_released_provider_cutover.py`` -- eligible for the
``released-client`` CI job (see ``.github/workflows/test-template.yml`` and
docs/adr/0067-validate-the-integrated-engine-default-cutover.md decision 4).

The last `create-forge` release still on the `0.4.1`-`0.5` engine line is
`0.3.2`. Its engine dependency is declared behind the ``engine`` extra
(`forge-template<0.5,>=0.4.1; extra == "engine"`, confirmed against PyPI's own
metadata during FT-18.01 planning) -- so the resolution proof here installs
``create-forge[engine]==0.3.2``, not a bare ``create-forge==0.3.2``, which
would resolve no engine at all and prove nothing. ``0.3.2`` still carries the
now-removed ``--engine-preview`` flag; this module targets that exact
release, not the current client CLI.

See docs/integrated-cutover-validation.md and
docs/cutover-provider-release.md#what-this-does-not-prove, which names this
proof as the open item FT-17.06 handed to FT-18.01.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from forge_template.schema import REPO_ROOT
from tests.released_provider import (
    ENGINE_VERSION,
    assert_success,
    child_env,
    make_venv,
    run,
    venv_console_script,
    venv_python,
)

pytestmark = pytest.mark.cutover

# The last create-forge release still declaring forge-template>=0.4.1,<0.5.
# Verified against PyPI's requires_dist during FT-18.01 planning.
_RELEASED_CLIENT_VERSION = "0.3.2"
_RELEASED_CLIENT_ENGINE_RANGE = SpecifierSet(">=0.4.1,<0.5")

_ANSWERS = {
    "project_description": "FT-18.01 released-client pin-back regression.",
    "license": "mit",
    "author_name": "Released Client Compatibility",
    "author_email": "released-client-compat@example.invalid",
}

_ENGINE_VERSION_PROBE = (
    "import importlib.metadata, json; "
    "print(json.dumps({"
    "'forge_template': importlib.metadata.version('forge-template'), "
    "}))"
)


def _pypi_index_has_release(package: str, version: str) -> bool:
    """True if `package==version` is a real, currently-listed PyPI release.

    Asserted rather than assumed for `forge-template==0.5.0`: without this,
    a resolution test could pass vacuously if 0.5.0 were somehow unlisted.
    """
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload: dict[str, object] = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.skip(f"PyPI unreachable: {exc}")
    info = payload.get("info")
    assert isinstance(info, dict), f"malformed PyPI response for {package}=={version}"
    return bool(info.get("version") == version)


def test_the_released_engine_line_is_published_before_asserting_pin_back() -> None:
    """Premise check: `forge-template 0.5.0` really is on the index. Without
    this, `test_the_released_client_resolves_the_0_4_1_line_after_0_5_0_publishes`
    could pass whether or not 0.5.0 had actually shipped.
    """
    assert _pypi_index_has_release("forge-template", ENGINE_VERSION), (
        f"forge-template=={ENGINE_VERSION} is not the current PyPI release -- "
        "this test's premise (0.5.0 has published) no longer holds"
    )


@pytest.fixture(scope="module")
def released_client_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One isolated venv with `create-forge[engine]==0.3.2` installed from
    the public index -- the pinned, previously reviewed release, not this
    working tree.
    """
    venv = tmp_path_factory.mktemp("released-client") / ".venv"
    python = make_venv(venv)
    install = run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            f"create-forge[engine]=={_RELEASED_CLIENT_VERSION}",
        ],
        REPO_ROOT,
    )
    assert_success(
        install, context=f"install create-forge[engine]=={_RELEASED_CLIENT_VERSION}"
    )
    return venv


def test_the_released_client_resolves_the_0_4_1_line_after_0_5_0_publishes(
    released_client_venv: Path,
) -> None:
    python = venv_python(released_client_venv)
    probe = run([str(python), "-c", _ENGINE_VERSION_PROBE], REPO_ROOT)
    assert_success(probe, context="engine-version probe in the released-client venv")
    resolved = json.loads(probe.stdout)["forge_template"]

    assert Version(resolved) in _RELEASED_CLIENT_ENGINE_RANGE, (
        f"create-forge[engine]=={_RELEASED_CLIENT_VERSION} resolved "
        f"forge-template=={resolved}, outside its declared "
        f"{_RELEASED_CLIENT_ENGINE_RANGE}"
    )
    assert resolved != ENGINE_VERSION, (
        f"create-forge[engine]=={_RELEASED_CLIENT_VERSION} resolved the "
        f"just-published forge-template=={ENGINE_VERSION} -- its own pin "
        "should have kept it on the 0.4.x line"
    )

    script = venv_console_script(released_client_venv, "create-forge")
    version_check = run([str(script), "--version"], REPO_ROOT)
    assert_success(version_check, context="create-forge --version")
    assert _RELEASED_CLIENT_VERSION in version_check.stdout


def test_the_released_client_still_generates_against_the_0_4_1_line(
    released_client_venv: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """0.3.2's `new` command, run for real, with no engine change on either
    side of the pin. This is the pre-cutover client shape: no `.git`, no
    `.forge` (both are CF-18.03/CF-18.01 additions this release predates).
    """
    config_home = tmp_path_factory.mktemp("released-client-config")
    dest = tmp_path_factory.mktemp("released-client-generated") / "pinned-library"
    script = venv_console_script(released_client_venv, "create-forge")

    args = [
        str(script),
        "new",
        "Pinned Client Library",
        "--engine-preview",
        "--archetype",
        "library",
        "--no-capabilities",
        "--yes",
        "--path",
        str(dest),
    ]
    for key, value in _ANSWERS.items():
        args += ["--data", f"{key}={value}"]

    result = run(args, dest.parent, env=child_env(config_home))
    assert_success(result, context="create-forge new --engine-preview (0.3.2)")

    assert dest.is_dir()
    assert (dest / "pyproject.toml").is_file()
    packages = [p for p in (dest / "src").iterdir() if p.is_dir()]
    assert len(packages) == 1, packages
    package = packages[0]
    assert (package / "__init__.py").is_file()
    assert (package / "py.typed").is_file()
    assert (dest / "tests").is_dir()
    assert (dest / "uv.lock").is_file()
    assert not (dest / ".git").exists()
    assert not (dest / ".forge").exists()
    assert not (dest / ".venv").exists()
    assert list(dest.parent.glob(".create-forge-*")) == []

    lock_check = run(["uv", "lock", "--check"], dest, env=child_env(config_home))
    assert_success(lock_check, context="uv lock --check")

    pyproject_text = (dest / "pyproject.toml").read_text(encoding="utf-8")
    lock_text = (dest / "uv.lock").read_text(encoding="utf-8")
    for forbidden in ("forge-template", "create-forge"):
        assert forbidden not in pyproject_text
        assert forbidden not in lock_text


def test_a_plain_install_of_the_released_client_is_unaffected(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The gate's "plain installs unaffected" clause
    (docs/cutover-compatibility-and-acceptance.md#cross-repository-release-gates):
    a bare `create-forge==0.3.2`, with no `engine` extra, still installs and
    runs -- publishing `0.5.0` changes nothing for a client that never opted
    into the engine at all.
    """
    venv = tmp_path_factory.mktemp("released-client-plain") / ".venv"
    python = make_venv(venv)
    install = run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            f"create-forge=={_RELEASED_CLIENT_VERSION}",
        ],
        REPO_ROOT,
    )
    assert_success(install, context=f"install create-forge=={_RELEASED_CLIENT_VERSION}")

    # A plain install carries no `forge-template` at all -- confirmed by
    # asking the *venv's* metadata, not this process's own environment.
    probe = run(
        [
            str(python),
            "-c",
            "import importlib.metadata as m; print(m.version('forge-template'))",
        ],
        REPO_ROOT,
    )
    assert probe.returncode != 0, (
        f"a plain create-forge=={_RELEASED_CLIENT_VERSION} install resolved "
        f"forge-template=={probe.stdout.strip()} -- it should have resolved none"
    )

    script = venv_console_script(venv, "create-forge")
    version_check = run([str(script), "--version"], REPO_ROOT)
    assert_success(version_check, context="create-forge --version (plain install)")
    assert _RELEASED_CLIENT_VERSION in version_check.stdout

    doctor = run([str(script), "doctor", "--json"], REPO_ROOT)
    assert_success(doctor, context="create-forge doctor --json (plain install)")
    payload = json.loads(doctor.stdout)
    assert isinstance(payload, dict)
