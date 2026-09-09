"""Test-only reference builder and validator for docs/generation-provenance.md.

Mirrors ``tests/organisation_policy_contract.py``'s role for ADR 0040: a
downstream-shaped reference kept deliberately out of ``src/forge_template`` so
this fixture implies no shipped provenance model, no public export, and no new
``ForgeEngineError`` value. See ADR 0059. It is never collected by pytest
directly (no ``test_`` prefix) and ships in no package.

Two constraints are deliberate:

- The builder assembles a generation-metadata document from the public
  ``forge_template`` facade only -- ``get_engine_info``, ``discover_components``,
  ``plan_generation``, ``render_project`` -- so the document can never claim
  something the engine does not itself resolve.
- Failures raise this module's own :class:`MetadataError`, never
  ``forge_template.ForgeEngineError``. The public error surface stays exactly
  where FT-15.02's exclusions leave it: the two ``EngineErrorCode`` values the
  contract reserves are FT-17.01's to add, and this module keeps them as plain
  strings so ``tests/test_generation_provenance.py`` can assert they are still
  absent from the shipped enum.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from forge_template import (
    ForgeEngineError,
    ProjectSpec,
    discover_components,
    get_engine_info,
    parse_project_spec,
    plan_generation,
    render_project,
)

METADATA_VERSION = 1

#: The two ``EngineErrorCode`` values docs/generation-provenance.md reserves
#: for FT-17.01. Held as plain strings on purpose -- they are not in the
#: shipped enum yet.
INVALID_METADATA = "invalid-generation-metadata"
UNSUPPORTED_METADATA = "unsupported-generation-metadata"
RESERVED_ERROR_CODES = (INVALID_METADATA, UNSUPPORTED_METADATA)

_DISTRIBUTION = "forge-template"
_FOUNDATION = "foundation"
_REGENERATION_MODES = ("replace", "skip-if-exists")
_REPRODUCTION_MODES = ("exact", "degraded")

#: The documented update classification vocabulary.
CLASSIFICATIONS = ("unchanged", "added", "removed", "changed", "renamed")

#: ``copier.yml``'s ``_skip_if_exists``, restated as the owner-declared
#: disposition until a manifest field carries it (FT-17.01).
SKIP_IF_EXISTS = frozenset({"CHANGELOG.md", ".env"})

#: The persisted document's top-level fields; ``reproduction`` is optional.
REQUIRED_FIELDS = (
    "metadata_version",
    "provider",
    "protocols",
    "spec",
    "components",
    "output",
)
OPTIONAL_FIELDS = ("reproduction",)


class MetadataError(Exception):
    """Reference-only failure mirroring ``EngineErrorDetail``'s shape.

    ``code`` is one of :data:`RESERVED_ERROR_CODES`; ``operation`` is
    ``"parse"`` or ``"validate"``, never ``"render"``.
    """

    def __init__(
        self,
        *,
        code: str,
        operation: str,
        path: tuple[str | int, ...],
        message: str,
    ) -> None:
        self.code = code
        self.operation = operation
        self.path = path
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class RenameRecord:
    """One owner-declared ``{ from, to, since }`` migration pair."""

    source: str
    target: str
    since: str


def digest(content: bytes) -> str:
    """The ``sha256:<hex>`` form the ``output`` entries record."""
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _owner_token(owner: Any) -> str:
    if owner.kind == _FOUNDATION:
        return _FOUNDATION
    return f"component:{owner.id}"


def selected_ids(spec: ProjectSpec) -> tuple[str, ...]:
    """Every selected component id: archetype, then capabilities, platforms."""
    return (
        spec.components.archetype,
        *spec.components.capabilities,
        *spec.components.platforms,
    )


def build_metadata(
    spec: ProjectSpec,
    *,
    reproduction: str = "exact",
    reason: str = "",
) -> dict[str, Any]:
    """Assemble a generation-metadata document for ``spec``.

    Everything comes from the public facade: the engine identity, the
    catalogue, the resolved plan, and the rendered bytes.
    """
    if reproduction not in _REPRODUCTION_MODES:
        msg = f"unknown reproduction mode {reproduction!r}"
        raise MetadataError(
            code=INVALID_METADATA,
            operation="validate",
            path=("reproduction", "mode"),
            message=msg,
        )

    info = get_engine_info()
    catalogue = {component.id: component for component in discover_components()}
    plan = plan_generation(spec)
    rendered = {item.target: item.content for item in render_project(spec).files}
    owners = {item.target: _owner_token(item.owner) for item in plan.files}

    components: list[dict[str, str]] = []
    for component_id in selected_ids(spec):
        descriptor = catalogue.get(component_id)
        if descriptor is None:
            msg = f"selected component {component_id!r} is not in the catalogue"
            raise MetadataError(
                code=INVALID_METADATA,
                operation="validate",
                path=("components",),
                message=msg,
            )
        components.append({"id": component_id, "version": descriptor.version})

    output: list[dict[str, str]] = []
    for target in sorted(rendered):
        base = target.rsplit("/", 1)[-1]
        regeneration = "skip-if-exists" if base in SKIP_IF_EXISTS else "replace"
        output.append(
            {
                "target": target,
                "owner": owners[target],
                "digest": digest(rendered[target]),
                "regeneration": regeneration,
            }
        )

    document: dict[str, Any] = {
        "metadata_version": METADATA_VERSION,
        "provider": {"distribution": _DISTRIBUTION, "version": info.package_version},
        "protocols": {
            "projectspec": spec.protocol_version,
            "component_manifest": list(info.component_manifest_protocols),
        },
        "spec": spec.model_dump(mode="json"),
        "components": components,
        "output": output,
    }
    if reproduction != "exact":
        document["reproduction"] = {"mode": reproduction, "reason": reason}
    return document


def _fail(
    code: str,
    operation: str,
    path: tuple[str | int, ...],
    message: str,
) -> MetadataError:
    return MetadataError(code=code, operation=operation, path=path, message=message)


def validate_metadata(document: object) -> ProjectSpec:
    """Validate a metadata document, returning the reproduced effective spec.

    Raises :class:`MetadataError` -- never ``ForgeEngineError`` -- for a
    malformed, inconsistent, or unsupported document.
    """
    if not isinstance(document, Mapping):
        raise _fail(INVALID_METADATA, "parse", (), "document is not an object")

    version = document.get("metadata_version")
    if version != METADATA_VERSION:
        raise _fail(
            UNSUPPORTED_METADATA,
            "validate",
            ("metadata_version",),
            f"unsupported metadata_version {version!r}",
        )

    missing = [field for field in REQUIRED_FIELDS if field not in document]
    if missing:
        raise _fail(
            INVALID_METADATA,
            "validate",
            (missing[0],),
            f"required field {missing[0]!r} is missing",
        )
    unknown = set(document) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
    if unknown:
        raise _fail(
            INVALID_METADATA,
            "validate",
            (sorted(unknown)[0],),
            f"unknown field {sorted(unknown)[0]!r}",
        )

    provider = document["provider"]
    if (
        not isinstance(provider, Mapping)
        or provider.get("distribution") != _DISTRIBUTION
        or not isinstance(provider.get("version"), str)
        or not provider["version"]
    ):
        raise _fail(
            INVALID_METADATA,
            "validate",
            ("provider",),
            "provider identity is malformed",
        )

    protocols = document["protocols"]
    if not isinstance(protocols, Mapping) or not isinstance(
        protocols.get("projectspec"), int
    ):
        raise _fail(
            INVALID_METADATA, "validate", ("protocols",), "protocols block is malformed"
        )
    if protocols["projectspec"] not in get_engine_info().projectspec_protocols:
        raise _fail(
            UNSUPPORTED_METADATA,
            "validate",
            ("protocols", "projectspec"),
            f"unsupported ProjectSpec protocol {protocols['projectspec']!r}",
        )

    try:
        spec = parse_project_spec(document["spec"])
    except ForgeEngineError as exc:
        raise _fail(
            INVALID_METADATA, "validate", ("spec",), "embedded spec does not parse"
        ) from exc

    catalogue = {component.id: component for component in discover_components()}
    components = document["components"]
    if not isinstance(components, Sequence) or isinstance(components, str | bytes):
        raise _fail(
            INVALID_METADATA, "validate", ("components",), "components is not a list"
        )
    for index, entry in enumerate(components):
        entry_id = entry.get("id") if isinstance(entry, Mapping) else None
        descriptor = catalogue.get(entry_id) if isinstance(entry_id, str) else None
        if descriptor is None or not isinstance(entry, Mapping):
            raise _fail(
                INVALID_METADATA,
                "validate",
                ("components", index),
                "entry names a component the catalogue does not have",
            )
        if entry.get("version") != descriptor.version:
            raise _fail(
                INVALID_METADATA,
                "validate",
                ("components", index),
                "recorded component version does not match the catalogue",
            )

    rendered = {item.target: item.content for item in render_project(spec).files}
    covered: set[str] = set()
    entries = document["output"]
    if not isinstance(entries, Sequence) or isinstance(entries, str | bytes):
        raise _fail(INVALID_METADATA, "validate", ("output",), "output is not a list")
    for index, item in enumerate(entries):
        if not isinstance(item, Mapping):
            raise _fail(
                INVALID_METADATA,
                "validate",
                ("output", index),
                "entry is not an object",
            )
        target = item.get("target")
        if not isinstance(target, str) or target not in rendered:
            raise _fail(
                INVALID_METADATA,
                "validate",
                ("output", index),
                f"entry names an unrendered target {target!r}",
            )
        if item.get("regeneration") not in _REGENERATION_MODES:
            raise _fail(
                INVALID_METADATA,
                "validate",
                ("output", index, "regeneration"),
                "unknown regeneration disposition",
            )
        if item.get("digest") != digest(rendered[target]):
            raise _fail(
                INVALID_METADATA,
                "validate",
                ("output", target),
                "digest does not match a reproduced target",
            )
        covered.add(target)
    if covered != set(rendered):
        raise _fail(
            INVALID_METADATA,
            "validate",
            ("output",),
            "output does not cover every rendered target",
        )

    reproduction = document.get("reproduction")
    if reproduction is not None and (
        not isinstance(reproduction, Mapping)
        or reproduction.get("mode") not in _REPRODUCTION_MODES
    ):
        raise _fail(
            INVALID_METADATA,
            "validate",
            ("reproduction",),
            "reproduction block is malformed",
        )

    return spec


def classify_update(
    old: Mapping[str, bytes],
    new: Mapping[str, bytes],
    renames: Sequence[RenameRecord] = (),
) -> dict[str, str]:
    """Classify each target across an old/new render pair.

    Every value is one of :data:`CLASSIFICATIONS`. Renames are applied first,
    so a moved-and-edited file is reported once, as ``renamed``.
    """
    moved = {record.source: record.target for record in renames}
    result: dict[str, str] = {}
    for source, destination in moved.items():
        if source in old and destination in new:
            result[destination] = "renamed"
    for target in old.keys() | new.keys():
        if target in result or target in moved:
            continue
        if target in old and target in new:
            result[target] = "unchanged" if old[target] == new[target] else "changed"
        elif target in new:
            result[target] = "added"
        else:
            result[target] = "removed"
    return result
