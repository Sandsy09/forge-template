"""Test-only reference resolver for docs/organisation-policy.md protocol 1.

Mirrors ``tests/composition_contract.py``'s role for ADR 0028: a
downstream-shaped reference implementation kept deliberately out of
``src/forge_template`` so this fixture implies no shipped resolver, no
public export, and no new ``ForgeEngineError`` value. See ADR 0040. It is
never collected by pytest directly (no ``test_`` prefix) and ships in no
package.

Two constraints are deliberate, not incidental:

- Validation is hand-written rather than delegated to pydantic, so the
  *documented* detail codes in organisation-policy.md's "Structured
  failures" section are what actually surfaces, not pydantic's own error
  taxonomy.
- Failures raise this module's own :class:`PolicyError`, never
  ``forge_template.ForgeEngineError`` -- the public error surface stays
  exactly where CLAUDE.md and organisation-policy.md leave it: unchanged
  until a later, shipped implementation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from forge_template import ComponentDescriptor, ComponentSelection

POLICY_VERSION = 1

FIXTURES = Path(__file__).parent / "fixtures" / "organisation_policies"
POLICY_FIXTURES: dict[str, Path] = {
    path.stem: path for path in sorted(FIXTURES.glob("*.json"))
}

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

_TOP_LEVEL_FIELDS = frozenset(
    {"policy_version", "id", "description", "defaults", "required", "forbidden"}
)
_SELECTION_FIELDS = frozenset({"archetype", "capabilities", "platforms"})
_FORBIDDEN_FIELDS = frozenset({"archetypes", "capabilities", "platforms"})


def _is_identifier(value: object) -> bool:
    return isinstance(value, str) and _IDENTIFIER_RE.fullmatch(value) is not None


@dataclass(frozen=True)
class PolicyDetail:
    """One machine-readable failure, mirroring ``EngineErrorDetail``'s shape."""

    code: str
    path: str
    message: str


class PolicyError(Exception):
    """Reference-only failure mirroring organisation-policy.md's three
    categories: ``invalid-organisation-policy``,
    ``organisation-policy-conflict``, ``organisation-policy-violation``.
    """

    def __init__(self, category: str, details: tuple[PolicyDetail, ...]) -> None:
        self.category = category
        self.details = details
        super().__init__(category)


@dataclass(frozen=True)
class Selections:
    """One rule collection (``defaults`` or ``required``) from one policy."""

    archetype: str | None
    capabilities: frozenset[str]
    platforms: frozenset[str]


@dataclass(frozen=True)
class Forbidden:
    """A policy's ``forbidden`` rule collection."""

    archetypes: frozenset[str]
    capabilities: frozenset[str]
    platforms: frozenset[str]


@dataclass(frozen=True)
class Policy:
    """One parsed, wire-valid organisation-policy document."""

    id: str
    description: str
    defaults: Selections
    required: Selections
    forbidden: Forbidden


@dataclass(frozen=True)
class MergedPolicySet:
    """The order-independent union of one or more applied policies."""

    policy_ids: frozenset[str]
    defaults: Selections
    required: Selections
    forbidden: Forbidden


@dataclass(frozen=True)
class ExplicitSelection:
    """What a client explicitly chose, before any default fills a gap.

    ``None`` means "not supplied" (absent, so a default may apply);
    ``frozenset()`` means an explicit but empty choice, which
    organisation-policy.md states "is still an explicit choice" and must
    never be overwritten by a default.
    """

    archetype: str | None = None
    capabilities: frozenset[str] | None = None
    platforms: frozenset[str] | None = None


def _parse_id_set(
    raw: object, path: str, details: list[PolicyDetail]
) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if not isinstance(raw, list):
        details.append(
            PolicyDetail("invalid-field-type", path, f"{path} must be a list")
        )
        return frozenset()
    valid: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not _is_identifier(item):
            details.append(
                PolicyDetail("invalid-field-type", path, f"invalid identifier {item!r}")
            )
            continue
        if item in seen:
            details.append(
                PolicyDetail(
                    "duplicate-selection-id", path, f"duplicate identifier '{item}'"
                )
            )
            continue
        seen.add(item)
        valid.append(item)
    return frozenset(valid)


