"""Executable pin for docs/generation-provenance.md (FT-15.02 / ADR 0059).

The contract is only useful if the reference document it describes stays
derivable from the engine. Since FT-17.01 / ADR 0062 shipped the real
generation-metadata surface, these tests drive that surface directly: a real
``library`` render's ``RenderedProject.metadata``, its canonical
serialisation, and ``parse_generation_metadata`` /
``verify_generation_metadata``. They check the ownership map, recorded
identities, digests and field set all agree with what the engine actually
produces, that the two ``EngineErrorCode`` values are shipped and stay in the
``parse`` / ``validate`` band, and that the static fixtures still fail with
the documented code.

Since FT-17.04 / ADR 0065 shipped the real reproducible-render and update
surface, this module also drives ``plan_update`` directly: the reproduction
guarantee across all three archetypes, the five-value classification
vocabulary, ownership/regeneration agreement with the new plan, the
unavailable-historical-provider and tampered-merge-base fail-closed paths,
the decision-2 lenient-recorded-version seam, and rename-window surfacing
against a synthetic fixture catalogue (the shipped catalogue declares no
``[[renames]]`` record).
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

import forge_template.engine as engine_module
from forge_template import (
    DEFAULT_GENERATION_METADATA_TARGET,
    GENERATION_METADATA_VERSION,
    EngineErrorCode,
    ForgeEngineError,
    GenerationMetadata,
    ProjectSpec,
    discover_components,
    get_engine_info,
    parse_generation_metadata,
    parse_project_spec,
    plan_generation,
    plan_update,
    render_project,
    verify_generation_metadata,
)
from tests.generation_provenance_contract import (
    CLASSIFICATIONS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    SKIP_IF_EXISTS,
    digest,
    selected_ids,
)

ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs" / "generation-provenance.md"
COPIER = ROOT / "copier.yml"
FIXTURES = ROOT / "tests" / "fixtures" / "generation_metadata"
_PRODUCTION_COMPONENTS = ROOT / "src" / "forge_template" / "components"
_RENAME_FIXTURE = ROOT / "tests" / "fixtures" / "update_renames" / "renaming-widget"

_RESERVED_CODES = ("invalid-generation-metadata", "unsupported-generation-metadata")

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


def _metadata(spec: ProjectSpec) -> GenerationMetadata:
    document = render_project(spec).metadata
    assert document is not None
    return document


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


def test_render_result_carries_a_metadata_document_that_round_trips() -> None:
    """``render_project`` attaches the document; its canonical JSON parses
    back and verifies against the same render."""
    spec = _reference_spec()
    project = render_project(spec)
    assert project.metadata is not None

    document = json.loads(project.metadata.to_json())
    parsed = parse_generation_metadata(document)
    verify_generation_metadata(parsed, project)

    assert parse_project_spec(parsed.spec).model_dump() == spec.model_dump()
    assert parsed.metadata_version == GENERATION_METADATA_VERSION == 1
    assert DEFAULT_GENERATION_METADATA_TARGET == ".forge/generation.json"


def test_recorded_digests_reproduce_the_render() -> None:
    spec = _reference_spec()
    metadata = _metadata(spec)
    rendered = _rendered(spec)

    assert len(metadata.output) == len(rendered)
    for entry in metadata.output:
        assert entry.digest == digest(rendered[entry.target])


def test_output_ownership_matches_the_plan() -> None:
    """No `output` row claims ownership the engine's plan does not resolve."""
    spec = _reference_spec()
    metadata = _metadata(spec)
    plan = plan_generation(spec)
    expected = {
        item.target: (
            "foundation"
            if item.owner.kind == "foundation"
            else f"component:{item.owner.id}"
        )
        for item in plan.files
    }
    actual = {entry.target: entry.owner for entry in metadata.output}
    assert actual == expected

    regeneration = {entry.target: entry.regeneration for entry in metadata.output}
    planned_regeneration = {item.target: item.regeneration for item in plan.files}
    assert regeneration == planned_regeneration


