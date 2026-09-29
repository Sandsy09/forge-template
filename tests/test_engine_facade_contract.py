"""Frozen engine-facade characterisation -- FT-25.01 / ADR 0079.

The compatibility baseline the engine decomposition (FT-25.02) must keep
byte-for-byte. It complements, and does not restate, the existing pins:

- ``tests/test_cutover_gates.py`` -- the ``forge_template.__all__`` name set
  and the shipped ``EngineErrorCode`` values;
- ``tests/test_engine.py`` -- public parameter names/kinds and result-model
  field names.

What this module adds is recorded in ``tests/fixtures/engine_facade_baseline.json``
(regenerate deliberately with ``--update-goldens``, then review the diff):

- every public callable's full signature string, annotations and defaults
  included, and the ``parse_project_spec`` overload set;
- every public model's configuration and JSON schema (field types, defaults,
  required-ness) -- class names, never ``__module__``, which ADR 0079 makes
  non-contractual;
- the structured-error identity of every documented failure path: ``code``,
  ``operation``, top-level ``message``, and each detail's ``code``/``path``.

Plus unconditional import-behaviour assertions: both supported import paths
resolve to the same objects, and importing the package reads no catalogue,
loads no check-only module, and writes nothing.
"""

from __future__ import annotations

import inspect
import json
import shutil
import subprocess
import sys
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

import forge_template
import forge_template.engine
from forge_template import (
    EngineErrorCode,
    ForgeEngineError,
    GenerationMetadata,
    RenderedFile,
    RenderedProject,
    discover_components,
    map_legacy_library_answers,
    parse_generation_metadata,
    parse_project_spec,
    plan_generation,
    plan_update,
    render_project,
    validate_project_spec,
    validate_rendered_project,
    verify_generation_metadata,
)
from tests.engine_seams import override_sources

BASELINE = Path(__file__).parent / "fixtures" / "engine_facade_baseline.json"
_COMPONENT_FIXTURES = Path(__file__).parent / "fixtures" / "component_manifests"

#: Every ``forge_template.__all__`` name also reachable as an attribute of
#: ``forge_template.engine`` in 0.6.0. Clients are told to import from the
#: package, but these have been reachable from the module since they shipped,
#: so the decomposition keeps every one of them (as the same object).
_ENGINE_MODULE_NAMES = frozenset(
    {
        "AppliedRename",
        "ComponentDescriptor",
        "ComponentOption",
        "ComponentRelation",
        "EngineErrorCode",
        "EngineErrorDetail",
        "EngineInfo",
        "ForgeEngineError",
        "FoundationOwner",
        "GENERATION_METADATA_VERSION",
        "GenerationMetadata",
        "GenerationPlan",
        "MetadataProtocols",
        "OutputRecord",
        "PROJECT_SPEC_PROTOCOL_VERSION",
        "PlannedExtension",
        "PlannedFile",
        "ProjectSpec",
        "ProviderIdentity",
        "RenderedFile",
        "RenderedProject",
        "ReproductionRecord",
        "SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS",
        "SUPPORTED_PROJECTSPEC_PROTOCOLS",
        "SelectedComponent",
        "UpdatePlan",
        "UpdateTarget",
        "discover_components",
        "get_engine_info",
        "map_legacy_library_answers",
        "parse_generation_metadata",
        "parse_project_spec",
        "plan_generation",
        "plan_update",
        "render_project",
        "validate_project_spec",
        "validate_rendered_project",
        "verify_generation_metadata",
    }
)

#: Repository check-only modules the wheel excludes (scripts/check_wheel.py).
_CHECK_ONLY_MODULES = (
    "forge_template.adr",
    "forge_template.render",
    "forge_template.schema",
    "forge_template.github_actions",
)


def _public(name: str) -> Any:
    return getattr(forge_template, name)


def _public_callables() -> dict[str, Callable[..., Any]]:
    return {
        name: _public(name)
        for name in sorted(forge_template.__all__)
        if inspect.isfunction(_public(name))
    }


