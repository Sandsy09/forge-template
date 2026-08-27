"""Test-only aggregation of the composition, file-conflict, and
template-variable contracts into one composed artefact.

This module is not part of ``forge_template``'s public surface: it exists so
``tests/test_composition_contract.py`` can produce one golden-comparable
artefact per ProjectSpec/catalogue scenario without ``src/forge_template``
gaining a rendering entry point of its own. Exposing a stable, discoverable
composition/rendering facade remains FT-06.07
(https://github.com/Sandsy09/forge-template/issues/38) work; this helper's
``compose`` is deliberately not exported from ``forge_template`` so that
ownership boundary stays intact.

Rendering here covers a target's *base* contribution only -- the component
that owns it. Extension-point contributions are recorded in the composed
plan (see ``resolve_output_plan``) but never spliced into a base's rendered
text, because the in-file marker syntax an extension point splices into is
also FT-06.07 work (docs/file-conflicts.md, docs/composition-order.md). The
Jinja environment uses ``StrictUndefined`` because
docs/template-variables.md states, normatively, that an undefined
template-variable reference must fail rather than silently render empty.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from jinja2 import Environment, StrictUndefined

from forge_template.component_manifest import ComponentManifest, load_component_manifest
from forge_template.composition import composition_plan
from forge_template.file_conflicts import TEMPLATE_SUFFIX, resolve_output_plan
from forge_template.project_spec import ProjectSpec
from forge_template.template_variables import (
    load_option_schema,
    resolve_template_variables,
)

FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"

_JINJA_ENV = Environment(undefined=StrictUndefined)


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


def _content_file(
    manifest_path: Path, manifest: ComponentManifest, source_path: str
) -> Path:
    """Resolve one owned content-relative path to its real file on disk."""
    component_root = manifest_path.parent.resolve(strict=True)
    relative = PurePosixPath(manifest.content_root) / PurePosixPath(source_path)
    return (component_root / Path(*relative.parts)).resolve(strict=True)


def compose(spec: ProjectSpec, manifest_paths: dict[str, Path]) -> dict[str, Any]:
    """Return the full composed artefact for spec over manifest_paths.

    Chains ``composition_plan`` -> ``resolve_output_plan`` ->
    ``resolve_template_variables``, then renders each output target's base
    contribution. The result is plain, JSON-native data (no tuples), so it
    compares directly against a golden fixture loaded with ``json.loads``.
    """
    manifests = {
        identifier: load_component_manifest(path)
        for identifier, path in manifest_paths.items()
    }
    plan = composition_plan(spec, manifest_paths.values())
    output_files = resolve_output_plan(plan)

    schemas = {
        identifier: load_option_schema(manifest_paths[identifier], manifest)
        for identifier, manifest in manifests.items()
    }
    variables = resolve_template_variables(spec, schemas)
    context = variables.as_context()

    tree: dict[str, str] = {}
    for output_file in output_files:
        component_id = output_file.base.component_id
        source_path = output_file.base.source_path
        source = _content_file(
            manifest_paths[component_id], manifests[component_id], source_path
        )
        text = source.read_text(encoding="utf-8")
        if source_path.endswith(TEMPLATE_SUFFIX):
            text = _JINJA_ENV.from_string(text).render(**context)
        tree[output_file.target] = text

    return {
        "order": [placement.manifest.id for placement in plan],
        "targets": {
            output_file.target: output_file.model_dump(mode="json")
            for output_file in output_files
        },
        "variables": context,
        "tree": tree,
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