def test_recorded_identities_are_real() -> None:
    """Provider version, protocol integers and component versions are the
    engine's own, not literals."""
    spec = _reference_spec()
    metadata = _metadata(spec)
    info = get_engine_info()
    catalogue = {c.id: c.version for c in discover_components()}

    assert metadata.provider.distribution == "forge-template"
    assert metadata.provider.version == info.package_version
    assert metadata.protocols.projectspec == spec.protocol_version
    assert metadata.protocols.component_manifest == info.component_manifest_protocols
    recorded = {entry.id: entry.version for entry in metadata.components}
    assert recorded == {cid: catalogue[cid] for cid in selected_ids(spec)}


def test_every_string_leaf_traces_to_an_allowed_source() -> None:
    """The secret-free rule, executable: no string in the serialised document
    is invented -- each comes from the spec, the catalogue, the plan, a
    digest, or the fixed engine identity."""
    spec = _reference_spec()
    metadata = _metadata(spec)
    plan = plan_generation(spec)

    allowed: set[str] = set(_string_leaves(spec.model_dump(mode="json")))
    for component in discover_components():
        allowed |= {component.id, component.version, f"component:{component.id}"}
    allowed |= {item.target for item in plan.files}
    allowed |= {"forge-template", "foundation", get_engine_info().package_version}
    allowed |= {"replace", "skip-if-exists", "exact", "degraded"}

    for leaf in _string_leaves(json.loads(metadata.to_json())):
        if re.fullmatch(r"sha256:[0-9a-f]{64}", leaf):
            continue
        assert leaf in allowed, f"untraceable string leaf: {leaf!r}"


def test_field_table_and_document_are_a_bijection() -> None:
    """A field documented but not built, or built but not documented, fails."""
    documented = _doc_field_table()
    assert documented, "doc field table did not parse"
    assert set(documented) == set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    assert [f for f in documented if f in REQUIRED_FIELDS] == list(REQUIRED_FIELDS)

    built = _metadata(_reference_spec())
    serialised = set(json.loads(built.to_json()))
    # ``reproduction`` is absent on an exact render; every other field present.
    assert serialised == set(REQUIRED_FIELDS)
    assert set(GenerationMetadata.model_fields) == set(REQUIRED_FIELDS) | set(
        OPTIONAL_FIELDS
    )


def test_reserved_error_codes_are_shipped_and_parse_or_validate_only() -> None:
    """The two codes docs/generation-provenance.md reserved are now
    ``EngineErrorCode`` members, and every metadata failure carries
    ``operation`` in ``{parse, validate}`` -- never ``render``."""
    shipped = {code.value for code in EngineErrorCode}
    for reserved in _RESERVED_CODES:
        assert reserved in shipped
        assert reserved in DOC.read_text(encoding="utf-8")

    for name in _STATIC_FIXTURES:
        document = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        with pytest.raises(ForgeEngineError) as caught:
            parse_generation_metadata(document)
        assert caught.value.code.value in _RESERVED_CODES
        assert caught.value.operation in {"parse", "validate"}


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
    with pytest.raises(ForgeEngineError) as caught:
        parse_generation_metadata(document)
    assert (caught.value.code.value, caught.value.operation) == expected


def test_checked_in_baseline_reproduces_a_real_library_render() -> None:
    """example-library.json is a faithful, fully live reference: it parses,
    negotiates, and verifies against a fresh ``library`` render."""
    document = json.loads(
        (FIXTURES / "example-library.json").read_text(encoding="utf-8")
    )
    assert set(document) <= set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    assert set(REQUIRED_FIELDS) <= set(document)

    parsed = parse_generation_metadata(document)
    project = render_project(parse_project_spec(parsed.spec))
    verify_generation_metadata(parsed, project)


