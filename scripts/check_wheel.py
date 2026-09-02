"""Verify the built wheel ships the public engine and excludes repo tooling.

Mirrors `create-forge`'s own `scripts/check_wheel.py` (invariant 5 there):
building into a fresh temporary directory each run means this can never pass
by matching a stale `dist/*.whl` left over from an earlier build, and
`subprocess.run(check=True)` means `uv build` failing can't be swallowed by a
pipe.

Three things must hold, all added by ADR 0036 ("publish the engine to
PyPI"):

1. The public engine facade and its content trees (`foundation/content`,
   `components/*/content`) ship in the wheel -- this is what makes
   `forge-template` installable and discoverable at all.
2. `adr.py`, `render.py`, `schema.py` and `github_actions.py` do not. They
   are this repo's own CI tooling: they inspect `copier.yml`, `docs/adr/`
   and `template/` paths that do not exist in an installed wheel, and
   `render.py`/`schema.py` import `yaml`, which stays a dev-group-only
   dependency rather than something every engine consumer downloads.
3. The wheel imports cleanly, and `discover_components()` returns the
   production catalogue, in an isolated environment resolving only
   `[project.dependencies]` -- no dev-group extras. This is the check that
   would have caught #8 (`pyyaml` imported but undeclared): exclusion alone
   proves the modules are absent, not that what remains is self-sufficient.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

_MUST_CONTAIN = (
    "forge_template/engine.py",
    "forge_template/project_spec.py",
    # The Foundation content source and its manifest -- the wheel is
    # undiscoverable without foundation.toml, and unusable without content/.
    "forge_template/foundation/foundation.toml",
    "forge_template/foundation/content/",
    # Every catalogue component ships its manifest, its owned content tree,
    # and its extension contributions. A `[tool.hatch.build.targets.wheel]`
    # `exclude` that dropped `component.toml`, `extensions/`, or a component's
    # `options.schema.json` would otherwise publish an unusable catalogue --
    # see FT-11.04 / ADR 0052.
    "forge_template/components/cli/component.toml",
    "forge_template/components/cli/content/",
    "forge_template/components/cli/extensions/",
    "forge_template/components/jupyter/component.toml",
    "forge_template/components/jupyter/content/",
    "forge_template/components/jupyter/extensions/",
    "forge_template/components/library/component.toml",
    "forge_template/components/library/content/",
    "forge_template/components/library/extensions/",
    "forge_template/components/library/options.schema.json",
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
_SMOKE_IMPORT = (
    "import forge_template; "
    "descriptors = forge_template.discover_components(); "
    "ids = sorted(d.id for d in descriptors); "
    "assert ids == ['cli', 'jupyter', 'library', 'scientific-python'], ids; "
    "print('discovered:', ids)"
)


def _build_wheel(out_dir: Path) -> Path:
    """Build a wheel into `out_dir` and return its path."""
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        check=True,
    )
    wheels = sorted(out_dir.glob("*.whl"))
    if len(wheels) != 1:
        msg = f"expected exactly one wheel in {out_dir}, found {len(wheels)}: {wheels}"
        raise RuntimeError(msg)
    return wheels[0]


def _check_contents(wheel: Path) -> list[str]:
    """Return a list of content-check failures, empty if everything holds."""
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()

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


def _check_isolated_import(wheel: Path) -> str | None:
    """Return an error message if the wheel fails to import/discover in
    isolation, resolving only its declared runtime dependencies.
    """  # noqa: D205
    result = subprocess.run(
        [
            "uv",
            "run",
            "--isolated",
            "--no-project",
            "--with",
            str(wheel),
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
            f"isolated import failed against declared dependencies only:\n"
            f"{result.stderr}"
        )
    return None


def main() -> int:
    """Build a wheel and fail loudly if it ships the wrong set of modules."""
    with tempfile.TemporaryDirectory() as tmp:
        wheel = _build_wheel(Path(tmp))
        failures = _check_contents(wheel)
        import_failure = _check_isolated_import(wheel)
        if import_failure:
            failures.append(import_failure)

        if failures:
            print("\n".join(failures), file=sys.stderr)
            return 1

    print(f"ok: {wheel.name} ships the engine facade only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
