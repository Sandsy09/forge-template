"""Planning, rendering and output validation (private engine module).

ADR 0079. Prepares a deterministic plan for a validated ProjectSpec, checks
the extension contract, assembles and renders every planned target into
memory, and validates a rendered project. Reads package resources only;
never writes, starts a process, or merges.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from jinja2 import Environment, StrictUndefined, TemplateError
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import InvalidName, canonicalize_name
from pydantic import JsonValue, ValidationError

from forge_template import _discovery
from forge_template._discovery import ComponentRecord, FoundationRecord
from forge_template._errors import (
    EngineErrorCode,
    EngineErrorDetail,
    ForgeEngineError,
    detail_sort_key,
    single_detail,
    validation_details,
)
from forge_template._models import (
    GenerationPlan,
    PlannedExtension,
    PlannedFile,
    RenderedFile,
    RenderedProject,
)
from forge_template.component_manifest import ExtensionPoint, component_resource_path
from forge_template.composition import ComponentPlacement, composition_plan
from forge_template.file_conflicts import (
    TEMPLATE_SUFFIX,
    FoundationOwner,
    OutputFile,
    Owner,
    output_target,
    render_output_path,
    resolve_output_plan,
)
from forge_template.project_spec import ProjectSpec
from forge_template.template_variables import resolve_template_variables

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


@dataclass(frozen=True)
class PreparedGeneration:
    records: tuple[ComponentRecord, ...]
    foundation: FoundationRecord | None
    placements: tuple[ComponentPlacement, ...]
    outputs: tuple[OutputFile, ...]
    context: dict[str, JsonValue]
    plan: GenerationPlan

    def component_versions(self) -> dict[str, str]:
        """Every catalogue component's installed version, keyed by id."""
        return {record.manifest.id: record.manifest.version for record in self.records}


# --- Output validation ---------------------------------------------------------


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


def validate_output(
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
            details=tuple(sorted(details, key=detail_sort_key)),
        )

    return project


# --- Planning ------------------------------------------------------------------


def _extension_owner_id(owner: Owner) -> str:
    """Return an extension contribution's owning component id.

    An ``extend``-disposition ``OutputContribution.owner`` is always a
    ``ComponentOwner`` -- Foundation is never selectable and never declares
    its own ``contributions`` -- so this narrows the shared ``Owner`` type
    ``resolve_output_plan`` uses for both ``create`` and ``extend`` entries.
    """
    if isinstance(owner, FoundationOwner):  # pragma: no cover - see docstring
        msg = "an extension contribution must not be owned by Foundation"
        raise AssertionError(msg)
    return owner.id


def _regeneration_for(
    output: OutputFile,
    dispositions_by_owner: Mapping[str, Mapping[str, str]],
) -> Literal["replace", "skip-if-exists"]:
    """Resolve one target's regeneration disposition from its owner's manifest.

    A ``[[regeneration]]`` record only takes effect for a target its own
    component owns -- the disposition travels with the content owner
    (ADR 0059 decision 8). Foundation-owned targets are always ``"replace"``.
    """
    owner = output.base.owner
    if isinstance(owner, FoundationOwner):
        return "replace"
    disposition = dispositions_by_owner.get(owner.id, {}).get(output.target, "replace")
    return "skip-if-exists" if disposition == "skip-if-exists" else "replace"


def _public_plan(
    placements: tuple[ComponentPlacement, ...], outputs: tuple[OutputFile, ...]
) -> GenerationPlan:
    dispositions_by_owner = {
        placement.manifest.id: {
            record.target: record.disposition
            for record in placement.manifest.regeneration
        }
        for placement in placements
    }
    return GenerationPlan(
        component_order=tuple(placement.manifest.id for placement in placements),
        files=tuple(
            PlannedFile(
                target=output.target,
                owner=output.base.owner,
                extensions=tuple(
                    PlannedExtension(
                        component_id=_extension_owner_id(extension.owner),
                        extension_point=extension.extension_point or "",
                    )
                    for extension in output.extensions
                ),
                regeneration=_regeneration_for(output, dispositions_by_owner),
            )
            for output in outputs
        ),
    )


def _owned_source(record: ComponentRecord, source_path: str) -> Path:
    relative = PurePosixPath(record.manifest.content_root) / PurePosixPath(source_path)
    return component_resource_path(record.manifest_path, relative.as_posix())


def _foundation_owned_source(foundation: FoundationRecord, source_path: str) -> Path:
    relative = PurePosixPath(foundation.placement.source.content_root) / PurePosixPath(
        source_path
    )
    return component_resource_path(foundation.manifest_path, relative.as_posix())


def _base_source(
    owner: Owner,
    source_path: str,
    records_by_id: dict[str, ComponentRecord],
    foundation: FoundationRecord | None,
) -> Path:
    """Resolve one base contribution's actual content file, by owner kind."""
    if isinstance(owner, FoundationOwner):
        # resolve_output_plan never claims a Foundation-owned base unless
        # foundation was supplied to it -- the same foundation in scope here.
        assert foundation is not None
        return _foundation_owned_source(foundation, source_path)
    return _owned_source(records_by_id[owner.id], source_path)