def test_live_negatives_are_rejected() -> None:
    spec = _reference_spec()
    project = render_project(spec)
    metadata = project.metadata
    assert metadata is not None
    document = json.loads(metadata.to_json())

    tampered = json.loads(json.dumps(document))
    tampered["output"][0]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(ForgeEngineError) as caught:
        verify_generation_metadata(parse_generation_metadata(tampered), project)
    assert caught.value.code is EngineErrorCode.INVALID_GENERATION_METADATA
    assert caught.value.operation == "validate"

    unknown_component = json.loads(json.dumps(document))
    unknown_component["components"].append({"id": "nonesuch", "version": "1.0.0"})
    with pytest.raises(ForgeEngineError):
        parse_generation_metadata(unknown_component)

    short_output = json.loads(json.dumps(document))
    short_output["output"].pop()
    with pytest.raises(ForgeEngineError):
        verify_generation_metadata(parse_generation_metadata(short_output), project)

    extra_field = json.loads(json.dumps(document))
    extra_field["generated_at"] = "2026-09-10T00:00:00Z"
    with pytest.raises(ForgeEngineError):
        parse_generation_metadata(extra_field)


def _document(project: Any) -> dict[str, Any]:
    """The canonical JSON document, as a plain ``dict`` a test can mutate."""
    metadata = project.metadata
    assert metadata is not None
    document: dict[str, Any] = json.loads(metadata.to_json())
    return document


_ARCHETYPE_PAYLOADS: dict[str, dict[str, Any]] = {
    "library": _REFERENCE_PAYLOAD,
    "cli": {
        **_REFERENCE_PAYLOAD,
        "components": {"archetype": "cli", "capabilities": [], "platforms": []},
        "component_options": {},
    },
    "data-science": {
        **_REFERENCE_PAYLOAD,
        "components": {
            "archetype": "data-science",
            "capabilities": ["jupyter"],
            "platforms": [],
        },
        "component_options": {},
    },
}


@pytest.mark.parametrize("archetype", sorted(_ARCHETYPE_PAYLOADS))
def test_reproduction_is_byte_identical_across_archetypes(archetype: str) -> None:
    """The reproducibility guarantee, proven same-release for all three
    archetypes: render -> attach metadata -> re-render from the embedded spec
    -> byte-identical, and the recorded document verifies against the
    reproduction. Cross-release provisioning is the client's own step
    (CF-16.02), proven against a real released artefact at FT-17.05/FT-18.01."""
    spec = parse_project_spec(_ARCHETYPE_PAYLOADS[archetype])
    original = render_project(spec)
    assert original.metadata is not None

    reproduced_spec = parse_project_spec(original.metadata.spec)
    reproduction = render_project(reproduced_spec)

    original_bytes = {f.target: f.content for f in original.files}
    reproduced_bytes = {f.target: f.content for f in reproduction.files}
    assert reproduced_bytes == original_bytes
    verify_generation_metadata(original.metadata, reproduction)


def test_plan_update_classifies_every_documented_value() -> None:
    """Selecting a capability yields ``added``/``unchanged``; dropping it
    yields ``removed``; a spec identity change yields ``changed``; a repeated
    update with no change yields only ``unchanged`` -- the contract's explicit
    no-op case."""
    library_spec = _reference_spec()
    library = render_project(library_spec)
    assert library.metadata is not None
    recorded = _document(library)
    old_bytes = {f.target: f.content for f in library.files}

    with_jupyter_payload = {
        **_REFERENCE_PAYLOAD,
        "components": {
            "archetype": "library",
            "capabilities": ["jupyter"],
            "platforms": [],
        },
    }
    with_jupyter = render_project(parse_project_spec(with_jupyter_payload))

    added_plan = plan_update(recorded, old=old_bytes, new=with_jupyter)
    added_values = {t.classification for t in added_plan.targets}
    assert added_values <= set(CLASSIFICATIONS)
    assert "added" in added_values
    assert "unchanged" in added_values

    with_jupyter_recorded = _document(with_jupyter)
    with_jupyter_bytes = {f.target: f.content for f in with_jupyter.files}
    removed_plan = plan_update(
        with_jupyter_recorded, old=with_jupyter_bytes, new=library
    )
    assert "removed" in {t.classification for t in removed_plan.targets}

    edited_payload = {
        **_REFERENCE_PAYLOAD,
        "project": {**_REFERENCE_PAYLOAD["project"], "description": "Edited."},
    }
    edited = render_project(parse_project_spec(edited_payload))
    changed_plan = plan_update(recorded, old=old_bytes, new=edited)
    assert "changed" in {t.classification for t in changed_plan.targets}

    noop_plan = plan_update(recorded, old=old_bytes, new=library)
    assert {t.classification for t in noop_plan.targets} == {"unchanged"}
    assert noop_plan.renames == ()
    assert noop_plan.reproduction.mode == "exact"


