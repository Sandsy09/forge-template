"""Tests for the implicit Foundation content source."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from forge_template.foundation_source import (
    FoundationPlacement,
    FoundationSource,
    foundation_content_order,
    foundation_placement,
    load_foundation_source,
)

FIXTURE = Path(__file__).parent / "fixtures" / "foundation" / "foundation.toml"


def _copy_fixture(tmp_path: Path) -> Path:
    destination = tmp_path / "foundation"
    shutil.copytree(FIXTURE.parent, destination)
    return destination / "foundation.toml"


def test_loads_the_fixture_source() -> None:
    source = load_foundation_source(FIXTURE)

    assert source.foundation_version == 1
    assert source.content_root == "content"
    assert [point.id for point in source.extension_points] == ["pyproject-build-system"]


def test_model_is_strict_and_frozen() -> None:
    source = load_foundation_source(FIXTURE)

    with pytest.raises(ValidationError, match="frozen"):
        source.content_root = "changed"
    with pytest.raises(ValidationError):
        FoundationSource.model_validate(
            {"foundation_version": 1, "content_root": "content", "unexpected": True}
        )


@pytest.mark.parametrize("foundation_version", [None, 2, True])
def test_missing_unsupported_or_coerced_version_is_rejected(
    foundation_version: object,
) -> None:
    payload: dict[str, object] = {"content_root": "content"}
    if foundation_version is not None:
        payload["foundation_version"] = foundation_version

    with pytest.raises(ValidationError):
        FoundationSource.model_validate(payload)


def test_extension_point_content_must_fall_inside_content_root() -> None:
    with pytest.raises(ValidationError, match="must fall inside content_root"):
        FoundationSource.model_validate(
            {
                "foundation_version": 1,
                "content_root": "content",
                "extension_points": [{"id": "x", "content": "outside.jinja"}],
            }
        )


def test_extension_point_identifiers_must_be_unique() -> None:
    with pytest.raises(ValidationError, match="extension point identifiers"):
        FoundationSource.model_validate(
            {
                "foundation_version": 1,
                "content_root": "content",
                "extension_points": [
                    {"id": "x", "content": "content/a.jinja"},
                    {"id": "x", "content": "content/b.jinja"},
                ],
            }
        )


def test_loader_requires_canonical_filename(tmp_path: Path) -> None:
    manifest_path = _copy_fixture(tmp_path)
    renamed = manifest_path.with_name("source.toml")
    manifest_path.rename(renamed)

    with pytest.raises(ValueError, match=r"foundation\.toml"):
        load_foundation_source(renamed)


def test_loader_rejects_missing_empty_and_invalid_resource_types(
    tmp_path: Path,
) -> None:
    missing = _copy_fixture(tmp_path / "missing")
    shutil.rmtree(missing.parent / "content")
    with pytest.raises(FileNotFoundError):
        load_foundation_source(missing)

    empty = _copy_fixture(tmp_path / "empty")
    shutil.rmtree(empty.parent / "content")
    (empty.parent / "content").mkdir()
    with pytest.raises(ValueError, match="content_root is empty"):
        load_foundation_source(empty)

    wrong_type = _copy_fixture(tmp_path / "wrong-type")
    shutil.rmtree(wrong_type.parent / "content")
    (wrong_type.parent / "content").write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        load_foundation_source(wrong_type)


def test_loader_rejects_symlink_escape_when_supported(tmp_path: Path) -> None:
    manifest_path = _copy_fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file.txt").write_text("outside", encoding="utf-8")
    shutil.rmtree(manifest_path.parent / "content")
    try:
        (manifest_path.parent / "content").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("creating directory symlinks is unavailable on this platform")

    # Caught by component_resource_path's own containment check (shared with
    # component_manifest.py) while resolving content_root itself, before this
    # module's own rglob-loop check over content_root's *entries* ever runs --
    # mirrors component_manifest.py's identical test for the identical reason.
    with pytest.raises(ValueError, match="escapes component directory"):
        load_foundation_source(manifest_path)


def test_loader_rejects_missing_extension_point_file(tmp_path: Path) -> None:
    manifest_path = _copy_fixture(tmp_path)
    with manifest_path.open("a", encoding="utf-8") as manifest_file:
        manifest_file.write(
            '\n[[extension_points]]\nid = "absent"\ncontent = "content/absent.jinja"\n'
        )
    with pytest.raises(FileNotFoundError):
        load_foundation_source(manifest_path)


def test_foundation_content_order_is_deterministic_and_relative() -> None:
    assert foundation_content_order(FIXTURE) == ("pyproject.toml.jinja",)


def test_foundation_placement_bundles_source_and_content_order() -> None:
    placement = foundation_placement(FIXTURE)

    assert isinstance(placement, FoundationPlacement)
    assert placement.source == load_foundation_source(FIXTURE)
    assert placement.content_paths == foundation_content_order(FIXTURE)


def test_foundation_placement_is_strict_and_frozen() -> None:
    placement = foundation_placement(FIXTURE)

    with pytest.raises(ValidationError, match="frozen"):
        placement.content_paths = ()
