"""Row 339 of the acceptance matrix (FT-18.01):
`docs/cutover-compatibility-and-acceptance.md#regression` -- the integrated
cutover. The immutable released `forge-template` `0.5.0` (downloaded from
PyPI and digest-verified, never this working tree) paired with the
candidate `create-forge` `0.4.0` client (built from the sibling working
tree, since it is not yet published -- CF-18.07 left that gated on this
issue) must pass the cross-repository acceptance matrix together.

``cutover``-marked (``uv run poe cutover``, or narrowly
``uv run pytest -m cutover tests/test_released_provider_cutover.py``).
Sibling-gated like ``tests/test_cross_repository_validation.py`` -- the
whole module skips when no ``create-forge`` checkout is found -- and for the
same reason stays out of CI (ADR 0057; row 338's suite is the hermetic half
that does run in CI, see ``tests/test_released_client_compatibility.py``).

Scope, per docs/adr/0067-validate-the-integrated-engine-default-cutover.md
decision 1: every matrix row observable through the `create-forge` boundary
is re-executed here against the *installed released* engine, and the
provider-side Engine/Generated-project rows are re-proven against that same
released wheel rather than the working tree. The exhaustive 2240-composition
sweep and all three FT-17.05 full-composition build cells are cited, not
repeated -- see "Cited, not re-executed" in
docs/integrated-cutover-validation.md.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import forge_template as ft
from forge_template.schema import REPO_ROOT
from tests.released_provider import (
    CLIENT_ENGINE_RANGE,
    CLIENT_VERSION,
    WHEEL,
    VerifiedDownload,
    assert_success,
    child_env,
    direct_url,
    download_verified_artefact,
    is_windows_venv,
    make_venv,
    run,
    site_packages,
    venv_console_script,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

pytestmark = pytest.mark.cutover

_ANSWERS: Mapping[str, str] = {
    "project_description": "FT-18.01 integrated cutover fixture.",
    "license": "mit",
    "author_name": "Integrated Cutover",
    "author_email": "integrated-cutover@example.invalid",
}

# Six compositions chosen to cover catalogue edges the historical
# ten-composition crossrepo set does not reach, while staying inside the
# runtime budget (ADR 0067 decision 1): the bare floor, one maximal
# every-compatible-capability cell (also the one `poe check` cell),
# `renovate` (never built through a client before), a full `cli` cell,
# and both Data Science edges.
_COMPOSITIONS: tuple[tuple[str, tuple[str, ...], tuple[str, ...], str], ...] = (
    ("library", (), (), "library-minimal"),
    (
        "library",
        (
            "changelog",
            "coverage",
            "dependabot",
            "documentation",
            "dotenv-example",
            "jupyter",
            "pre-commit",
            "pyright",
            "scientific-python",
        ),
        ("github",),
        "library-github-max",
    ),
    ("library", ("changelog", "dotenv-example", "renovate"), (), "library-renovate"),
    (
        "cli",
        (
            "changelog",
            "coverage",
            "dotenv-example",
            "jupyter",
            "pre-commit",
            "pyright",
            "scientific-python",
        ),
        ("github",),
        "cli-full",
    ),
    ("data-science", ("jupyter",), (), "data-science-min"),
    (
        "data-science",
        ("jupyter", "scientific-python", "coverage", "pyright", "pre-commit"),
        ("github",),
        "data-science-rich",
    ),
)
_DETERMINISM_SLUGS = ("library-minimal", "data-science-rich")
_MAXIMAL_SLUG = "library-github-max"


@dataclass(frozen=True, slots=True)
class CandidateClient:
    """The candidate create-forge wheel, built from the sibling tree, and
    the exact commit it was built from -- recorded, never pinned, so a later
    CF-18.07 commit does not red this suite (docs/integrated-cutover-validation.md).
    """

    wheel: Path
    commit: str


@dataclass(frozen=True, slots=True)
class ReleasedPair:
    """One isolated venv holding the digest-verified released provider and
    the candidate client, both installed from file -- never an index.
    """

    venv: Path
    python: Path
    create_forge_script: Path


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    dest: Path
    archetype: str
    capabilities: tuple[str, ...]
    platforms: tuple[str, ...]


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def released_wheel(tmp_path_factory: pytest.TempPathFactory) -> VerifiedDownload:
    dest_dir = tmp_path_factory.mktemp("released-wheel")
    return download_verified_artefact(WHEEL, dest_dir)


@pytest.fixture(scope="session")
def candidate_client(
    tmp_path_factory: pytest.TempPathFactory, create_forge_root: Path
) -> CandidateClient:
    """Build the candidate `create-forge` wheel from the sibling working
    tree, asserting the two facts the acceptance matrix fixes for this
    issue (candidate version, engine range) and that the build left the
    checkout byte-for-byte unmodified -- ADR 0066 decision 3's
    no-sibling-edit constraint, made executable rather than only promised.
    """
    pyproject_text = (create_forge_root / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{CLIENT_VERSION}"' in pyproject_text, (
        f"sibling create-forge is not version {CLIENT_VERSION}; this suite's "
        "recorded candidate identity is stale -- re-check "
        "tests/released_provider.py's CLIENT_VERSION"
    )
    assert f'"forge-template{CLIENT_ENGINE_RANGE}"' in pyproject_text, (
        f"sibling create-forge does not declare forge-template{CLIENT_ENGINE_RANGE}"
    )

    before = run(["git", "status", "--porcelain"], create_forge_root)
    assert_success(before, context="git status --porcelain (before candidate build)")
    head = run(["git", "rev-parse", "HEAD"], create_forge_root)
    assert_success(head, context="git rev-parse HEAD (candidate client)")
    commit = head.stdout.strip()

    out_dir = tmp_path_factory.mktemp("candidate-client-wheel")
    build = run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)], create_forge_root
    )
    assert_success(build, context="uv build --wheel (candidate client)")

    after = run(["git", "status", "--porcelain"], create_forge_root)
    assert_success(after, context="git status --porcelain (after candidate build)")
    assert before.stdout == after.stdout, (
        "building the candidate client wheel modified the sibling checkout "
        "(ADR 0066 decision 3's no-sibling-edit constraint):\n"
        f"before:\n{before.stdout}\nafter:\n{after.stdout}"
    )

    wheels = sorted(out_dir.glob("create_forge-*.whl"))
    assert len(wheels) == 1, wheels
    return CandidateClient(wheel=wheels[0], commit=commit)


@pytest.fixture(scope="session")
def released_pair(
    tmp_path_factory: pytest.TempPathFactory,
    released_wheel: VerifiedDownload,
    candidate_client: CandidateClient,
) -> ReleasedPair:
    """One venv with the verified released provider and the built candidate
    client installed as file paths -- so no index copy of either can
    substitute for the bytes this suite already verified or built.
    """
    venv = tmp_path_factory.mktemp("released-pair") / ".venv"
    python = make_venv(venv)
    install = run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            str(released_wheel.path),
            str(candidate_client.wheel),
            "uv",
        ],
        REPO_ROOT,
    )
    assert_success(install, context="install released provider + candidate client")
    return ReleasedPair(
        venv=venv,
        python=python,
        create_forge_script=venv_console_script(venv, "create-forge"),
    )


@pytest.fixture(scope="session")
def pair_env(
    tmp_path_factory: pytest.TempPathFactory, released_pair: ReleasedPair
) -> dict[str, str]:
    config_home = tmp_path_factory.mktemp("cutover-config")
    scripts_dir = (
        released_pair.venv / "Scripts"
        if is_windows_venv(released_pair.venv)
        else released_pair.venv / "bin"
    )
    return child_env(config_home, extra_path=scripts_dir)


def _generate(
    pair: ReleasedPair,
    env_: Mapping[str, str],
    *,
    project_name: str,
    archetype: str,
    capabilities: Sequence[str],
    platforms: Sequence[str],
    dest: Path,
    extra_args: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    args: list[str] = [
        str(pair.create_forge_script),
        "new",
        project_name,
        "--archetype",
        archetype,
        "--yes",
        "--path",
        str(dest),
    ]
    for key, value in _ANSWERS.items():
        args += ["--data", f"{key}={value}"]
    for capability in capabilities:
        args += ["--capability", capability]
    if not capabilities:
        args.append("--no-capabilities")
    for platform in platforms:
        args += ["--platform", platform]
    if not platforms:
        args.append("--no-platforms")
    if "github" in platforms:
        # The `github` platform's one required option (docs/platform-and-
        # tooling-parity.md).
        args += ["--component-option", "github.organisation=cutover-fixture-org"]
    args += list(extra_args)
    return run(args, dest.parent, env=env_)


def _assert_project_shape(dest: Path, *, capabilities: Sequence[str] = ()) -> None:
    assert dest.is_dir()
    assert (dest / "pyproject.toml").is_file()
    packages = [p for p in (dest / "src").iterdir() if p.is_dir()]
    assert len(packages) == 1, packages
    package = packages[0]
    assert (package / "__init__.py").is_file()
    assert (package / "py.typed").is_file()
    assert (dest / "tests").is_dir()
    assert (dest / "uv.lock").is_file()
    assert (dest / ".git").is_dir()
    assert (dest / ".forge" / "generation.json").is_file()
    # `.venv` exists exactly when `pre-commit` was selected: CF-18.03's
    # post-rename lifecycle runs `uv run --directory <dst> pre-commit
    # install --install-hooks` only when a rendered `.pre-commit-config.yaml`
    # is present, and `uv run` implicitly creates the venv it needs.
    if "pre-commit" in capabilities:
        assert (dest / ".venv").is_dir()
    else:
        assert not (dest / ".venv").exists()
    assert list(dest.parent.glob(".create-forge-*")) == []


@pytest.fixture(scope="session")
def generated_projects(
    tmp_path_factory: pytest.TempPathFactory,
    released_pair: ReleasedPair,
    pair_env: Mapping[str, str],
) -> dict[str, GeneratedProject]:
    root = tmp_path_factory.mktemp("cutover-generated")
    projects: dict[str, GeneratedProject] = {}
    for archetype, capabilities, platforms, slug in _COMPOSITIONS:
        dest = root / slug
        result = _generate(
            released_pair,
            pair_env,
            project_name=f"Cutover {slug}",
            archetype=archetype,
            capabilities=capabilities,
            platforms=platforms,
            dest=dest,
        )
        assert_success(
            result,
            context=(
                f"create-forge new --archetype {archetype} "
                f"(capabilities={capabilities}, platforms={platforms})"
            ),
        )
        projects[slug] = GeneratedProject(
            dest=dest,
            archetype=archetype,
            capabilities=capabilities,
            platforms=platforms,
        )
    return projects


# --------------------------------------------------------------------------
# artefact identity and pairing
# --------------------------------------------------------------------------


def test_the_published_artefacts_match_their_recorded_identities(
    released_wheel: VerifiedDownload,
) -> None:
    """`download_verified_artefact` already asserted this on every call --
    this test exists so the assertion has a named node in the report, per
    row 339's "immutable released provider" premise and re-confirming
    docs/cutover-compatibility-and-acceptance.md's Publication row.
    """
    assert released_wheel.identity == WHEEL
    assert released_wheel.path.is_file()
    assert released_wheel.path.name == WHEEL.filename


def test_the_pair_installs_the_verified_wheel_and_the_candidate_client(
    released_pair: ReleasedPair,
) -> None:
    """Executable acceptance criterion 4's counterpart for the released pair:
    the provider's `direct_url.json` names the verified download, the
    client's names the built candidate -- both `file://`, never an index --
    and each reports the exact version this issue targets.
    """
    packages = site_packages(released_pair.python, cwd=REPO_ROOT)
    provider_url = direct_url(packages, "forge_template-*.dist-info")
    client_url = direct_url(packages, "create_forge-*.dist-info")

    assert str(provider_url["url"]).startswith("file://"), provider_url
    assert str(client_url["url"]).startswith("file://"), client_url

    version_probe = run(
        [
            str(released_pair.python),
            "-c",
            "import importlib.metadata as m, json; "
            "print(json.dumps({"
            "'forge_template': m.version('forge-template'), "
            "'create_forge': m.version('create-forge')}))",
        ],
        REPO_ROOT,
    )
    assert_success(version_probe, context="installed-version probe")
    versions = json.loads(version_probe.stdout)
    assert versions["forge_template"] == WHEEL.filename.split("-")[1]
    assert versions["create_forge"] == CLIENT_VERSION


_ENGINE_PROBE = """
import json
import forge_template as ft

