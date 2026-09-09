"""Executable pin for docs/generation-provenance.md (FT-15.02 / ADR 0059).

The contract is only useful if the reference document it describes stays
derivable from the engine. These tests build a real generation-metadata
document for a ``library`` render through the public facade and check that its
ownership map, recorded identities, digests and field set all agree with what
the engine actually produces -- and that the two ``EngineErrorCode`` values
the contract reserves are still absent from the shipped enum, so this file
fails deliberately when FT-17.01 adds them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from forge_template import (
    EngineErrorCode,
    ProjectSpec,
    discover_components,
    get_engine_info,
    parse_project_spec,
    plan_generation,
    render_project,
)
from tests.generation_provenance_contract import (
    CLASSIFICATIONS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    RESERVED_ERROR_CODES,
    SKIP_IF_EXISTS,
    MetadataError,
    RenameRecord,
    build_metadata,
    classify_update,
    digest,
    selected_ids,
    validate_metadata,
)

ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs" / "generation-provenance.md"
COPIER = ROOT / "copier.yml"
FIXTURES = ROOT / "tests" / "fixtures" / "generation_metadata"

_REFERENCE_PAYLOAD: dict[str, Any] = {
    "protocol_version": 1,
    "project": {
        "name": "Reference Project",
        "package_name": "refproj",
        "repository_name": "reference-project",
        "description": "Generation-provenance inventory fixture.",
        "licence": "mit",
        "authors": [{"name": "Test User", "email": "test@example.com"}],
    },
    "python": {"minimum": "3.11", "development": "3.13"},
    "components": {"archetype": "library", "capabilities": [], "platforms": []},
    "component_options": {
        "library": {"packaging_mode": "uv-build-static", "initial_version": "0.1.0"}
    },
}


def _reference_spec() -> ProjectSpec:
    return parse_project_spec(_REFERENCE_PAYLOAD)


def _rendered(spec: ProjectSpec) -> dict[str, bytes]:
    return {item.target: item.content for item in render_project(spec).files}


def _string_leaves(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _string_leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _string_leaves(item)]
    return []


def _doc_field_table() -> list[str]:
    """The `field` keys from the doc's metadata-document table."""
    text = DOC.read_text(encoding="utf-8")
    start = text.index("## The generation metadata document")
    end = text.index("### `output` entries", start)
    return re.findall(r"(?m)^\|\s*`([a-z_]+)`\s*\|", text[start:end])


def _copier_skip_if_exists() -> set[str]:
    text = COPIER.read_text(encoding="utf-8")
    block = re.search(r"(?m)^_skip_if_exists:\n((?:\s+-\s+.+\n)+)", text)
    assert block is not None, "copier.yml has no _skip_if_exists block"
    return set(re.findall(r"-\s+(\S+)", block.group(1)))


def test_reference_document_validates_and_reproduces_its_digests() -> None:
    """A freshly built document round-trips: validation reproduces the render
    and every recorded digest matches."""
    spec = _reference_spec()
    document = build_metadata(spec)

    returned = validate_metadata(document)
    assert returned.model_dump() == spec.model_dump()

    rendered = _rendered(spec)
    assert len(document["output"]) == len(rendered)
    for entry in document["output"]:
        assert entry["digest"] == digest(rendered[entry["target"]])


def test_output_ownership_matches_the_plan() -> None:
    """No `output` row claims ownership the engine's plan does not resolve."""
    spec = _reference_spec()
    document = build_metadata(spec)
    plan = plan_generation(spec)
    expected = {
        item.target: (
            "foundation"
            if item.owner.kind == "foundation"
            else f"component:{item.owner.id}"
        )
        for item in plan.files
    }
    actual = {row["target"]: row["owner"] for row in document["output"]}
    assert actual == expected


def test_recorded_identities_are_real() -> None:
    """Provider version, protocol integers and component versions are the
    engine's own, not literals."""
    spec = _reference_spec()
    document = build_metadata(spec)
    info = get_engine_info()
    catalogue = {c.id: c.version for c in discover_components()}

    assert document["provider"] == {
        "distribution": "forge-template",
        "version": info.package_version,
    }
    assert document["protocols"]["projectspec"] == spec.protocol_version
    assert document["protocols"]["component_manifest"] == list(
        info.component_manifest_protocols
    )
    recorded = {entry["id"]: entry["version"] for entry in document["components"]}
    assert recorded == {cid: catalogue[cid] for cid in selected_ids(spec)}


def test_every_string_leaf_traces_to_an_allowed_source() -> None:
    """The secret-free rule, executable: no string in the serialised document
    is invented -- each comes from the spec, the catalogue, the plan, a
    digest, or the fixed engine identity."""
    spec = _reference_spec()
    document = build_metadata(spec, reproduction="degraded", reason="release yanked")
    plan = plan_generation(spec)

    allowed: set[str] = set(_string_leaves(spec.model_dump(mode="json")))
    for component in discover_components():
        allowed |= {component.id, component.version, f"component:{component.id}"}
    allowed |= {item.target for item in plan.files}
    allowed |= {"forge-template", "foundation", get_engine_info().package_version}
    allowed |= {"replace", "skip-if-exists", "exact", "degraded", "release yanked"}

    for leaf in _string_leaves(document):
        if re.fullmatch(r"sha256:[0-9a-f]{64}", leaf):
            continue
        assert leaf in allowed, f"untraceable string leaf: {leaf!r}"


