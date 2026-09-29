"""Per-composition output fingerprints -- FT-25.01 / ADR 0079.

The deterministic-output baseline the engine decomposition (FT-25.02) is
checked against. One fingerprint per accepted composition
(:func:`tests.composition_matrix.valid_compositions`) covers everything a
client can observe from a render: the plan's component order and per-file
ownership, every rendered target's bytes, and the generation-metadata
document (whose ``output`` digests restate the bytes). The provider version
inside the metadata is normalised so a version bump alone never moves the
baseline.

``tests/test_composition_sweep.py`` asserts every fingerprint under the
``sweep`` marker; ``tests/test_engine_baseline.py`` asserts one composition
per archetype in the fast suite. A mismatch is a behaviour change to explain,
never a fixture to regenerate reflexively. Regenerate deliberately with::

    uv run python -m tests.composition_fingerprints --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

from forge_template import parse_project_spec, render_project
from tests.composition_matrix import Composition, valid_compositions

if TYPE_CHECKING:
    from forge_template import ProjectSpec, RenderedProject

#: Bumped only when the fingerprint *definition* below changes.
FINGERPRINT_VERSION = 1

FINGERPRINTS_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "composition_fingerprints.json"
)

_PROVIDER_VERSION_PLACEHOLDER = "<provider-version>"


def sweep_payload(composition: Composition) -> dict[str, object]:
    """The canonical ProjectSpec payload the sweep renders for a composition."""
    options: dict[str, dict[str, object]] = {
        "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"},
    }
    if "github" in composition.platforms:
        options["github"] = {"organisation": "sweep-org"}
    if "coverage" in composition.capabilities:
        options["coverage"] = {"fail_under": 80}
    if "documentation" in composition.capabilities:
        options["documentation"] = {"site_name": "Sweep Fixture"}
    return {
        "protocol_version": 1,
        "project": {
            "name": "Composition Sweep Fixture",
            "package_name": "composition_sweep_fixture",
            "repository_name": "composition-sweep-fixture",
            "description": "FT-17.05 exhaustive composition sweep fixture.",
            "licence": "mit",
            "authors": [{"name": "Test User"}],
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {
            "archetype": composition.archetype,
            "capabilities": list(composition.capabilities),
            "platforms": list(composition.platforms),
        },
        "component_options": {
            component_id: value
            for component_id, value in options.items()
            if component_id == composition.archetype
            or component_id in composition.capabilities
            or component_id in composition.platforms
        },
    }


def sweep_spec(composition: Composition) -> ProjectSpec:
    return parse_project_spec(sweep_payload(composition))


def fingerprint(project: RenderedProject) -> str:
    """The sha256 of one render's canonical, client-observable content."""
    assert project.metadata is not None
    metadata = project.metadata.model_dump(mode="json")
    metadata["provider"]["version"] = _PROVIDER_VERSION_PLACEHOLDER
    document = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "component_order": list(project.plan.component_order),
        "plan": [item.model_dump(mode="json") for item in project.plan.files],
        "files": {
            item.target: hashlib.sha256(item.content).hexdigest()
            for item in project.files
        },
        "metadata": metadata,
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def composition_fingerprint(composition: Composition) -> str:
    return fingerprint(render_project(sweep_spec(composition)))


def load_fingerprints() -> dict[str, str]:
    loaded: dict[str, str] = json.loads(FINGERPRINTS_PATH.read_text(encoding="utf-8"))
    return loaded


def _entry(composition: Composition) -> tuple[str, str]:
    return composition.slug, composition_fingerprint(composition)


def write_fingerprints() -> int:
    """Render every accepted composition and rewrite the checked-in baseline."""
    compositions = valid_compositions()
    with ProcessPoolExecutor() as pool:
        entries = dict(pool.map(_entry, compositions, chunksize=16))
    text = json.dumps(dict(sorted(entries.items())), indent=2) + "\n"
    FINGERPRINTS_PATH.write_bytes(text.encode("utf-8"))
    return len(entries)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite tests/fixtures/composition_fingerprints.json",
    )
    args = parser.parse_args()
    if not args.write:
        parser.error("pass --write to regenerate the baseline deliberately")
    count = write_fingerprints()
    print(f"wrote {count} fingerprints to {FINGERPRINTS_PATH}")


if __name__ == "__main__":
    main()