components = sorted(ft.discover_components(), key=lambda d: d.id)
info = ft.get_engine_info()
payload = {
    "package_version": info.package_version,
    "projectspec_protocols": list(info.projectspec_protocols),
    "component_manifest_protocols": list(info.component_manifest_protocols),
    "metadata_version": info.metadata_version,
    "component_ids": [d.id for d in components],
    "error_codes": sorted(code.value for code in ft.EngineErrorCode),
    "descriptor_json": [d.model_dump_json() for d in components],
}
print(json.dumps(payload))
"""


@pytest.fixture(scope="session")
def released_engine_facts(released_pair: ReleasedPair) -> dict[str, object]:
    result = run([str(released_pair.python), "-c", _ENGINE_PROBE], REPO_ROOT)
    assert_success(result, context="engine-facts probe against the released wheel")
    payload: dict[str, object] = json.loads(result.stdout)
    return payload


def test_the_installed_release_publishes_the_negotiation_facts(
    released_engine_facts: dict[str, object],
) -> None:
    assert released_engine_facts["package_version"] == WHEEL.filename.split("-")[1]
    assert released_engine_facts["projectspec_protocols"] == [1]
    assert released_engine_facts["component_manifest_protocols"] == [1, 2, 3]
    assert released_engine_facts["metadata_version"] == 1


def test_the_installed_release_discovers_the_fourteen_component_catalogue(
    released_engine_facts: dict[str, object],
) -> None:
    assert released_engine_facts["component_ids"] == [
        "changelog",
        "cli",
        "coverage",
        "data-science",
        "dependabot",
        "documentation",
        "dotenv-example",
        "github",
        "jupyter",
        "library",
        "pre-commit",
        "pyright",
        "renovate",
        "scientific-python",
    ]


_PATH_LEAK_TOKENS = (
    "content_root",
    "options_schema",
    "extensions/",
    "content/",
    "component.toml",
    "src/forge_template",
    "\\\\",
    "//",
)


def test_the_installed_release_descriptors_carry_no_filesystem_path(
    released_engine_facts: dict[str, object],
) -> None:
    descriptors = released_engine_facts["descriptor_json"]
    assert isinstance(descriptors, list) and descriptors
    for raw in descriptors:
        assert isinstance(raw, str)
        for token in _PATH_LEAK_TOKENS:
            assert token not in raw, (token, raw)


def test_the_installed_release_ships_the_two_generation_metadata_codes(
    released_engine_facts: dict[str, object],
) -> None:
    codes = released_engine_facts["error_codes"]
    assert isinstance(codes, list)
    assert "invalid-generation-metadata" in codes
    assert "unsupported-generation-metadata" in codes


def test_the_released_wheel_imports_and_renders_in_isolation(
    released_wheel: VerifiedDownload,
) -> None:
    """`uv run --isolated --no-project --with <wheel>` resolves only the
    wheel's own declared dependencies -- the isolated-import smoke check
    `scripts/check_wheel.py` runs for a locally built artefact, run here
    against the *downloaded, verified* one, and strengthened: the isolated
    `__all__` must equal this process's own (the working tree at the `0.5.0`
    tag), so the released bytes are proven to export exactly what was
    reviewed -- no 43-name literal duplicated from `tests/test_cutover_gates.py`.
    """
    probe = (
        "import forge_template as ft; import json; "
        "info = ft.get_engine_info(); "
        "assert info.package_version and info.metadata_version; "
        "descriptors = ft.discover_components(); "
        "assert len(descriptors) == 14; "
        "print(json.dumps(sorted(ft.__all__)))"
    )
    result = run(
        [
            "uv",
            "run",
            "--isolated",
            "--no-project",
            "--with",
            str(released_wheel.path),
            "python",
            "-c",
            probe,
        ],
        REPO_ROOT,
    )
    assert_success(result, context="isolated import of the verified released wheel")
    isolated_all = json.loads(result.stdout)
    assert isolated_all == sorted(ft.__all__)


# --------------------------------------------------------------------------
# generated projects
# --------------------------------------------------------------------------


@pytest.mark.parametrize("slug", [composition[3] for composition in _COMPOSITIONS])
def test_every_boundary_composition_generates_through_the_released_pair(
    generated_projects: dict[str, GeneratedProject],
    pair_env: Mapping[str, str],
    slug: str,
) -> None:
    project = generated_projects[slug]
    _assert_project_shape(project.dest, capabilities=project.capabilities)

    lock_check = run(["uv", "lock", "--check"], project.dest, env=pair_env)
    assert_success(lock_check, context=f"uv lock --check ({slug})")

    pyproject_text = (project.dest / "pyproject.toml").read_text(encoding="utf-8")
    lock_text = (project.dest / "uv.lock").read_text(encoding="utf-8")
    for forbidden in ("forge-template", "create-forge"):
        assert forbidden not in pyproject_text
        assert forbidden not in lock_text

    if project.archetype == "data-science":
        assert (project.dest / "notebooks" / "getting-started.ipynb").is_file()


_OWNERSHIP_PROBE_TEMPLATE = """
import json
import forge_template as ft

