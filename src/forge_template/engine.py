"""Stable, side-effect-free Forge template-engine facade.

The public functions in this module are the supported boundary for
``create-forge`` and other clients. They discover only components bundled in
the installed ``forge-template`` distribution, validate the canonical
ProjectSpec, produce an immutable generation plan, and render an in-memory
file set. Destination orchestration deliberately remains a client concern.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from importlib import metadata, resources
from pathlib import Path, PurePosixPath
from typing import Literal, TypeAlias, overload

from jinja2 import Environment, StrictUndefined, TemplateError
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import InvalidName, canonicalize_name
from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from forge_template.component_manifest import (
    COMPONENT_MANIFEST_PROTOCOL_VERSION,
    ComponentManifest,
    component_resource_path,
    load_component_manifest,
    validate_manifest_selection,
    validate_manifest_set,
)
from forge_template.composition import ComponentPlacement, composition_plan
from forge_template.file_conflicts import (
    TEMPLATE_SUFFIX,
    OutputFile,
    output_target,
    resolve_output_plan,
)
from forge_template.project_spec import PROJECT_SPEC_PROTOCOL_VERSION, ProjectSpec
from forge_template.template_variables import (
    OptionSchema,
    load_option_schema,
    resolve_template_variables,
)

SUPPORTED_PROJECTSPEC_PROTOCOLS: tuple[int, ...] = (PROJECT_SPEC_PROTOCOL_VERSION,)
"""ProjectSpec wire protocols accepted by this engine compatibility line."""

SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS: tuple[int, ...] = (
    COMPONENT_MANIFEST_PROTOCOL_VERSION,
)
"""Component manifest protocols accepted by this engine compatibility line."""

_DISTRIBUTION_NAME = "forge-template"
_EXTENSION_TOKEN_START = "[[forge:extension"
_EXTENSION_TOKEN_RE = re.compile(
    r"^(?P<indent>[\t ]*)\[\[forge:extension "
    r"(?P<identifier>[a-z][a-z0-9]*(?:-[a-z0-9]+)*)\]\](?:\r?\n|$)",
    re.MULTILINE,
)
_JINJA_ENVIRONMENT = Environment(
    autoescape=False,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)

# Deliberately private: tests replace this with the checked-in fixture
# catalogue. Public clients cannot redirect discovery to arbitrary content.
_CATALOGUE_ROOT_OVERRIDE: Path | None = None

ProjectSpecPayload: TypeAlias = ProjectSpec | Mapping[str, object] | str | bytes
"""Inputs accepted by :func:`parse_project_spec`."""


class _PublicModel(BaseModel):
    """Shared strict and immutable behaviour for public result models."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EngineInfo(_PublicModel):
    """Installed engine package and data-protocol compatibility metadata."""

    package_version: str
    projectspec_protocols: tuple[int, ...]
    component_manifest_protocols: tuple[int, ...]


class ComponentRelation(_PublicModel):
    """One component requirement or conflict exposed for client guidance."""

    id: str
    version: str | None = None


class ComponentOption(_PublicModel):
    """One owner-local option declaration exposed during discovery."""

    name: str
    type: Literal["string", "integer", "boolean", "string_list"]
    required: bool
    default: JsonValue
    choices: tuple[JsonValue, ...]
    description: str


class ComponentDescriptor(_PublicModel):
    """Path-free component metadata suitable for client choice presentation."""

    id: str
    name: str
    description: str
    kind: Literal["archetype", "capability", "platform"]
    version: str
    projectspec_protocols: tuple[int, ...]
    requires_python: str
    requires: tuple[ComponentRelation, ...]
    conflicts: tuple[ComponentRelation, ...]
    options: tuple[ComponentOption, ...]


class PlannedExtension(_PublicModel):
    """One selected component extending an owner-declared point."""

    component_id: str
    extension_point: str


class PlannedFile(_PublicModel):
    """One generated target and its component ownership metadata."""

    target: str
    owner_component_id: str
    extensions: tuple[PlannedExtension, ...] = ()


class GenerationPlan(_PublicModel):
    """Deterministic, path-free preview of a generation request."""

    component_order: tuple[str, ...]
    files: tuple[PlannedFile, ...]


class RenderedFile(_PublicModel):
    """One immutable project-relative target and its rendered bytes."""

    target: str
    content: bytes