def test_plan_update_target_ownership_matches_the_new_plan() -> None:
    """No ``UpdateTarget`` claims ownership or a disposition the resolved
    plan does not agree with -- the new plan for a surviving target, the
    recorded document for a removed one."""
    library = render_project(_reference_spec())
    assert library.metadata is not None
    recorded = _document(library)
    old_bytes = {f.target: f.content for f in library.files}

    with_jupyter_payload = {
        **_REFERENCE_PAYLOAD,
        "components": {
            "archetype": "library",
            "capabilities": ["jupyter"],
            "platforms": [],
        },
    }
    with_jupyter_spec = parse_project_spec(with_jupyter_payload)
    with_jupyter = render_project(with_jupyter_spec)
    plan = plan_generation(with_jupyter_spec)
    expected = {
        item.target: (
            "foundation"
            if item.owner.kind == "foundation"
            else f"component:{item.owner.id}"
        )
        for item in plan.files
    }
    expected_regeneration = {item.target: item.regeneration for item in plan.files}

    update = plan_update(recorded, old=old_bytes, new=with_jupyter)
    for entry in update.targets:
        if entry.classification == "removed":
            continue
        assert entry.owner == expected[entry.target]
        assert entry.regeneration == expected_regeneration[entry.target]


def test_plan_update_fails_closed_on_an_unavailable_historical_provider() -> None:
    """An empty ``old`` against a non-empty recorded ``output`` reports the
    ``provider`` axis, the recorded version, and both remedies -- never any
    absolute path or rendered content."""
    library = render_project(_reference_spec())
    assert library.metadata is not None
    recorded = _document(library)

    with pytest.raises(ForgeEngineError) as caught:
        plan_update(recorded, old={}, new=library)
    assert caught.value.code is EngineErrorCode.UNSUPPORTED_GENERATION_METADATA
    assert caught.value.operation == "validate"
    detail = caught.value.details[0]
    assert detail.path == ("provider",)
    assert recorded["provider"]["version"] in detail.message
    assert "provision" in detail.message
    assert "degraded" in detail.message
    assert "\\" not in detail.message
    assert "/" not in detail.message


def test_plan_update_rejects_a_tampered_merge_base() -> None:
    """An ``old`` render whose bytes do not match the recorded digest fails
    ``invalid-generation-metadata`` / ``validate`` -- it did not come from
    this document."""
    library = render_project(_reference_spec())
    assert library.metadata is not None
    recorded = _document(library)
    old_bytes = {f.target: f.content for f in library.files}

    tampered = dict(old_bytes)
    target = next(iter(tampered))
    tampered[target] = tampered[target] + b"tampered"
    with pytest.raises(ForgeEngineError) as caught:
        plan_update(recorded, old=tampered, new=library)
    assert caught.value.code is EngineErrorCode.INVALID_GENERATION_METADATA
    assert caught.value.operation == "validate"

    incomplete = dict(old_bytes)
    del incomplete[next(iter(incomplete))]
    with pytest.raises(ForgeEngineError) as caught:
        plan_update(recorded, old=incomplete, new=library)
    assert caught.value.code is EngineErrorCode.INVALID_GENERATION_METADATA