with open({spec_path!r}, encoding="utf-8") as handle:
    spec = ft.parse_project_spec(json.load(handle))
plan = ft.plan_generation(spec)
selected = set(plan.component_order)
owners = set()
for file in plan.files:
    if file.owner.kind == "foundation":
        owners.add("foundation")
    else:
        owners.add(file.owner.id)
missing = selected - owners
print(json.dumps({{
    "owners": sorted(owners),
    "selected": sorted(selected),
    "missing": sorted(missing),
}}))
"""


@pytest.mark.parametrize("slug", [composition[3] for composition in _COMPOSITIONS])
def test_every_generated_target_has_an_explicit_owner(
    generated_projects: dict[str, GeneratedProject],
    released_pair: ReleasedPair,
    tmp_path: Path,
    slug: str,
) -> None:
    """Every selected component contributes at least one owned file -- run
    against the *recorded spec* of a real generation, through the released
    engine's own `plan_generation`, not a hand-built ProjectSpec.
    """
    project = generated_projects[slug]
    metadata = json.loads(
        (project.dest / ".forge" / "generation.json").read_text(encoding="utf-8")
    )
    spec_path = tmp_path / f"{slug}-spec.json"
    spec_path.write_text(json.dumps(metadata["spec"]), encoding="utf-8")

    probe = _OWNERSHIP_PROBE_TEMPLATE.format(spec_path=str(spec_path))
    result = run([str(released_pair.python), "-c", probe], REPO_ROOT)
    assert_success(result, context=f"ownership probe ({slug})")
    payload = json.loads(result.stdout)
    assert payload["missing"] == [], (
        f"{slug}: selected components with no owned file: {payload['missing']}"
    )


_REPRODUCE_PROBE_TEMPLATE = """
import json
import forge_template as ft

