"""The single place tests reach the engine's private, test-only seams.

FT-25.01 / ADR 0079. The catalogue and Foundation root overrides (and the
catalogue loader ``get_engine_info`` must never call) are deliberately
private: clients cannot redirect discovery to arbitrary content. Tests used
to patch them directly on ``forge_template.engine`` in a dozen modules; they
now go through this module, which is how FT-25.02 moved them into the private
``forge_template._discovery`` by changing one line -- :data:`SEAM_MODULE`.

Nothing here is a supported API, and nothing outside ``tests/`` may use it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Final

import forge_template._discovery as SEAM_MODULE  # noqa: N812

if TYPE_CHECKING:
    import pytest

__all__ = [
    "SEAM_MODULE",
    "UNCHANGED",
    "overridden_sources",
    "override_sources",
    "replace_catalogue_loader",
]


class _Unchanged(Enum):
    TOKEN = "unchanged"


UNCHANGED: Final = _Unchanged.TOKEN
"""Leave that override as it is (distinct from ``None``, which clears it)."""

_CATALOGUE = "_CATALOGUE_ROOT_OVERRIDE"
_FOUNDATION = "_FOUNDATION_ROOT_OVERRIDE"
_LOADER = "load_catalogue"


def _module() -> ModuleType:
    return SEAM_MODULE


def override_sources(
    monkeypatch: pytest.MonkeyPatch,
    *,
    catalogue: Path | _Unchanged | None = UNCHANGED,
    foundation: Path | _Unchanged | None = UNCHANGED,
) -> None:
    """Point discovery at a fixture catalogue and/or Foundation root.

    ``None`` restores the installed source for that axis; :data:`UNCHANGED`
    leaves it alone. Undone automatically by ``monkeypatch``.
    """
    if not isinstance(catalogue, _Unchanged):
        monkeypatch.setattr(_module(), _CATALOGUE, catalogue)
    if not isinstance(foundation, _Unchanged):
        monkeypatch.setattr(_module(), _FOUNDATION, foundation)


@contextmanager
def overridden_sources(
    *, catalogue: Path | None, foundation: Path | None
) -> Iterator[None]:
    """:func:`override_sources` for callers without a ``monkeypatch``.

    Restores the previous values even when the body raises.
    """
    module = _module()
    previous = (getattr(module, _CATALOGUE), getattr(module, _FOUNDATION))
    setattr(module, _CATALOGUE, catalogue)
    setattr(module, _FOUNDATION, foundation)
    try:
        yield
    finally:
        setattr(module, _CATALOGUE, previous[0])
        setattr(module, _FOUNDATION, previous[1])


def replace_catalogue_loader(
    monkeypatch: pytest.MonkeyPatch, loader: Callable[[], object]
) -> None:
    """Replace the private catalogue loader, e.g. to prove it is never called."""
    monkeypatch.setattr(_module(), _LOADER, loader)