def _public_models() -> dict[str, type[BaseModel]]:
    return {
        name: _public(name)
        for name in sorted(forge_template.__all__)
        if inspect.isclass(_public(name)) and issubclass(_public(name), BaseModel)
    }


def _signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {
        name: str(inspect.signature(function))
        for name, function in _public_callables().items()
    }
    signatures["parse_project_spec@overloads"] = [
        str(inspect.signature(overload))
        for overload in typing.get_overloads(parse_project_spec)
    ]
    signatures["ForgeEngineError.__init__"] = str(
        inspect.signature(ForgeEngineError.__init__)
    )
    signatures["ForgeEngineError.as_dict"] = str(
        inspect.signature(ForgeEngineError.as_dict)
    )
    return signatures


def _models() -> dict[str, Any]:
    return {
        name: {
            "config": {
                key: model.model_config.get(key)
                for key in ("extra", "frozen", "strict", "populate_by_name")
            },
            "schema": model.model_json_schema(),
        }
        for name, model in _public_models().items()
    }


def _constants() -> dict[str, Any]:
    return {
        "PROJECT_SPEC_PROTOCOL_VERSION": forge_template.PROJECT_SPEC_PROTOCOL_VERSION,
        "SUPPORTED_PROJECTSPEC_PROTOCOLS": list(
            forge_template.SUPPORTED_PROJECTSPEC_PROTOCOLS
        ),
        "SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS": list(
            forge_template.SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS
        ),
        "GENERATION_METADATA_VERSION": forge_template.GENERATION_METADATA_VERSION,
        "DEFAULT_GENERATION_METADATA_TARGET": (
            forge_template.DEFAULT_GENERATION_METADATA_TARGET
        ),
        "EngineErrorCode": {member.name: member.value for member in EngineErrorCode},
    }


# --- The structured-error identity table -------------------------------------


def _library_payload(**options: object) -> dict[str, Any]:
    return {
        "protocol_version": 1,
        "project": {
            "name": "Example Project",
            "package_name": "example_project",
            "repository_name": "example-project",
            "licence": "mit",
        },
        "python": {"minimum": "3.11", "development": "3.13"},
        "components": {"archetype": "library", "capabilities": [], "platforms": []},
        "component_options": {"library": dict(options)} if options else {},
    }


def _library_project() -> RenderedProject:
    return render_project(parse_project_spec(_library_payload()))


def _document(project: RenderedProject) -> dict[str, Any]:
    assert project.metadata is not None
    loaded: dict[str, Any] = json.loads(project.metadata.to_json())
    return loaded


def _old(project: RenderedProject) -> dict[str, bytes]:
    return {item.target: item.content for item in project.files}


def _identity(error: ForgeEngineError) -> dict[str, Any]:
    payload = error.as_dict()
    assert set(payload) == {"code", "operation", "message", "details"}
    # The installed package version appears in one message; normalise it so
    # a release bump alone never moves the baseline.
    version = forge_template.get_engine_info().package_version
    return {
        "code": error.code.value,
        "operation": error.operation,
        "message": error.message.replace(repr(version), "'<package-version>'"),
        "details": [
            {"code": detail.code, "path": [str(part) for part in detail.path]}
            for detail in error.details
        ],
    }


