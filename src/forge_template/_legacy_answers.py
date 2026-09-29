"""The released Copier Library answer mapping (private engine module).

ADR 0079. Implements the table documented by
docs/library-archetype.md#legacy-copier-answer-mapping. Pure: it takes a plain
answer mapping and returns a plain option mapping.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from forge_template._errors import EngineErrorCode, ForgeEngineError, single_detail

_LEGACY_PACKAGING_MODE: dict[tuple[str, str], str] = {
    ("uv_build", "static"): "uv-build-static",
    ("hatchling", "static"): "hatchling-static",
    ("hatchling", "vcs"): "hatchling-vcs",
}
"""The documented FT-08.02 legacy-answer mapping
(docs/library-archetype.md#legacy-copier-answer-mapping): every
``build_backend``/resolved-``versioning`` pair the released Copier scaffold
can produce, keyed exactly as ``map_legacy_library_answers`` receives them."""


def _invalid(detail_code: str, message: str) -> ForgeEngineError:
    return ForgeEngineError(
        code=EngineErrorCode.INVALID_COMPONENT_OPTIONS,
        operation="map-legacy-answers",
        message="Legacy Library answers are invalid.",
        details=single_detail(detail_code, message),
    )


def map_answers(answers: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """See :func:`forge_template.map_legacy_library_answers`."""
    unknown = sorted(set(answers) - {"build_backend", "versioning_resolved"})
    if unknown:
        msg = f"unexpected legacy Library answer(s): {', '.join(unknown)}"
        raise _invalid("unexpected-legacy-answer", msg)

    missing = sorted({"build_backend", "versioning_resolved"} - set(answers))
    if missing:
        msg = f"missing legacy Library answer(s): {', '.join(missing)}"
        raise _invalid("missing-legacy-answer", msg)

    build_backend = answers["build_backend"]
    versioning_resolved = answers["versioning_resolved"]
    if not isinstance(build_backend, str) or not isinstance(versioning_resolved, str):
        msg = (
            "legacy Library answers must be strings: "
            f"build_backend={build_backend!r}, "
            f"versioning_resolved={versioning_resolved!r}"
        )
        raise _invalid("invalid-legacy-answer-type", msg)

    packaging_mode = _LEGACY_PACKAGING_MODE.get((build_backend, versioning_resolved))
    if packaging_mode is None:
        msg = (
            "unsupported legacy Library answer combination: "
            f"build_backend={build_backend!r}, "
            f"versioning_resolved={versioning_resolved!r}"
        )
        raise _invalid("unsupported-legacy-answer-combination", msg)
    return {"packaging_mode": packaging_mode}
