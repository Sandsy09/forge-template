"""The engine's structured error type (private; import from the package).

ADR 0079: ``EngineErrorCode``, ``EngineErrorDetail`` and ``ForgeEngineError``
are re-exported unchanged by the facade. The helpers below build the details
every private engine module attaches to a failure.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import JsonValue, ValidationError

from forge_template._models import _PublicModel


class EngineErrorCode(StrEnum):
    """Stable machine-readable categories for expected engine failures."""

    INVALID_PROJECT_SPEC = "invalid-project-spec"
    COMPONENT_DISCOVERY_FAILED = "component-discovery-failed"
    INVALID_COMPONENT_SELECTION = "invalid-component-selection"
    INVALID_COMPONENT_OPTIONS = "invalid-component-options"
    GENERATION_PLAN_FAILED = "generation-plan-failed"
    TEMPLATE_RENDER_FAILED = "template-render-failed"
    GENERATED_PROJECT_INVALID = "generated-project-invalid"
    INVALID_GENERATION_METADATA = "invalid-generation-metadata"
    UNSUPPORTED_GENERATION_METADATA = "unsupported-generation-metadata"


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


def validation_details(exc: ValidationError) -> tuple[EngineErrorDetail, ...]:
    return tuple(
        EngineErrorDetail(
            code=str(error["type"]),
            path=tuple(error["loc"]),
            message=str(error["msg"]),
        )
        for error in exc.errors()
    )


def single_detail(code: str, message: str) -> tuple[EngineErrorDetail, ...]:
    return (EngineErrorDetail(code=code, message=message),)


def metadata_error(
    code: EngineErrorCode,
    operation: Literal["parse", "validate"],
    path: tuple[str | int, ...],
    message: str,
) -> ForgeEngineError:
    """One structured generation-metadata failure, never ``operation="render"``."""
    return ForgeEngineError(
        code=code,
        operation=operation,
        message=message,
        details=(EngineErrorDetail(code=code.value, path=path, message=message),),
    )


def detail_sort_key(
    detail: EngineErrorDetail,
) -> tuple[tuple[str, ...], str, str]:
    return tuple(str(part) for part in detail.path), detail.code, detail.message