def test_field_table_and_document_are_a_bijection() -> None:
    """A field documented but not built, or built but not documented, fails."""
    documented = _doc_field_table()
    assert documented, "doc field table did not parse"
    assert set(documented) == set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    assert [f for f in documented if f in REQUIRED_FIELDS] == list(REQUIRED_FIELDS)


def test_reserved_error_codes_are_not_yet_in_the_shipped_enum() -> None:
    """Tripwire: this fails when FT-17.01 adds the codes, forcing the contract
    and the implementation back into step."""
    shipped = {code.value for code in EngineErrorCode}
    for reserved in RESERVED_ERROR_CODES:
        assert reserved not in shipped, (
            f"{reserved!r} is now shipped -- update docs/generation-provenance.md "
            "and tests/generation_provenance_contract.py to use EngineErrorCode"
        )
    text = DOC.read_text(encoding="utf-8")
    for reserved in RESERVED_ERROR_CODES:
        assert reserved in text


_STATIC_FIXTURES = {
    "example-not-an-object.json": ("invalid-generation-metadata", "parse"),
    "example-unsupported-metadata-version.json": (
        "unsupported-generation-metadata",
        "validate",
    ),
    "example-missing-provider.json": ("invalid-generation-metadata", "validate"),
    "example-malformed-provider.json": ("invalid-generation-metadata", "validate"),
    "example-unsupported-projectspec-protocol.json": (
        "unsupported-generation-metadata",
        "validate",
    ),
}


@pytest.mark.parametrize(("name", "expected"), sorted(_STATIC_FIXTURES.items()))
def test_static_fixtures_fail_with_the_documented_code(
    name: str, expected: tuple[str, str]
) -> None:
    document = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    with pytest.raises(MetadataError) as caught:
        validate_metadata(document)
    assert (caught.value.code, caught.value.operation) == expected


def test_checked_in_baseline_is_a_faithful_shape_reference() -> None:
    """example-library.json need not carry live digests, but its structure,
    targets and identities must still be real."""
    document = json.loads(
        (FIXTURES / "example-library.json").read_text(encoding="utf-8")
    )
    assert set(document) <= set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    assert set(REQUIRED_FIELDS) <= set(document)

    spec = parse_project_spec(document["spec"])
    targets = set(_rendered(spec))
    catalogue = {c.id: c.version for c in discover_components()}
    for entry in document["output"]:
        assert entry["target"] in targets
        owner = entry["owner"]
        assert owner == "foundation" or owner.removeprefix("component:") in catalogue
        assert entry["regeneration"] in {"replace", "skip-if-exists"}
    for entry in document["components"]:
        assert catalogue.get(entry["id"]) == entry["version"]


def test_live_negatives_are_rejected() -> None:
    spec = _reference_spec()

    tampered = build_metadata(spec)
    tampered["output"][0]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(MetadataError) as caught:
        validate_metadata(tampered)
    assert caught.value.code == "invalid-generation-metadata"
    assert caught.value.operation == "validate"

    unknown_component = build_metadata(spec)
    unknown_component["components"].append({"id": "nonesuch", "version": "1.0.0"})
    with pytest.raises(MetadataError):
        validate_metadata(unknown_component)

    short_output = build_metadata(spec)
    short_output["output"].pop()
    with pytest.raises(MetadataError):
        validate_metadata(short_output)

    extra_field = build_metadata(spec)
    extra_field["generated_at"] = "2026-09-09T00:00:00Z"
    with pytest.raises(MetadataError):
        validate_metadata(extra_field)


def test_classify_update_uses_only_the_documented_vocabulary() -> None:
    library = _rendered(_reference_spec())
    with_jupyter_payload = {
        **_REFERENCE_PAYLOAD,
        "components": {
            "archetype": "library",
            "capabilities": ["jupyter"],
            "platforms": [],
        },
    }
    with_jupyter = _rendered(parse_project_spec(with_jupyter_payload))

    classified = classify_update(library, with_jupyter)
    assert set(classified.values()) <= set(CLASSIFICATIONS)
    assert "added" in classified.values()
    assert "unchanged" in classified.values()

    old = {"src/refproj/old_name.py": b"x", "keep.py": b"k"}
    new = {"src/refproj/new_name.py": b"x", "keep.py": b"k"}
    record = RenameRecord("src/refproj/old_name.py", "src/refproj/new_name.py", "2.0.0")
    renamed = classify_update(old, new, [record])
    assert renamed["src/refproj/new_name.py"] == "renamed"
    assert renamed["keep.py"] == "unchanged"
    assert "src/refproj/old_name.py" not in renamed


def test_skip_if_exists_matches_copier() -> None:
    """The owner-declared never-clobber set is derived from copier.yml, not a
    hand-kept copy."""
    assert set(SKIP_IF_EXISTS) == _copier_skip_if_exists()