class RenderedProject(_PublicModel):
    """A generation plan and its deterministic in-memory file set."""

    plan: GenerationPlan
    files: tuple[RenderedFile, ...]


class EngineErrorCode(StrEnum):
    """Stable machine-readable categories for expected engine failures."""

    INVALID_PROJECT_SPEC = "invalid-project-spec"
    COMPONENT_DISCOVERY_FAILED = "component-discovery-failed"
    INVALID_COMPONENT_SELECTION = "invalid-component-selection"
    INVALID_COMPONENT_OPTIONS = "invalid-component-options"
    GENERATION_PLAN_FAILED = "generation-plan-failed"
    TEMPLATE_RENDER_FAILED = "template-render-failed"
    GENERATED_PROJECT_INVALID = "generated-project-invalid"


class EngineErrorDetail(_PublicModel):
    """One structured location and reason attached to an engine failure."""

    code: str
    path: tuple[str | int, ...] = ()
    message: str


class ForgeEngineError(Exception):
    """The single supported exception type for expected engine failures."""

    def __init__(
        self,
        *,
        code: EngineErrorCode,
        operation: str,
        message: str,
        details: tuple[EngineErrorDetail, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.operation = operation
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible representation for client diagnostics."""
        return {
            "code": self.code.value,
            "operation": self.operation,
            "message": self.message,
            "details": [detail.model_dump(mode="json") for detail in self.details],
        }


@dataclass(frozen=True)
class _ComponentRecord:
    manifest_path: Path
    manifest: ComponentManifest
    option_schema: OptionSchema


@dataclass(frozen=True)
class _PreparedGeneration:
    records: tuple[_ComponentRecord, ...]
    placements: tuple[ComponentPlacement, ...]
    outputs: tuple[OutputFile, ...]
    context: dict[str, JsonValue]
    plan: GenerationPlan


def _package_version() -> str:
    try:
        return metadata.version(_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        # A raw source-tree import is not a supported installed engine, but a
        # diagnostic value is more useful than making metadata inspection fail.
        return "0+unknown"


def get_engine_info() -> EngineInfo:
    """Return package/protocol metadata without discovering components."""
    return EngineInfo(
        package_version=_package_version(),
        projectspec_protocols=SUPPORTED_PROJECTSPEC_PROTOCOLS,
        component_manifest_protocols=SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS,
    )


def _validation_details(exc: ValidationError) -> tuple[EngineErrorDetail, ...]:
    return tuple(
        EngineErrorDetail(
            code=str(error["type"]),
            path=tuple(error["loc"]),
            message=str(error["msg"]),
        )
        for error in exc.errors()
    )


def _single_detail(code: str, message: str) -> tuple[EngineErrorDetail, ...]:
    return (EngineErrorDetail(code=code, message=message),)


def _detail_sort_key(
    detail: EngineErrorDetail,
) -> tuple[tuple[str, ...], str, str]:
    return tuple(str(part) for part in detail.path), detail.code, detail.message


def _duplicate_targets(targets: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for target in targets:
        if target in seen:
            duplicates.add(target)
        seen.add(target)
    return tuple(sorted(duplicates))


def _validate_pyproject(
    spec: ProjectSpec,
    content: bytes,
) -> list[EngineErrorDetail]:
    target = "pyproject.toml"
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [
            EngineErrorDetail(
                code="invalid-pyproject-encoding",
                path=(target,),
                message=f"pyproject.toml must be UTF-8: {exc}",
            )
        ]

    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return [
            EngineErrorDetail(
                code="invalid-pyproject-toml",
                path=(target,),
                message=f"pyproject.toml is not valid TOML: {exc}",
            )
        ]

    details: list[EngineErrorDetail] = []
    project = payload.get("project")
    if not isinstance(project, dict):
        return [
            EngineErrorDetail(
                code="invalid-project-table",
                path=(target, "project"),
                message="pyproject.toml must contain a [project] table.",
            )
        ]

    name = project.get("name")
    if not isinstance(name, str) or not name.strip():
        details.append(
            EngineErrorDetail(
                code="invalid-project-name",
                path=(target, "project", "name"),
                message="[project].name must be a non-empty distribution name.",
            )
        )
    else:
        try:
            actual_name = canonicalize_name(name, validate=True)
        except InvalidName as exc:
            details.append(
                EngineErrorDetail(
                    code="invalid-project-name",
                    path=(target, "project", "name"),
                    message=f"[project].name is not a valid distribution name: {exc}",
                )
            )
        else:
            expected_name = canonicalize_name(
                spec.project.repository_name,
                validate=True,
            )
            if actual_name != expected_name:
                details.append(
                    EngineErrorDetail(
                        code="project-name-mismatch",
                        path=(target, "project", "name"),
                        message=(
                            "[project].name must match ProjectSpec "
                            f"repository_name {spec.project.repository_name!r} after "
                            "distribution-name normalisation."
                        ),
                    )
                )

    requires_python = project.get("requires-python")
    if not isinstance(requires_python, str):
        details.append(
            EngineErrorDetail(
                code="invalid-requires-python",
                path=(target, "project", "requires-python"),
                message="[project].requires-python must be a string.",
            )
        )
    else:
        try:
            SpecifierSet(requires_python)
        except InvalidSpecifier as exc:
            details.append(
                EngineErrorDetail(
                    code="invalid-requires-python",
                    path=(target, "project", "requires-python"),
                    message=f"[project].requires-python is invalid: {exc}",
                )
            )
        else:
            expected = f">={spec.python.minimum}"
            if requires_python != expected:
                details.append(
                    EngineErrorDetail(
                        code="python-requires-mismatch",
                        path=(target, "project", "requires-python"),
                        message=(
                            f"[project].requires-python must be exactly {expected!r}."
                        ),
                    )
                )

    return details


def validate_rendered_project(
    spec: ProjectSpec,
    project: RenderedProject,
) -> RenderedProject:
    """Validate an immutable rendered project without filesystem side effects.

    See ``docs/generated-project-validation.md`` for the supported contract.
    """
    details: list[EngineErrorDetail] = []
    planned_targets = tuple(item.target for item in project.plan.files)
    rendered_targets = tuple(item.target for item in project.files)

    for target in _duplicate_targets(planned_targets):
        details.append(
            EngineErrorDetail(
                code="duplicate-plan-target",
                path=(target,),
                message=f"Generation plan contains duplicate target {target!r}.",
            )
        )
    if planned_targets != tuple(sorted(planned_targets)):
        details.append(
            EngineErrorDetail(
                code="unordered-plan-targets",
                path=("plan", "files"),
                message="Generation plan targets must be in lexical order.",
            )
        )

    for target in _duplicate_targets(rendered_targets):
        details.append(
            EngineErrorDetail(
                code="duplicate-rendered-target",
                path=(target,),
                message=f"Rendered project contains duplicate target {target!r}.",
            )
        )
    if rendered_targets != tuple(sorted(rendered_targets)):
        details.append(
            EngineErrorDetail(
                code="unordered-rendered-targets",
                path=("files",),
                message="Rendered project targets must be in lexical order.",
            )
        )

    planned_set = set(planned_targets)
    rendered_set = set(rendered_targets)
    for target in sorted(planned_set - rendered_set):
        details.append(
            EngineErrorDetail(
                code="missing-rendered-file",
                path=(target,),
                message=f"Planned target {target!r} is missing from rendered output.",
            )
        )
    for target in sorted(rendered_set - planned_set):
        details.append(
            EngineErrorDetail(
                code="unexpected-rendered-file",
                path=(target,),
                message=f"Rendered target {target!r} is not present in the plan.",
            )
        )

    if "pyproject.toml" not in planned_set or "pyproject.toml" not in rendered_set:
        details.append(
            EngineErrorDetail(
                code="missing-pyproject",
                path=("pyproject.toml",),
                message="A generated project must plan and render pyproject.toml.",
            )
        )

    rendered_by_target: dict[str, bytes] = {}
    for rendered_file in project.files:
        rendered_by_target.setdefault(rendered_file.target, rendered_file.content)
        try:
            text = rendered_file.content.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if _EXTENSION_TOKEN_START in text:
            details.append(
                EngineErrorDetail(
                    code="unresolved-extension-marker",
                    path=(rendered_file.target,),
                    message=(
                        f"Rendered target {rendered_file.target!r} contains an "
                        "unresolved Forge extension marker."
                    ),
                )
            )

    pyproject = rendered_by_target.get("pyproject.toml")
    if pyproject is not None:
        details.extend(_validate_pyproject(spec, pyproject))

    if details:
        raise ForgeEngineError(
            code=EngineErrorCode.GENERATED_PROJECT_INVALID,
            operation="validate-output",
            message="The generated project is invalid.",
            details=tuple(sorted(details, key=_detail_sort_key)),
        )

    return project


@overload
def parse_project_spec(payload: ProjectSpec) -> ProjectSpec: ...


@overload
def parse_project_spec(payload: Mapping[str, object]) -> ProjectSpec: ...


@overload
def parse_project_spec(payload: str | bytes) -> ProjectSpec: ...


def parse_project_spec(payload: object) -> ProjectSpec:
    """Strictly parse one ProjectSpec wire payload without catalogue access."""
    if isinstance(payload, ProjectSpec):
        return payload

    try:
        if isinstance(payload, (str, bytes)):
            return ProjectSpec.model_validate_json(payload)
        if isinstance(payload, Mapping):
            return ProjectSpec.model_validate_json(json.dumps(dict(payload)))
    except (TypeError, ValueError, ValidationError) as exc:
        details = (
            _validation_details(exc)
            if isinstance(exc, ValidationError)
            else _single_detail("invalid-json-value", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.INVALID_PROJECT_SPEC,
            operation="parse",
            message="ProjectSpec is invalid.",
            details=details,
        ) from exc

    message = "ProjectSpec input must be a ProjectSpec, mapping, JSON string, or bytes."
    raise ForgeEngineError(
        code=EngineErrorCode.INVALID_PROJECT_SPEC,
        operation="parse",
        message=message,
        details=_single_detail("invalid-input-type", message),
    )


@contextmanager
def _catalogue_directory() -> Iterator[Path]:
    if _CATALOGUE_ROOT_OVERRIDE is not None:
        yield _CATALOGUE_ROOT_OVERRIDE.resolve(strict=True)
        return

    package_root = resources.files("forge_template.components")
    with resources.as_file(package_root) as resolved:
        yield resolved


def _load_catalogue() -> tuple[_ComponentRecord, ...]:
    try:
        with _catalogue_directory() as root:
            manifest_paths = tuple(sorted(root.rglob("component.toml")))
            loaded = tuple(
                (path, load_component_manifest(path)) for path in manifest_paths
            )
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise ForgeEngineError(
            code=EngineErrorCode.COMPONENT_DISCOVERY_FAILED,
            operation="discover",
            message="The installed component catalogue could not be read.",
            details=_single_detail("catalogue-unavailable", str(exc)),
        ) from exc
    except (ValueError, ValidationError) as exc:
        details = (
            _validation_details(exc)
            if isinstance(exc, ValidationError)
            else _single_detail("invalid-manifest", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.COMPONENT_DISCOVERY_FAILED,
            operation="discover",
            message="The installed component catalogue is invalid.",
            details=details,
        ) from exc

    try:
        validate_manifest_set(manifest for _path, manifest in loaded)
        return tuple(
            _ComponentRecord(
                manifest_path=path,
                manifest=manifest,
                option_schema=load_option_schema(path, manifest),
            )
            for path, manifest in loaded
        )
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        details = (
            _validation_details(exc)
            if isinstance(exc, ValidationError)
            else _single_detail("invalid-catalogue", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.COMPONENT_DISCOVERY_FAILED,
            operation="discover",
            message="The installed component catalogue is invalid.",
            details=details,
        ) from exc


def _descriptor(record: _ComponentRecord) -> ComponentDescriptor:
    manifest = record.manifest
    return ComponentDescriptor(
        id=manifest.id,
        name=manifest.name,
        description=manifest.description,
        kind=manifest.kind,
        version=manifest.version,
        projectspec_protocols=manifest.compatibility.projectspec_protocols,
        requires_python=manifest.compatibility.requires_python,
        requires=tuple(
            ComponentRelation(id=reference.id, version=reference.version)
            for reference in manifest.requires
        ),
        conflicts=tuple(
            ComponentRelation(id=reference.id, version=reference.version)
            for reference in manifest.conflicts
        ),
        options=tuple(
            ComponentOption(
                name=option.name,
                type=option.type,
                required=option.required,
                default=option.default,
                choices=option.choices,
                description=option.description,
            )
            for option in record.option_schema.options
        ),
    )


def discover_components() -> tuple[ComponentDescriptor, ...]:
    """Return the installed, reviewed component catalogue in lexical order."""
    return tuple(_descriptor(record) for record in _load_catalogue())


def _validate_against_catalogue(
    spec: ProjectSpec, records: tuple[_ComponentRecord, ...]
) -> None:
    manifests = tuple(record.manifest for record in records)
    try:
        validate_manifest_selection(spec, manifests)
    except (ValueError, ValidationError) as exc:
        details = (
            _validation_details(exc)
            if isinstance(exc, ValidationError)
            else _single_detail("invalid-selection", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.INVALID_COMPONENT_SELECTION,
            operation="validate",
            message="ProjectSpec component selection is invalid.",
            details=details,
        ) from exc

    schemas = {record.manifest.id: record.option_schema for record in records}
    try:
        resolve_template_variables(spec, schemas)
    except (ValueError, ValidationError) as exc:
        details = (
            _validation_details(exc)
            if isinstance(exc, ValidationError)
            else _single_detail("invalid-options", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.INVALID_COMPONENT_OPTIONS,
            operation="validate",
            message="ProjectSpec component options are invalid.",
            details=details,
        ) from exc


def validate_project_spec(spec: ProjectSpec) -> ProjectSpec:
    """Validate a parsed ProjectSpec against the installed component catalogue."""
    _validate_against_catalogue(spec, _load_catalogue())
    return spec


def _public_plan(
    placements: tuple[ComponentPlacement, ...], outputs: tuple[OutputFile, ...]
) -> GenerationPlan:
    return GenerationPlan(
        component_order=tuple(placement.manifest.id for placement in placements),
        files=tuple(
            PlannedFile(
                target=output.target,
                owner_component_id=output.base.component_id,
                extensions=tuple(
                    PlannedExtension(
                        component_id=extension.component_id,
                        extension_point=extension.extension_point or "",
                    )
                    for extension in output.extensions
                ),
            )
            for output in outputs
        ),
    )


def _owned_source(record: _ComponentRecord, source_path: str) -> Path:
    relative = PurePosixPath(record.manifest.content_root) / PurePosixPath(source_path)
    return component_resource_path(record.manifest_path, relative.as_posix())


def _contribution_source(record: _ComponentRecord, source_path: str) -> Path:
    return component_resource_path(record.manifest_path, source_path)


def _points_for_output(record: _ComponentRecord, target: str) -> tuple[str, ...]:
    content_root = PurePosixPath(record.manifest.content_root)
    return tuple(
        point.id
        for point in record.manifest.extension_points
        if output_target(
            PurePosixPath(point.content).relative_to(content_root).as_posix()
        )
        == target
    )


def _read_extension_text(path: Path, *, role: str) -> str:
    if not path.name.endswith(TEMPLATE_SUFFIX):
        msg = f"{role} must be a .jinja UTF-8 text resource"
        raise ValueError(msg)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        msg = f"{role} must be valid UTF-8 text"
        raise ValueError(msg) from exc


def _validate_extension_contract(
    outputs: tuple[OutputFile, ...], records_by_id: dict[str, _ComponentRecord]
) -> None:
    for output in outputs:
        owner = records_by_id[output.base.component_id]
        declared = _points_for_output(owner, output.target)
        source = _owned_source(owner, output.base.source_path)

        if not source.name.endswith(TEMPLATE_SUFFIX):
            if declared or _EXTENSION_TOKEN_START.encode() in source.read_bytes():
                msg = f"extension owner {output.target!r} must be a .jinja resource"
                raise ValueError(msg)
            continue

        try:
            owner_text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            msg = f"template owner {output.target!r} must be valid UTF-8 text"
            raise ValueError(msg) from exc

        markers = tuple(_EXTENSION_TOKEN_RE.finditer(owner_text))
        if owner_text.count(_EXTENSION_TOKEN_START) != len(markers):
            msg = f"template {output.target!r} contains a malformed extension token"
            raise ValueError(msg)

        marker_ids = tuple(marker.group("identifier") for marker in markers)
        undeclared = sorted(set(marker_ids) - set(declared))
        if undeclared:
            msg = (
                f"template {output.target!r} contains undeclared extension point(s): "
                + ", ".join(undeclared)
            )
            raise ValueError(msg)

        for point in declared:
            count = marker_ids.count(point)
            if count != 1:
                msg = (
                    f"template {output.target!r} must contain extension point "
                    f"{point!r} exactly once; found {count}"
                )
                raise ValueError(msg)

        for extension in output.extensions:
            contributor = records_by_id[extension.component_id]
            contribution = _contribution_source(contributor, extension.source_path)
            text = _read_extension_text(
                contribution,
                role=(
                    f"contribution {extension.component_id!r} to "
                    f"{extension.extension_point!r}"
                ),
            )
            if text and not text.endswith("\n"):
                msg = (
                    f"contribution {extension.component_id!r} to "
                    f"{extension.extension_point!r} must end with a newline"
                )
                raise ValueError(msg)
            if _EXTENSION_TOKEN_START in text:
                msg = (
                    f"contribution {extension.component_id!r} must not contain "
                    "nested extension tokens"
                )
                raise ValueError(msg)


def _prepare_generation(spec: ProjectSpec) -> _PreparedGeneration:
    records = _load_catalogue()
    _validate_against_catalogue(spec, records)
    records_by_id = {record.manifest.id: record for record in records}

    try:
        placements = composition_plan(
            spec, (record.manifest_path for record in records)
        )
        outputs = resolve_output_plan(placements)
        schemas = {record.manifest.id: record.option_schema for record in records}
        variables = resolve_template_variables(spec, schemas)
        _validate_extension_contract(outputs, records_by_id)
    except ForgeEngineError:
        raise
    except (OSError, ValueError, ValidationError) as exc:
        details = (
            _validation_details(exc)
            if isinstance(exc, ValidationError)
            else _single_detail("invalid-generation-plan", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.GENERATION_PLAN_FAILED,
            operation="plan",
            message="The generation plan is invalid.",
            details=details,
        ) from exc

    return _PreparedGeneration(
        records=records,
        placements=placements,
        outputs=outputs,
        context=variables.as_context(),
        plan=_public_plan(placements, outputs),
    )


def plan_generation(spec: ProjectSpec) -> GenerationPlan:
    """Return a deterministic, side-effect-free plan for one ProjectSpec."""
    return _prepare_generation(spec).plan


def _indent_contribution(text: str, indent: str) -> str:
    return "".join(
        f"{indent}{line}" if line.rstrip("\r\n") else line
        for line in text.splitlines(keepends=True)
    )


def _assembled_template(
    output: OutputFile,
    records_by_id: dict[str, _ComponentRecord],
) -> str:
    owner = records_by_id[output.base.component_id]
    source = _owned_source(owner, output.base.source_path)
    text = source.read_text(encoding="utf-8")
    by_point: dict[str, list[str]] = {}
    for extension in output.extensions:
        contributor = records_by_id[extension.component_id]
        contribution = _contribution_source(contributor, extension.source_path)
        by_point.setdefault(extension.extension_point or "", []).append(
            contribution.read_text(encoding="utf-8")
        )

    def replace(marker: re.Match[str]) -> str:
        indent = marker.group("indent")
        identifier = marker.group("identifier")
        return "".join(
            _indent_contribution(contribution, indent)
            for contribution in by_point.get(identifier, [])
        )

    return _EXTENSION_TOKEN_RE.sub(replace, text)


def render_project(spec: ProjectSpec) -> RenderedProject:
    """Render one ProjectSpec to immutable in-memory project-relative files."""
    prepared = _prepare_generation(spec)
    records_by_id = {record.manifest.id: record for record in prepared.records}
    rendered: list[RenderedFile] = []

    try:
        for output in prepared.outputs:
            owner = records_by_id[output.base.component_id]
            source = _owned_source(owner, output.base.source_path)
            if output.base.source_path.endswith(TEMPLATE_SUFFIX):
                assembled = _assembled_template(output, records_by_id)
                content = (
                    _JINJA_ENVIRONMENT.from_string(assembled)
                    .render(**prepared.context)
                    .encode("utf-8")
                )
            else:
                content = source.read_bytes()
            rendered.append(RenderedFile(target=output.target, content=content))
    except (OSError, UnicodeError, TemplateError, ValueError) as exc:
        raise ForgeEngineError(
            code=EngineErrorCode.TEMPLATE_RENDER_FAILED,
            operation="render",
            message="Project rendering failed.",
            details=_single_detail("template-render-failed", str(exc)),
        ) from exc

    project = RenderedProject(plan=prepared.plan, files=tuple(rendered))
    return validate_rendered_project(spec, project)
