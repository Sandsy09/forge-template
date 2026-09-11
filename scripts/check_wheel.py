"""Verify the built wheel and sdist ship the public engine, sanely.

Mirrors `create-forge`'s own `scripts/check_wheel.py` (invariant 5 there):
building into a fresh temporary directory each run means this can never pass
by matching a stale `dist/*` left over from an earlier build, and
`subprocess.run(check=True)` means `uv build` failing can't be swallowed by a
pipe.

Three things must hold for the **wheel**, all added by ADR 0036 ("publish the
engine to PyPI"):

1. The public engine facade and its content trees (`foundation/content`,
   `components/*/content`) ship in the wheel -- this is what makes
   `forge-template` installable and discoverable at all.
2. `adr.py`, `render.py`, `schema.py` and `github_actions.py` do not. They
   are this repo's own CI tooling: they inspect `copier.yml`, `docs/adr/`
   and `template/` paths that do not exist in an installed wheel, and
   `render.py`/`schema.py` import `yaml`, which stays a dev-group-only
   dependency rather than something every engine consumer downloads.
3. The wheel imports cleanly, `discover_components()` returns the production
   catalogue, `get_engine_info()` reports the negotiation facts, and one
   composition renders end to end, in an isolated environment resolving only
   `[project.dependencies]` -- no dev-group extras. This is the check that
   would have caught #8 (`pyyaml` imported but undeclared): exclusion alone
   proves the modules are absent, not that what remains is self-sufficient.

FT-17.05 (docs/provider-acceptance-validation.md) added the **sdist** audit
acceptance criterion 3 names alongside the wheel. An sdist is not a wheel with
a different suffix: by design (no `[tool.hatch.build.targets.sdist]`
override in `pyproject.toml`) it is the *rebuildable source archive* and
correctly contains the full repository -- `adr.py`, `render.py`, `tests/`,
`docs/`, `template/`, all of it, so a client can reproduce the wheel or run
this repo's own test suite from it. Applying the wheel's `_MUST_NOT_CONTAIN`
exclusion list to the sdist would therefore always fail, for the right
reason: that repo tooling is *supposed* to be there. The sdist audit instead
proves what an sdist actually promises -- it contains everything the wheel
needs to be rebuilt from (`_MUST_CONTAIN`, prefix-adjusted for
`<name>-<version>/src/forge_template/...`), it imports the same way once
built, and it stays under its own (much larger, since it carries the full
repo) size ceiling.

FT-14.02 (docs/cross-repository-validation.md) added the wheel size ceiling
below: ADR 0056 measured a 72,566-byte local review wheel; the published
`0.4.0` wheel is 72,544 bytes. FT-17.02 (the `github` platform) took a local
wheel to ~85 KB, FT-17.03 (the eight tooling capabilities) to ~105 KB, and
FT-17.04 (the reproducible-render `engine.py`/`generation_metadata.py`
additions, no new content trees) to ~108 KB, still under the 128 KiB ceiling.
FT-17.05 measured the sdist at ~726 KB (it carries the full repo, unlike the
wheel). Both ceilings are deliberately loose bounds, not tight pins -- archive
metadata (timestamps, compression) makes an exact byte count
non-reproducible across machines, but an unbounded content addition (a new
archetype or capability outgrowing the reviewed catalogue) should still fail
loudly here rather than silently ship.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

_MUST_CONTAIN = (
    "forge_template/engine.py",
    "forge_template/project_spec.py",
    "forge_template/generation_metadata.py",
    # The Foundation content source and its manifest -- the wheel is
    # undiscoverable without foundation.toml, and unusable without content/.
    "forge_template/foundation/foundation.toml",
    "forge_template/foundation/content/",
    # Every catalogue component ships its manifest, its owned content tree,
    # and its extension contributions. A `[tool.hatch.build.targets.wheel]`
    # `exclude` that dropped `component.toml`, `extensions/`, or a component's
    # `options.schema.json` would otherwise publish an unusable catalogue --
    # see FT-11.04 / ADR 0052.
    "forge_template/components/changelog/component.toml",
    "forge_template/components/changelog/content/",
    "forge_template/components/changelog/extensions/",
    "forge_template/components/cli/component.toml",
    "forge_template/components/cli/content/",
    "forge_template/components/cli/extensions/",
    "forge_template/components/coverage/component.toml",
    "forge_template/components/coverage/content/",
    "forge_template/components/coverage/extensions/",
    "forge_template/components/coverage/options.schema.json",
    "forge_template/components/data-science/component.toml",
    "forge_template/components/data-science/content/",
    "forge_template/components/data-science/extensions/",
    "forge_template/components/dependabot/component.toml",
    "forge_template/components/dependabot/content/",
    "forge_template/components/documentation/component.toml",
    "forge_template/components/documentation/content/",
    "forge_template/components/documentation/extensions/",
    "forge_template/components/documentation/options.schema.json",
    "forge_template/components/dotenv-example/component.toml",
    "forge_template/components/dotenv-example/content/",
    "forge_template/components/dotenv-example/extensions/",
    "forge_template/components/github/component.toml",
    "forge_template/components/github/content/",
    "forge_template/components/github/extensions/",
    "forge_template/components/github/options.schema.json",
    "forge_template/components/jupyter/component.toml",
    "forge_template/components/jupyter/content/",
    "forge_template/components/jupyter/extensions/",
    "forge_template/components/library/component.toml",
    "forge_template/components/library/content/",
    "forge_template/components/library/extensions/",
    "forge_template/components/library/options.schema.json",
    "forge_template/components/pre-commit/component.toml",
    "forge_template/components/pre-commit/content/",
    "forge_template/components/pre-commit/extensions/",
    "forge_template/components/pyright/component.toml",
    "forge_template/components/pyright/content/",
    "forge_template/components/pyright/extensions/",
    "forge_template/components/renovate/component.toml",
    "forge_template/components/renovate/content/",
    "forge_template/components/scientific-python/component.toml",
    "forge_template/components/scientific-python/content/",
    "forge_template/components/scientific-python/extensions/",
)
_MUST_NOT_CONTAIN = (
    "forge_template/adr.py",
    "forge_template/render.py",
    "forge_template/schema.py",
    "forge_template/github_actions.py",
)
# A generous ceiling around ADR 0056's 72,566-byte review measurement and the
# published 0.4.0 wheel's 72,544 bytes -- see the module docstring.
_MAX_WHEEL_BYTES = 131_072  # 128 KiB
# The sdist carries the full repository by design (see the module docstring),
# so its ceiling is set around FT-17.05's ~726 KB measurement instead of the
# wheel's -- a generous bound against the same unbounded-growth failure mode.
_MAX_SDIST_BYTES = 2_097_152  # 2 MiB
_SMOKE_IMPORT = (
    "import forge_template; "
    "info = forge_template.get_engine_info(); "
    "assert info.package_version and info.projectspec_protocols "
    "and info.component_manifest_protocols and info.metadata_version; "
    "descriptors = forge_template.discover_components(); "
    "ids = sorted(d.id for d in descriptors); "
    "assert ids == "
    "['changelog', 'cli', 'coverage', 'data-science', 'dependabot', "
    "'documentation', 'dotenv-example', 'github', 'jupyter', 'library', "
    "'pre-commit', 'pyright', 'renovate', 'scientific-python'], ids; "
    "spec = forge_template.parse_project_spec({"
    "'protocol_version': 1, "
    "'project': {'name': 'Smoke', 'package_name': 'smoke', "
    "'repository_name': 'smoke', 'description': 'd', 'licence': 'mit', "
    "'authors': [{'name': 'Smoke Test'}]}, "
    "'python': {'minimum': '3.11', 'development': '3.13'}, "
    "'components': {'archetype': 'library', 'capabilities': [], 'platforms': []}, "
    "'component_options': {'library': {'packaging_mode': 'uv-build-static', "
    "'initial_version': '0.1.0'}}}); "
    "project = forge_template.render_project(spec); "
    "assert project.files; "
    "print('discovered:', ids); "
    "print('negotiated:', info.package_version, info.metadata_version); "
    "print('rendered:', len(project.files), 'files')"
)


def _build_artefacts(out_dir: Path) -> tuple[Path, Path]:
    """Build a wheel and an sdist into `out_dir`; return (wheel, sdist)."""
    subprocess.run(
        ["uv", "build", "--out-dir", str(out_dir)],
        check=True,
    )
    wheels = sorted(out_dir.glob("*.whl"))
    sdists = sorted(out_dir.glob("*.tar.gz"))
    if len(wheels) != 1:
        msg = f"expected exactly one wheel in {out_dir}, found {len(wheels)}: {wheels}"
        raise RuntimeError(msg)
    if len(sdists) != 1:
        msg = f"expected exactly one sdist in {out_dir}, found {len(sdists)}: {sdists}"
        raise RuntimeError(msg)
    return wheels[0], sdists[0]


def _wheel_names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


def _sdist_names(sdist: Path) -> list[str]:
    """Member names, restated on the wheel's flat `forge_template/...` footing.

    Strips the `<name>-<version>/` archive prefix and the `src/` layout
    segment so they compare against `_MUST_CONTAIN` the same way the wheel's
    names do.
    """
    with tarfile.open(sdist) as archive:
        raw = archive.getnames()
    stripped = []
    for name in raw:
        _prefix, _sep, rest = name.partition("/")
        stripped.append(rest.removeprefix("src/"))
    return stripped


def _check_wheel_contents(wheel: Path) -> list[str]:
    """Return a list of content-check failures, empty if everything holds."""
    names = _wheel_names(wheel)

    failures = []
    for member in _MUST_CONTAIN:
        if not any(name.startswith(member) for name in names):
            failures.append(f"missing: {member!r} not found in {wheel.name}")
    for member in _MUST_NOT_CONTAIN:
        if any(name == member for name in names):
            failures.append(
                f"leaked: {member!r} is repo-local tooling and must not ship "
                f"in {wheel.name} -- check [tool.hatch.build.targets.wheel]'s "
                "exclude list"
            )
    return failures


def _check_sdist_contents(sdist: Path) -> list[str]:
    """The sdist's positive obligation only.

    See the module docstring for why `_MUST_NOT_CONTAIN` does not apply to it.
    """
    names = _sdist_names(sdist)
    failures = []
    for member in _MUST_CONTAIN:
        if not any(name.startswith(member) for name in names):
            failures.append(
                f"missing: {member!r} not found in {sdist.name} -- the sdist "
                "must carry everything needed to rebuild the wheel"
            )
    return failures


def _check_size(artefact: Path, *, ceiling: int, doc: str) -> str | None:
    """Return an error message if `artefact` exceeds `ceiling` bytes."""
    size = artefact.stat().st_size
    if size > ceiling:
        return (
            f"too large: {artefact.name} is {size:,} bytes, over the "
            f"{ceiling:,}-byte ceiling recorded in {doc} -- if this growth "
            "is expected, re-measure and raise the ceiling deliberately"
        )
    return None


def _check_isolated_import(artefact: Path) -> str | None:
    """Return an error message if `artefact` fails the isolated smoke test.

    `artefact` is a wheel or an sdist; either must import, discover, negotiate
    and render in isolation, resolving only its declared runtime dependencies.
    """
    result = subprocess.run(
        [
            "uv",
            "run",
            "--isolated",
            "--no-project",
            "--with",
            str(artefact),
            "python",
            "-c",
            _SMOKE_IMPORT,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return (
            f"isolated import failed against declared dependencies only "
            f"({artefact.name}):\n{result.stderr}"
        )
    return None


def _identity(artefact: Path) -> str:
    """One printable evidence line: this artefact's name, size and digest."""
    digest = hashlib.sha256(artefact.read_bytes()).hexdigest()
    size = artefact.stat().st_size
    return f"{artefact.name}  {size:,} bytes  sha256:{digest}"


def main() -> int:
    """Build both artefacts and fail loudly if either is wrong."""
    with tempfile.TemporaryDirectory() as tmp:
        wheel, sdist = _build_artefacts(Path(tmp))

        failures = _check_wheel_contents(wheel)
        if size_failure := _check_size(
            wheel,
            ceiling=_MAX_WHEEL_BYTES,
            doc="docs/cross-repository-validation.md",
        ):
            failures.append(size_failure)
        if import_failure := _check_isolated_import(wheel):
            failures.append(import_failure)

        failures.extend(_check_sdist_contents(sdist))
        if sdist_size_failure := _check_size(
            sdist,
            ceiling=_MAX_SDIST_BYTES,
            doc="docs/provider-acceptance-validation.md",
        ):
            failures.append(sdist_size_failure)
        if sdist_import_failure := _check_isolated_import(sdist):
            failures.append(sdist_import_failure)

        if failures:
            print("\n".join(failures), file=sys.stderr)
            return 1

        wheel_identity = _identity(wheel)
        sdist_identity = _identity(sdist)

    print(f"ok: {wheel_identity}")
    print(f"ok: {sdist_identity}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