with open({metadata_path!r}, encoding="utf-8") as handle:
    raw = json.load(handle)
metadata = ft.parse_generation_metadata(raw)
spec = ft.parse_project_spec(metadata.spec)
project = ft.render_project(spec)
ft.verify_generation_metadata(metadata, project)
print("verified")
"""


@pytest.mark.parametrize("slug", [composition[3] for composition in _COMPOSITIONS])
def test_recorded_metadata_reproduces_the_generated_project_byte_for_byte(
    generated_projects: dict[str, GeneratedProject],
    released_pair: ReleasedPair,
    slug: str,
) -> None:
    """The provider's reproducibility guarantee
    (docs/generation-provenance.md), proven for the first time against a
    `.forge/generation.json` a *client* wrote (every prior proof re-renders
    a document the engine itself produced in-process)."""
    project = generated_projects[slug]
    metadata_path = project.dest / ".forge" / "generation.json"
    probe = _REPRODUCE_PROBE_TEMPLATE.format(metadata_path=str(metadata_path))
    result = run([str(released_pair.python), "-c", probe], REPO_ROOT)
    assert_success(result, context=f"reproduction probe ({slug})")
    assert result.stdout.strip() == "verified"


def test_the_client_classifies_update_targets_against_the_released_engine(
    generated_projects: dict[str, GeneratedProject],
    released_pair: ReleasedPair,
    pair_env: Mapping[str, str],
) -> None:
    """`create-forge update --dry-run` on a freshly generated project, still
    routed through the committed `.forge/generation.json` -- proving the
    client boundary form of `plan_update` writes nothing and reports a
    classification for every target."""
    project = generated_projects[_MAXIMAL_SLUG]
    result = run(
        [
            str(released_pair.create_forge_script),
            "update",
            str(project.dest),
            "--dry-run",
        ],
        project.dest,
        env=pair_env,
    )
    assert_success(result, context="create-forge update --dry-run")
    assert "unchanged target(s)." in result.stdout


@pytest.mark.parametrize("slug", _DETERMINISM_SLUGS)
def test_repeated_generation_is_byte_identical(
    generated_projects: dict[str, GeneratedProject],
    released_pair: ReleasedPair,
    pair_env: Mapping[str, str],
    tmp_path: Path,
    slug: str,
) -> None:
    """`uv.lock` (network-resolved) and `.git/**` (lifecycle bookkeeping) are
    excluded; so is `.venv/**` when `pre-commit` is selected -- CF-18.03's
    lifecycle creates it via `uv run --directory <dst> pre-commit install
    --install-hooks`, and its contents (e.g. `activate` scripts) embed
    venv-specific bytes, not rendered ones. `.forge/generation.json` stays
    *in* the comparison -- `GenerationMetadata` records no timestamp, so it
    is deterministic like every other rendered byte."""
    first = generated_projects[slug]
    archetype, capabilities, platforms, _ = next(
        c for c in _COMPOSITIONS if c[3] == slug
    )
    second_dest = tmp_path / slug
    result = _generate(
        released_pair,
        pair_env,
        project_name=f"Cutover {slug}",
        archetype=archetype,
        capabilities=capabilities,
        platforms=platforms,
        dest=second_dest,
    )
    assert_success(result, context=f"regenerate {slug}")

    def _rendered_files(root: Path) -> dict[str, Path]:
        return {
            path.relative_to(root).as_posix(): path
            for path in root.rglob("*")
            if path.is_file()
            and path.name != "uv.lock"
            and ".git" not in path.relative_to(root).parts
            and ".venv" not in path.relative_to(root).parts
        }

    first_files = _rendered_files(first.dest)
    second_files = _rendered_files(second_dest)
    assert set(first_files) == set(second_files)
    for relative, path in first_files.items():
        assert path.read_bytes() == second_files[relative].read_bytes(), relative


def _forge_free_probe(package_name: str, python: Path) -> None:
    result = run(
        [
            str(python),
            "-c",
            "import importlib.metadata as m; "
            "names = {d.metadata['Name'] for d in m.distributions()}; "
            "forbidden = {'forge-template', 'create-forge'} & names; "
            "assert not forbidden, forbidden",
        ],
        REPO_ROOT,
    )
    assert_success(result, context=f"Forge-freedom probe ({package_name})")


def test_the_maximal_composition_builds_installs_and_passes_its_own_check(
    generated_projects: dict[str, GeneratedProject],
    tmp_path_factory: pytest.TempPathFactory,
    pair_env: Mapping[str, str],
) -> None:
    """The one full build-and-check cell (ADR 0067 decision 1) -- the other
    two archetypes' full-composition builds are cited to FT-17.05's own
    three provider-side cells rather than repeated here."""
    project = generated_projects[_MAXIMAL_SLUG]
    dest = project.dest

    sync = run(["uv", "sync", "--all-groups", "--locked"], dest, env=pair_env)
    assert_success(sync, context="uv sync --all-groups --locked")

    build_dir = tmp_path_factory.mktemp("cutover-maximal-build")
    build = run(["uv", "build", "--out-dir", str(build_dir)], dest, env=pair_env)
    assert_success(build, context="uv build")
    wheels = sorted(build_dir.glob("*.whl"))
    assert len(wheels) == 1, wheels

    install_venv = tmp_path_factory.mktemp("cutover-maximal-install") / ".venv"
    install_python = make_venv(install_venv)
    install = run(
        ["uv", "pip", "install", "--python", str(install_python), str(wheels[0])],
        dest,
    )
    assert_success(install, context="install the generated project's own wheel")
    _forge_free_probe(wheels[0].name, install_python)

    lock_text = (dest / "uv.lock").read_text(encoding="utf-8")
    for forbidden in ("forge-template", "create-forge"):
        assert forbidden not in lock_text

    check = run(["uv", "run", "--locked", "poe", "check"], dest, env=pair_env)
    assert_success(check, context="poe check (generated project)")

    precommit_config = dest / ".pre-commit-config.yaml"
    if precommit_config.is_file():
        git_init = run(["git", "init"], dest, env=pair_env)
        assert_success(git_init, context="git init (pre-commit smoke)")
        add = run(["git", "add", "-A"], dest, env=pair_env)
        assert_success(add, context="git add -A (pre-commit smoke)")
        precommit = run(
            ["uv", "run", "pre-commit", "run", "--all-files"], dest, env=pair_env
        )
        assert_success(precommit, context="pre-commit run --all-files")


# --------------------------------------------------------------------------
# rejections
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RejectionCase:
    archetype: str
    capabilities: tuple[str, ...]
    platforms: tuple[str, ...]
    extra_args: tuple[str, ...]
    expect: tuple[str, ...]


_REJECTIONS = (
    pytest.param(
        RejectionCase(
            "data-science",
            (),
            (),
            ("--no-capabilities",),
            ("requires selected component(s): jupyter", "Add --capability jupyter."),
        ),
        id="data-science-explicit-no-capabilities",
    ),
    pytest.param(
        RejectionCase(
            "data-science", (), (), (), ("requires selected component(s): jupyter",)
        ),
        id="data-science-missing-capability-flag",
    ),
    pytest.param(
        RejectionCase("not-a-real-archetype", (), (), (), ("Unknown archetype",)),
        id="unknown-archetype",
    ),
    pytest.param(
        RejectionCase(
            "library",
            (),
            (),
            ("--no-capabilities", "--component-option", "not-a-real.option=value"),
            ("Unknown --component-option component",),
        ),
        id="unknown-component-option-owner",
    ),
    pytest.param(
        RejectionCase(
            "library",
            ("dependabot",),
            (),
            (),
            # No client-owned "Add --platform github." hint here: create-forge's
            # `_missing_requirement_hint` only covers the *archetype's own*
            # direct requirements (data-science -> jupyter, above) --
            # confirmed by running this case against the released pair --
            # never a capability's `requires` edge onto another component.
            ("requires selected component(s): github",),
        ),
        id="dependabot-without-github",
    ),
    pytest.param(
        RejectionCase(
            "library",
            ("dependabot", "renovate"),
            ("github",),
            (),
            ("conflicts with selected component(s):",),
        ),
        id="dependabot-renovate-conflict",
    ),
    pytest.param(
        RejectionCase(
            "cli",
            ("documentation",),
            (),
            (),
            ("requires selected component(s): library",),
        ),
        id="documentation-requires-library",
    ),
)


@pytest.mark.parametrize("case", _REJECTIONS)
def test_documented_rejections_leave_no_partial_destination(
    released_pair: ReleasedPair,
    pair_env: Mapping[str, str],
    tmp_path: Path,
    case: RejectionCase,
) -> None:
    dest = tmp_path / "rejected"
    result = _generate(
        released_pair,
        pair_env,
        project_name="Cutover Rejected",
        archetype=case.archetype,
        capabilities=case.capabilities,
        platforms=case.platforms,
        dest=dest,
        extra_args=case.extra_args,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert not dest.exists()
    assert list(tmp_path.glob(".create-forge-*")) == []
    normalised = " ".join((result.stdout + result.stderr).split())
    for expected in case.expect:
        assert expected in normalised, (expected, normalised)


def test_the_client_reads_no_component_resource_to_negotiate_or_select(
    released_pair: ReleasedPair,
    pair_env: Mapping[str, str],
) -> None:
    """`create-forge list` names the full catalogue without ever touching a
    component resource -- descriptors alone are enough to negotiate and
    select, the client-boundary form of rows 328/329."""
    result = run(
        [str(released_pair.create_forge_script), "list"], REPO_ROOT, env=pair_env
    )
    assert_success(result, context="create-forge list")
    for component_id in (
        "changelog",
        "cli",
        "coverage",
        "data-science",
        "dependabot",
        "documentation",
        "dotenv-example",
        "github",
        "jupyter",
        "library",
        "pre-commit",
        "pyright",
        "renovate",
        "scientific-python",
    ):
        assert component_id in result.stdout, component_id
    for token in _PATH_LEAK_TOKENS:
        assert token not in result.stdout, token