def _scenarios(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> dict[str, Callable[[], object]]:
    """Every documented failure path, driven through the public facade only
    (plus the private test seam for an unreadable or broken catalogue)."""
    spec = parse_project_spec(_library_payload())
    project = _library_project()
    document = _document(project)
    assert project.metadata is not None
    metadata = project.metadata

    def missing_catalogue() -> object:
        override_sources(monkeypatch, catalogue=tmp_path / "missing")
        return discover_components()

    def missing_foundation_at_plan() -> object:
        empty = tmp_path / "empty-foundation"
        empty.mkdir()
        override_sources(monkeypatch, foundation=empty)
        return plan_generation(spec)

    def strict_undefined_at_render() -> object:
        root = tmp_path / "components"
        shutil.copytree(_COMPONENT_FIXTURES, root)
        source = root / "library" / "content" / "pyproject.toml.jinja"
        source.write_text(
            source.read_text(encoding="utf-8") + "\n{{ options.library.missing }}\n",
            encoding="utf-8",
        )
        override_sources(monkeypatch, catalogue=root, foundation=root)
        payload = _library_payload(build_backend="uv_build")
        return render_project(parse_project_spec(payload))

    unknown_archetype = _library_payload()
    unknown_archetype["components"]["archetype"] = "nonesuch"

    def tampered_old() -> dict[str, bytes]:
        old = _old(project)
        old["pyproject.toml"] = b"tampered\n"
        return old

    return {
        "parse_project_spec/invalid-mapping": lambda: parse_project_spec(
            {"protocol_version": 1}
        ),
        "parse_project_spec/invalid-json": lambda: parse_project_spec(b"{"),
        "parse_project_spec/invalid-type": lambda: parse_project_spec(42),  # type: ignore[call-overload]
        "discover_components/catalogue-unavailable": missing_catalogue,
        "validate_project_spec/unknown-archetype": lambda: validate_project_spec(
            parse_project_spec(unknown_archetype)
        ),
        "validate_project_spec/invalid-option": lambda: validate_project_spec(
            parse_project_spec(_library_payload(nonesuch=True))
        ),
        "plan_generation/foundation-unavailable": missing_foundation_at_plan,
        "render_project/strict-undefined": strict_undefined_at_render,
        "validate_rendered_project/empty-project": lambda: validate_rendered_project(
            spec,
            RenderedProject(
                plan=project.plan,
                files=(RenderedFile(target="README.md", content=b"x"),),
            ),
        ),
        "map_legacy_library_answers/unexpected": lambda: map_legacy_library_answers(
            {"build_backend": "uv_build", "versioning_resolved": "static", "x": "y"}
        ),
        "map_legacy_library_answers/missing": lambda: map_legacy_library_answers(
            {"build_backend": "uv_build"}
        ),
        "map_legacy_library_answers/non-string": lambda: map_legacy_library_answers(
            {"build_backend": "uv_build", "versioning_resolved": 1}
        ),
        "map_legacy_library_answers/unsupported": lambda: map_legacy_library_answers(
            {"build_backend": "uv_build", "versioning_resolved": "vcs"}
        ),
        "parse_generation_metadata/not-an-object": lambda: parse_generation_metadata(
            ["not", "an", "object"]  # type: ignore[arg-type]
        ),
        "parse_generation_metadata/not-json": lambda: parse_generation_metadata(
            "{not json"
        ),
        "parse_generation_metadata/malformed": lambda: parse_generation_metadata(
            {**document, "surprise": True}
        ),
        "parse_generation_metadata/unsupported-version": (
            lambda: parse_generation_metadata({**document, "metadata_version": 7})
        ),
        "parse_generation_metadata/unsupported-projectspec": (
            lambda: parse_generation_metadata(
                {**document, "protocols": {**document["protocols"], "projectspec": 7}}
            )
        ),
        "parse_generation_metadata/unsupported-manifest": (
            lambda: parse_generation_metadata(
                {
                    **document,
                    "protocols": {**document["protocols"], "component_manifest": [9]},
                }
            )
        ),
        "parse_generation_metadata/unknown-component": (
            lambda: parse_generation_metadata(
                {**document, "components": [{"id": "nonesuch", "version": "1.0.0"}]}
            )
        ),
        "parse_generation_metadata/version-drift": lambda: parse_generation_metadata(
            {**document, "components": [{"id": "library", "version": "0.0.1"}]}
        ),
        "parse_generation_metadata/selection-mismatch": (
            lambda: parse_generation_metadata({**document, "components": []})
        ),
        "parse_generation_metadata/spec-invalid": lambda: parse_generation_metadata(
            {**document, "spec": {"protocol_version": 1}}
        ),
        "verify_generation_metadata/coverage": lambda: verify_generation_metadata(
            metadata,
            RenderedProject(plan=project.plan, files=project.files[:-1]),
        ),
        "verify_generation_metadata/digest": lambda: verify_generation_metadata(
            metadata,
            RenderedProject(
                plan=project.plan,
                files=tuple(
                    RenderedFile(target=item.target, content=b"changed")
                    if item.target == "pyproject.toml"
                    else item
                    for item in project.files
                ),
            ),
        ),
        "plan_update/unavailable-provider": lambda: plan_update(
            document, old={}, new=project
        ),
        "plan_update/target-mismatch": lambda: plan_update(
            document, old={"only.txt": b""}, new=project
        ),
        "plan_update/digest-mismatch": lambda: plan_update(
            document, old=tampered_old(), new=project
        ),
        "plan_update/not-an-object": lambda: plan_update(
            7,  # type: ignore[arg-type]
            old=_old(project),
            new=project,
        ),
    }


def _error_table(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    table: dict[str, Any] = {}
    for name, scenario in _scenarios(monkeypatch, tmp_path).items():
        try:
            scenario()
        except ForgeEngineError as error:
            table[name] = _identity(error)
        else:  # pragma: no cover - a failure path that stopped failing
            table[name] = "did-not-raise"
        # A scenario may install a private seam; never leak it to the next.
        monkeypatch.undo()
    return table


def _inventory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    return {
        "constants": _constants(),
        "signatures": _signatures(),
        "models": _models(),
        "errors": _error_table(monkeypatch, tmp_path),
    }


def test_facade_matches_the_recorded_baseline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, update_goldens: bool
) -> None:
    """Signatures, model schemas and the error identity table are exactly
    the 0.6.0 facade. Regenerate only for a reviewed, deliberate change."""
    inventory = _inventory(monkeypatch, tmp_path)
    if update_goldens:
        text = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
        BASELINE.write_bytes(text.encode("utf-8"))
    recorded = json.loads(BASELINE.read_text(encoding="utf-8"))
    for section in ("constants", "signatures", "models", "errors"):
        assert inventory[section] == recorded[section], section


def test_every_documented_failure_path_raises_the_single_error_type(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    table = _error_table(monkeypatch, tmp_path)
    assert "did-not-raise" not in table.values()
    assert {entry["code"] for entry in table.values()} == {
        member.value for member in EngineErrorCode
    }, "every EngineErrorCode must be reachable from a characterised path"


def test_public_models_are_strict_frozen_and_closed() -> None:
    for name, model in _public_models().items():
        assert model.model_config.get("extra") == "forbid", name
        assert model.model_config.get("frozen") is True, name
        assert model.model_config.get("strict") is True, name


def test_both_import_paths_resolve_to_the_same_objects() -> None:
    reachable = {
        name for name in forge_template.__all__ if hasattr(forge_template.engine, name)
    }
    assert reachable == _ENGINE_MODULE_NAMES
    for name in _ENGINE_MODULE_NAMES:
        assert getattr(forge_template.engine, name) is _public(name), name
    assert set(forge_template.__all__) == {
        name for name in dir(forge_template) if name in forge_template.__all__
    }


_IMPORT_PROBE = """
import json, os, sys
before = set(os.listdir("."))
import forge_template
import forge_template.engine
print(json.dumps({
    "modules": sorted(m for m in sys.modules if m.startswith("forge_template")),
    "created": sorted(set(os.listdir(".")) - before),
}))
"""


def test_importing_the_facade_has_no_side_effects(tmp_path: Path) -> None:
    """Importing loads no check-only module, touches no component catalogue
    or Foundation package, and writes nothing to the working directory."""
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_PROBE],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    probe = json.loads(result.stdout)
    modules = set(probe["modules"])
    assert not modules & set(_CHECK_ONLY_MODULES), modules
    assert "forge_template.components" not in modules
    assert "forge_template.foundation" not in modules
    assert probe["created"] == []


def test_generation_metadata_is_the_public_type() -> None:
    project = _library_project()
    assert type(project.metadata) is GenerationMetadata