def parse_policy_document(payload: object, *, source: str) -> Policy:
    """Strictly parse one wire document into a :class:`Policy`.

    Raises :class:`PolicyError` with category ``invalid-organisation-policy``
    and every violation found, not just the first -- matching organisation-
    policy.md's "lexically/path-sorted details" structured-failure shape.
    """
    details: list[PolicyDetail] = []

    if not isinstance(payload, dict):
        details.append(
            PolicyDetail("invalid-field-type", source, f"{source} must be an object")
        )
        raise PolicyError("invalid-organisation-policy", tuple(details))

    unknown = sorted(set(payload) - _TOP_LEVEL_FIELDS)
    for name in unknown:
        details.append(
            PolicyDetail("unknown-field", f"{source}.{name}", f"unknown field '{name}'")
        )

    version = payload.get("policy_version")
    if version != POLICY_VERSION:
        details.append(
            PolicyDetail(
                "unsupported-policy-version",
                f"{source}.policy_version",
                f"unsupported policy_version {version!r}; "
                f"only {POLICY_VERSION} is supported",
            )
        )

    policy_id: object = payload.get("id")
    if not _is_identifier(policy_id):
        details.append(
            PolicyDetail(
                "invalid-policy-id", f"{source}.id", f"invalid policy id {policy_id!r}"
            )
        )

    description: object = payload.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        details.append(
            PolicyDetail(
                "invalid-field-type",
                f"{source}.description",
                "description must be a string",
            )
        )
        description = ""

    def parse_selections(field_name: str) -> Selections:
        raw = payload.get(field_name)
        if raw is None:
            return Selections(None, frozenset(), frozenset())
        if not isinstance(raw, dict):
            details.append(
                PolicyDetail(
                    "invalid-field-type",
                    f"{source}.{field_name}",
                    f"{field_name} must be an object",
                )
            )
            return Selections(None, frozenset(), frozenset())
        for name in sorted(set(raw) - _SELECTION_FIELDS):
            details.append(
                PolicyDetail(
                    "unknown-field",
                    f"{source}.{field_name}.{name}",
                    f"unknown field '{name}'",
                )
            )
        archetype: object = raw.get("archetype")
        resolved_archetype: str | None = None
        if archetype is not None:
            if _is_identifier(archetype):
                resolved_archetype = archetype  # type: ignore[assignment]
            else:
                details.append(
                    PolicyDetail(
                        "invalid-field-type",
                        f"{source}.{field_name}.archetype",
                        f"archetype must be a kebab-case identifier, got {archetype!r}",
                    )
                )
        capabilities = _parse_id_set(
            raw.get("capabilities"), f"{source}.{field_name}.capabilities", details
        )
        platforms = _parse_id_set(
            raw.get("platforms"), f"{source}.{field_name}.platforms", details
        )
        return Selections(resolved_archetype, capabilities, platforms)

    def parse_forbidden() -> Forbidden:
        raw = payload.get("forbidden")
        if raw is None:
            return Forbidden(frozenset(), frozenset(), frozenset())
        if not isinstance(raw, dict):
            details.append(
                PolicyDetail(
                    "invalid-field-type",
                    f"{source}.forbidden",
                    "forbidden must be an object",
                )
            )
            return Forbidden(frozenset(), frozenset(), frozenset())
        for name in sorted(set(raw) - _FORBIDDEN_FIELDS):
            details.append(
                PolicyDetail(
                    "unknown-field",
                    f"{source}.forbidden.{name}",
                    f"unknown field '{name}'",
                )
            )
        return Forbidden(
            _parse_id_set(
                raw.get("archetypes"), f"{source}.forbidden.archetypes", details
            ),
            _parse_id_set(
                raw.get("capabilities"), f"{source}.forbidden.capabilities", details
            ),
            _parse_id_set(
                raw.get("platforms"), f"{source}.forbidden.platforms", details
            ),
        )

    defaults = parse_selections("defaults")
    required = parse_selections("required")
    forbidden = parse_forbidden()

    if (
        defaults.archetype is None
        and not defaults.capabilities
        and not defaults.platforms
        and required.archetype is None
        and not required.capabilities
        and not required.platforms
        and not forbidden.archetypes
        and not forbidden.capabilities
        and not forbidden.platforms
    ):
        details.append(
            PolicyDetail("empty-policy", source, f"{source} declares no rule")
        )

    if details:
        raise PolicyError(
            "invalid-organisation-policy", tuple(sorted(details, key=lambda d: d.path))
        )

    assert isinstance(
        policy_id, str
    )  # narrowed: no invalid-policy-id detail was raised
    return Policy(
        id=policy_id,
        description=description,
        defaults=defaults,
        required=required,
        forbidden=forbidden,
    )


