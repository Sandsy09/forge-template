"""Golden-fixture scenarios exercised through the public engine facade.

The fixture-root override remains private and test-only; production discovery
always reads the installed package catalogue.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import forge_template.engine as engine_module
from forge_template import render_project
from forge_template.project_spec import ProjectSpec

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"


def project_spec(
    *,
    archetype: str,
    capabilities: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
    component_options: dict[str, dict[str, Any]] | None = None,
) -> ProjectSpec:
    """Build one ProjectSpec against a fixed project/Python identity.

    The identity itself is not what these tests exercise -- only the
    selection and options vary between scenarios.
    """
    return ProjectSpec.model_validate(
        {
            "protocol_version": 1,
            "project": {
                "name": "Example Project",
                "package_name": "example_project",
                "repository_name": "example-project",
                "licence": "mit",
            },
            "python": {"minimum": "3.11", "development": "3.13"},
            "components": {
                "archetype": archetype,
                "capabilities": capabilities,
                "platforms": platforms,
            },
            "component_options": component_options or {},
        }
    )


def compose(spec: ProjectSpec, manifest_paths: dict[str, Path]) -> dict[str, Any]:
    """Return the full composed artefact for spec over manifest_paths.

    Calls the supported ``render_project`` facade. The private fixture-root
    seam is restored even on failure, and the result is converted to plain
    JSON-native data for comparison with the checked-in goldens.
    """
    roots = {path.parent.parent for path in manifest_paths.values()}
    if len(roots) != 1:
        msg = "one golden scenario must use exactly one fixture catalogue"
        raise ValueError(msg)

    previous = engine_module._CATALOGUE_ROOT_OVERRIDE
    engine_module._CATALOGUE_ROOT_OVERRIDE = roots.pop()
    try:
        rendered = render_project(spec)
    finally:
        engine_module._CATALOGUE_ROOT_OVERRIDE = previous

    return {
        "order": list(rendered.plan.component_order),
        "targets": {
            planned_file.target: planned_file.model_dump(mode="json")
            for planned_file in rendered.plan.files
        },
        "tree": {
            rendered_file.target: rendered_file.content.decode("utf-8")
            for rendered_file in rendered.files
        },
    }


def _manifest_paths(*identifiers: str) -> dict[str, Path]:
    return {
        identifier: FIXTURES / identifier / "component.toml"
        for identifier in identifiers
    }


SCENARIOS: dict[str, tuple[ProjectSpec, dict[str, Path]]] = {
    "minimal": (
        project_spec(
            archetype="library",
            component_options={"library": {"build_backend": "uv_build"}},
        ),
        _manifest_paths("library"),
    ),
    "extension": (
        project_spec(
            archetype="library",
            capabilities=("coverage",),
            platforms=("github",),
            component_options={
                "library": {"build_backend": "hatchling"},
                "github": {"organisation": "forge-example"},
            },
        ),
        _manifest_paths("library", "coverage", "github"),
    ),
    "full": (
        project_spec(
            archetype="library",
            capabilities=("changelog", "coverage", "documentation"),
            platforms=("github",),
            component_options={
                "library": {"build_backend": "uv_build", "initial_version": "0.2.0"},
                "github": {"organisation": "forge-example"},
            },
        ),
        _manifest_paths("library", "changelog", "coverage", "documentation", "github"),
    ),
}
"""The composed scenarios golden fixtures cover.

``minimal`` is the floor: one archetype and nothing else, exercising an
empty capability/platform tier and a schema-supplied default alongside a
required option. ``extension`` is the canonical case that runs against tier
order: a capability (``coverage``) contributing to a platform
(``github``)'s extension point, applied in an earlier tier than its target.
``full`` selects every reference component at once, the kitchen-sink
pattern that has already caught real bugs the narrower scenarios missed
(see CLAUDE.md).
"""


def scenario_result(name: str) -> dict[str, Any]:
    """Return one named scenario's composed artefact.

    A thin wrapper so a subprocess invoked with a different
    ``PYTHONHASHSEED`` can reach one scenario by name from a one-line
    ``-c`` script, without duplicating ``SCENARIOS``' construction.
    """
    spec, manifest_paths = SCENARIOS[name]
    return compose(spec, manifest_paths)