def _owner_extension_points(
    owner: Owner,
    records_by_id: dict[str, ComponentRecord],
    foundation: FoundationRecord | None,
) -> tuple[ExtensionPoint, ...]:
    if isinstance(owner, FoundationOwner):
        assert foundation is not None
        return foundation.placement.source.extension_points
    return records_by_id[owner.id].manifest.extension_points


def _owner_content_root(
    owner: Owner,
    records_by_id: dict[str, ComponentRecord],
    foundation: FoundationRecord | None,
) -> str:
    if isinstance(owner, FoundationOwner):
        assert foundation is not None
        return foundation.placement.source.content_root
    return records_by_id[owner.id].manifest.content_root


def _contribution_source(record: ComponentRecord, source_path: str) -> Path:
    return component_resource_path(record.manifest_path, source_path)


def _points_for_output(
    owner: Owner,
    target: str,
    context: dict[str, JsonValue],
    records_by_id: dict[str, ComponentRecord],
    foundation: FoundationRecord | None,
) -> tuple[str, ...]:
    content_root = PurePosixPath(_owner_content_root(owner, records_by_id, foundation))
    return tuple(
        point.id
        for point in _owner_extension_points(owner, records_by_id, foundation)
        if output_target(
            render_output_path(
                PurePosixPath(point.content).relative_to(content_root).as_posix(),
                context,
            )
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
    outputs: tuple[OutputFile, ...],
    context: dict[str, JsonValue],
    records_by_id: dict[str, ComponentRecord],
    foundation: FoundationRecord | None,
) -> None:
    for output in outputs:
        owner = output.base.owner
        declared = _points_for_output(
            owner, output.target, context, records_by_id, foundation
        )
        source = _base_source(owner, output.base.source_path, records_by_id, foundation)

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
            extension_owner_id = _extension_owner_id(extension.owner)
            contributor = records_by_id[extension_owner_id]
            contribution = _contribution_source(contributor, extension.source_path)
            text = _read_extension_text(
                contribution,
                role=(
                    f"contribution {extension_owner_id!r} to "
                    f"{extension.extension_point!r}"
                ),
            )
            if text and not text.endswith("\n"):
                msg = (
                    f"contribution {extension_owner_id!r} to "
                    f"{extension.extension_point!r} must end with a newline"
                )
                raise ValueError(msg)
            if _EXTENSION_TOKEN_START in text:
                msg = (
                    f"contribution {extension_owner_id!r} must not contain "
                    "nested extension tokens"
                )
                raise ValueError(msg)


def prepare_generation(spec: ProjectSpec) -> PreparedGeneration:
    records = _discovery.load_catalogue()
    foundation = _discovery.load_foundation()
    _discovery.validate_against_catalogue(spec, records, foundation)
    records_by_id = {record.manifest.id: record for record in records}

    try:
        placements = composition_plan(
            spec, (record.manifest_path for record in records)
        )
        schemas = {record.manifest.id: record.option_schema for record in records}
        variables = resolve_template_variables(spec, schemas)
        context = variables.as_context()
        outputs = resolve_output_plan(
            placements,
            context,
            foundation=foundation.placement if foundation is not None else None,
        )
        _validate_extension_contract(outputs, context, records_by_id, foundation)
    except ForgeEngineError:
        raise
    except (OSError, ValueError, ValidationError) as exc:
        details = (
            validation_details(exc)
            if isinstance(exc, ValidationError)
            else single_detail("invalid-generation-plan", str(exc))
        )
        raise ForgeEngineError(
            code=EngineErrorCode.GENERATION_PLAN_FAILED,
            operation="plan",
            message="The generation plan is invalid.",
            details=details,
        ) from exc

    return PreparedGeneration(
        records=records,
        foundation=foundation,
        placements=placements,
        outputs=outputs,
        context=context,
        plan=_public_plan(placements, outputs),
    )


# --- Rendering -----------------------------------------------------------------


def _indent_contribution(text: str, indent: str) -> str:
    return "".join(
        f"{indent}{line}" if line.rstrip("\r\n") else line
        for line in text.splitlines(keepends=True)
    )


def _assembled_template(
    output: OutputFile,
    records_by_id: dict[str, ComponentRecord],
    foundation: FoundationRecord | None,
) -> str:
    source = _base_source(
        output.base.owner, output.base.source_path, records_by_id, foundation
    )
    text = source.read_text(encoding="utf-8")
    by_point: dict[str, list[str]] = {}
    for extension in output.extensions:
        contributor = records_by_id[_extension_owner_id(extension.owner)]
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


def render_files(prepared: PreparedGeneration) -> tuple[RenderedFile, ...]:
    """Render every planned target of a prepared generation into memory."""
    records_by_id = {record.manifest.id: record for record in prepared.records}
    rendered: list[RenderedFile] = []

    try:
        for output in prepared.outputs:
            source = _base_source(
                output.base.owner,
                output.base.source_path,
                records_by_id,
                prepared.foundation,
            )
            if output.base.source_path.endswith(TEMPLATE_SUFFIX):
                assembled = _assembled_template(
                    output, records_by_id, prepared.foundation
                )
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
            details=single_detail("template-render-failed", str(exc)),
        ) from exc

    return tuple(rendered)