def load_policy(path: Path) -> Policy:
    """Parse one checked-in fixture document from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_policy_document(payload, source=path.stem)


def merge_policies(policies: Sequence[Policy]) -> MergedPolicySet:
    """Merge policies with no caller-order precedence.

    Raises :class:`PolicyError` with category ``organisation-policy-conflict``
    when policies individually valid still contradict one another.
    """
    details: list[PolicyDetail] = []

    seen_ids: set[str] = set()
    for policy in policies:
        if policy.id in seen_ids:
            details.append(
                PolicyDetail(
                    "duplicate-policy-id",
                    policy.id,
                    f"policy id '{policy.id}' applied more than once",
                )
            )
        seen_ids.add(policy.id)

    default_archetypes = {
        p.id: p.defaults.archetype for p in policies if p.defaults.archetype
    }
    required_archetypes = {
        p.id: p.required.archetype for p in policies if p.required.archetype
    }

    distinct_defaults = set(default_archetypes.values())
    if len(distinct_defaults) > 1:
        for policy_id, archetype in sorted(default_archetypes.items()):
            details.append(
                PolicyDetail(
                    "conflicting-archetype-default",
                    policy_id,
                    f"conflicting default archetype '{archetype}'",
                )
            )

    distinct_required = set(required_archetypes.values())
    if len(distinct_required) > 1:
        for policy_id, archetype in sorted(required_archetypes.items()):
            details.append(
                PolicyDetail(
                    "conflicting-archetype-requirement",
                    policy_id,
                    f"conflicting required archetype '{archetype}'",
                )
            )

    merged_default_archetype = (
        next(iter(distinct_defaults)) if len(distinct_defaults) == 1 else None
    )
    merged_required_archetype = (
        next(iter(distinct_required)) if len(distinct_required) == 1 else None
    )

    if (
        merged_default_archetype is not None
        and merged_required_archetype is not None
        and merged_default_archetype != merged_required_archetype
    ):
        details.append(
            PolicyDetail(
                "default-requirement-conflict",
                "archetype",
                f"default archetype '{merged_default_archetype}' differs from "
                f"required archetype '{merged_required_archetype}'",
            )
        )

    merged_default_capabilities = frozenset[str]().union(
        *(p.defaults.capabilities for p in policies)
    )
    merged_default_platforms = frozenset[str]().union(
        *(p.defaults.platforms for p in policies)
    )
    merged_required_capabilities = frozenset[str]().union(
        *(p.required.capabilities for p in policies)
    )
    merged_required_platforms = frozenset[str]().union(
        *(p.required.platforms for p in policies)
    )
    merged_forbidden_archetypes = frozenset[str]().union(
        *(p.forbidden.archetypes for p in policies)
    )
    merged_forbidden_capabilities = frozenset[str]().union(
        *(p.forbidden.capabilities for p in policies)
    )
    merged_forbidden_platforms = frozenset[str]().union(
        *(p.forbidden.platforms for p in policies)
    )

    if (
        merged_default_archetype is not None
        and merged_default_archetype in merged_forbidden_archetypes
    ):
        details.append(
            PolicyDetail(
                "default-forbidden-conflict",
                "archetype",
                f"default archetype '{merged_default_archetype}' is also forbidden",
            )
        )
    if (
        merged_required_archetype is not None
        and merged_required_archetype in merged_forbidden_archetypes
    ):
        details.append(
            PolicyDetail(
                "required-forbidden-conflict",
                "archetype",
                f"required archetype '{merged_required_archetype}' is also forbidden",
            )
        )
    for capability in sorted(
        merged_default_capabilities & merged_forbidden_capabilities
    ):
        details.append(
            PolicyDetail(
                "default-forbidden-conflict",
                f"capabilities.{capability}",
                f"capability '{capability}' is both defaulted and forbidden",
            )
        )
    for platform in sorted(merged_default_platforms & merged_forbidden_platforms):
        details.append(
            PolicyDetail(
                "default-forbidden-conflict",
                f"platforms.{platform}",
                f"platform '{platform}' is both defaulted and forbidden",
            )
        )
    for capability in sorted(
        merged_required_capabilities & merged_forbidden_capabilities
    ):
        details.append(
            PolicyDetail(
                "required-forbidden-conflict",
                f"capabilities.{capability}",
                f"capability '{capability}' is both required and forbidden",
            )
        )
    for platform in sorted(merged_required_platforms & merged_forbidden_platforms):
        details.append(
            PolicyDetail(
                "required-forbidden-conflict",
                f"platforms.{platform}",
                f"platform '{platform}' is both required and forbidden",
            )
        )

    if details:
        raise PolicyError(
            "organisation-policy-conflict", tuple(sorted(details, key=lambda d: d.path))
        )

    return MergedPolicySet(
        policy_ids=frozenset(seen_ids),
        defaults=Selections(
            merged_default_archetype,
            merged_default_capabilities,
            merged_default_platforms,
        ),
        required=Selections(
            merged_required_archetype,
            merged_required_capabilities,
            merged_required_platforms,
        ),
        forbidden=Forbidden(
            merged_forbidden_archetypes,
            merged_forbidden_capabilities,
            merged_forbidden_platforms,
        ),
    )


def _check_component(
    component_id: str,
    expected_kind: str,
    path: str,
    by_id: Mapping[str, str],
    details: list[PolicyDetail],
) -> None:
    kind = by_id.get(component_id)
    if kind is None:
        details.append(
            PolicyDetail(
                "unknown-component", path, f"unknown component '{component_id}'"
            )
        )
    elif kind != expected_kind:
        details.append(
            PolicyDetail(
                "component-kind-mismatch",
                path,
                f"'{component_id}' is kind '{kind}', expected '{expected_kind}'",
            )
        )


def resolve_selection(
    merged: MergedPolicySet,
    *,
    explicit: ExplicitSelection,
    catalogue: Sequence[ComponentDescriptor],
    profile_default_archetype: str | None = None,
    profile_default_capabilities: frozenset[str] = frozenset(),
    profile_default_platforms: frozenset[str] = frozenset(),
) -> ComponentSelection:
    """Resolve one effective selection under the documented authority order.

    ``profile default < merged organisation-policy default < explicit user
    choice < required/forbidden organisation constraint`` -- required and
    forbidden rules only validate the result; they never add, remove, or
    replace an explicit selection. Raises :class:`PolicyError` with category
    ``organisation-policy-violation`` on a validation failure. On success,
    returns a real ``forge_template.ComponentSelection`` -- proving the
    reference resolver's output is directly ProjectSpec-shaped, not an
    approximation of it.
    """
    details: list[PolicyDetail] = []
    by_id = {descriptor.id: descriptor.kind for descriptor in catalogue}

    archetype: str | None
    if explicit.archetype is not None:
        archetype = explicit.archetype
    elif merged.defaults.archetype is not None:
        archetype = merged.defaults.archetype
    else:
        archetype = profile_default_archetype

    capabilities: frozenset[str]
    if explicit.capabilities is not None:
        capabilities = explicit.capabilities
    elif merged.defaults.capabilities:
        capabilities = merged.defaults.capabilities
    else:
        capabilities = profile_default_capabilities

    platforms: frozenset[str]
    if explicit.platforms is not None:
        platforms = explicit.platforms
    elif merged.defaults.platforms:
        platforms = merged.defaults.platforms
    else:
        platforms = profile_default_platforms

    if archetype is None:
        details.append(
            PolicyDetail(
                "no-permitted-archetype",
                "archetype",
                "no archetype selection is available",
            )
        )
    else:
        _check_component(archetype, "archetype", "archetype", by_id, details)

    for capability in sorted(capabilities):
        _check_component(
            capability, "capability", f"capabilities.{capability}", by_id, details
        )
    for platform in sorted(platforms):
        _check_component(platform, "platform", f"platforms.{platform}", by_id, details)

    if merged.required.archetype is not None and merged.required.archetype != archetype:
        details.append(
            PolicyDetail(
                "required-selection-missing",
                "archetype",
                f"required archetype '{merged.required.archetype}' is not selected",
            )
        )
    for capability in sorted(merged.required.capabilities - capabilities):
        details.append(
            PolicyDetail(
                "required-selection-missing",
                f"capabilities.{capability}",
                f"required capability '{capability}' is not selected",
            )
        )
    for platform in sorted(merged.required.platforms - platforms):
        details.append(
            PolicyDetail(
                "required-selection-missing",
                f"platforms.{platform}",
                f"required platform '{platform}' is not selected",
            )
        )

    if archetype is not None and archetype in merged.forbidden.archetypes:
        details.append(
            PolicyDetail(
                "forbidden-selection-selected",
                "archetype",
                f"forbidden archetype '{archetype}' is selected",
            )
        )
    for capability in sorted(capabilities & merged.forbidden.capabilities):
        details.append(
            PolicyDetail(
                "forbidden-selection-selected",
                f"capabilities.{capability}",
                f"forbidden capability '{capability}' is selected",
            )
        )
    for platform in sorted(platforms & merged.forbidden.platforms):
        details.append(
            PolicyDetail(
                "forbidden-selection-selected",
                f"platforms.{platform}",
                f"forbidden platform '{platform}' is selected",
            )
        )

    if details:
        raise PolicyError(
            "organisation-policy-violation",
            tuple(sorted(details, key=lambda d: d.path)),
        )

    assert archetype is not None  # no-permitted-archetype would have raised above
    return ComponentSelection(
        archetype=archetype,
        capabilities=tuple(sorted(capabilities)),
        platforms=tuple(sorted(platforms)),
    )