def test_recorded_component_version_drift_is_lenient_only_on_the_update_path() -> None:
    """The decision-2 seam: ``parse_generation_metadata`` keeps FT-17.01's
    exact recorded-component-version equality (the reproduce path), but
    ``plan_update`` treats a drifted version as expected input -- an update is
    by definition an old document read on a newer engine."""
    library = render_project(_reference_spec())
    assert library.metadata is not None
    recorded = _document(library)
    old_bytes = {f.target: f.content for f in library.files}

    drifted = json.loads(json.dumps(recorded))
    for component in drifted["components"]:
        if component["id"] == "library":
            component["version"] = "999.0.0"

    with pytest.raises(ForgeEngineError) as caught:
        parse_generation_metadata(drifted)
    assert caught.value.code is EngineErrorCode.INVALID_GENERATION_METADATA

    plan = plan_update(drifted, old=old_bytes, new=library)
    assert {t.classification for t in plan.targets} == {"unchanged"}


def test_plan_update_round_trips_a_degraded_reproduction_record() -> None:
    """A refreshed document a client wrote after an opt-in degraded two-way
    update carries ``reproduction.mode == "degraded"`` and still parses; a
    fresh render's document has no ``reproduction`` key at all (exact)."""
    library = render_project(_reference_spec())
    assert library.metadata is not None
    document = _document(library)
    assert "reproduction" not in document

    degraded = json.loads(json.dumps(document))
    degraded["reproduction"] = {
        "mode": "degraded",
        "reason": "historical provider release unavailable",
    }
    parsed = parse_generation_metadata(degraded)
    assert parsed.reproduction is not None
    assert parsed.reproduction.mode == "degraded"
    assert '"mode": "degraded"' in parsed.to_json()


@pytest.fixture
def rename_fixture_catalogue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Overlay the real production catalogue with the synthetic
    ``renaming-widget`` capability, mirroring
    ``tests/test_capability_composition.py``'s ``overlaid_catalogue``: only
    ``_CATALOGUE_ROOT_OVERRIDE`` moves, the real Foundation source stays live.
    """
    root = tmp_path / "catalogue"
    shutil.copytree(_PRODUCTION_COMPONENTS, root)
    shutil.copytree(_RENAME_FIXTURE, root / "renaming-widget")
    monkeypatch.setattr(engine_module, "_CATALOGUE_ROOT_OVERRIDE", root)


def test_plan_update_surfaces_only_in_window_renames(
    rename_fixture_catalogue: None,
) -> None:
    """Only the ``[[renames]]`` record whose ``since`` falls strictly between
    the recorded and installed component version is surfaced; a record at or
    below the recorded version, and one above the installed version, are
    both not."""
    payload = {
        **_REFERENCE_PAYLOAD,
        "components": {
            "archetype": "library",
            "capabilities": ["renaming-widget"],
            "platforms": [],
        },
    }
    spec = parse_project_spec(payload)
    new = render_project(spec)
    assert new.metadata is not None
    recorded = _document(new)
    for component in recorded["components"]:
        if component["id"] == "renaming-widget":
            component["version"] = "1.0.0"
    old_bytes = {f.target: f.content for f in new.files}

    update = plan_update(recorded, old=old_bytes, new=new)
    assert [r.model_dump(by_alias=True) for r in update.renames] == [
        {
            "component_id": "renaming-widget",
            "from": "widget/legacy.txt",
            "to": "widget/renamed.txt",
            "since": "1.1.0",
        }
    ]


def test_skip_if_exists_matches_copier() -> None:
    """The owner-declared never-clobber set is derived from copier.yml, not a
    hand-kept copy."""
    assert set(SKIP_IF_EXISTS) == _copier_skip_if_exists()
