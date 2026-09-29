"""A minimal, standalone independent engine client -- FT-25.03.

Run by ``tests/test_decomposed_engine_pairing.py`` with the interpreter of a
clean virtual environment that has exactly one ``forge-template`` installed
(the candidate wheel, its sdist build, or the published ``0.6.0`` wheel). It
imports nothing but the standard library and the top-level ``forge_template``
package -- no repository file, no private module, no test seam -- reads a
JSON request on stdin, and prints one JSON observation on stdout. Two
installations that print the same observation are indistinguishable to a
client.

The fingerprint below is deliberately a copy of
``tests.composition_fingerprints.fingerprint``: this script must run where
the repository's ``tests`` package does not exist. The pairing test compares
its results with the checked-in fixture, which cross-checks the copy.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

import forge_template
from forge_template import (
    ForgeEngineError,
    RenderedProject,
    discover_components,
    get_engine_info,
    parse_generation_metadata,
    parse_project_spec,
    plan_generation,
    plan_update,
    render_project,
    validate_project_spec,
    verify_generation_metadata,
)

_FINGERPRINT_VERSION = 1
_PROVIDER_VERSION_PLACEHOLDER = "<provider-version>"


def _fingerprint(project: RenderedProject) -> str:
    assert project.metadata is not None
    metadata = project.metadata.model_dump(mode="json")
    metadata["provider"]["version"] = _PROVIDER_VERSION_PLACEHOLDER
    document = {
        "fingerprint_version": _FINGERPRINT_VERSION,
        "component_order": list(project.plan.component_order),
        "plan": [item.model_dump(mode="json") for item in project.plan.files],
        "files": {
            item.target: hashlib.sha256(item.content).hexdigest()
            for item in project.files
        },
        "metadata": metadata,
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _failure(call: Any) -> dict[str, Any]:
    try:
        call()
    except ForgeEngineError as error:
        return {
            "code": error.code.value,
            "operation": error.operation,
            "message": error.message,
            "details": [
                [detail.code, [str(part) for part in detail.path]]
                for detail in error.details
            ],
        }
    return {"code": "did-not-raise"}


def observe(request: dict[str, Any]) -> dict[str, Any]:
    payloads: dict[str, dict[str, Any]] = request["payloads"]
    renders: dict[str, RenderedProject] = {}
    compositions: dict[str, Any] = {}
    for slug, payload in sorted(payloads.items()):
        spec = validate_project_spec(parse_project_spec(payload))
        plan = plan_generation(spec)
        project = render_project(spec)
        assert project.plan == plan
        assert project.metadata is not None
        recorded = project.metadata.to_json()
        document = parse_generation_metadata(recorded)
        verify_generation_metadata(document, project)
        renders[slug] = project
        compositions[slug] = {
            "fingerprint": _fingerprint(project),
            "recorded": recorded,
        }

    transitions: dict[str, Any] = {}
    for name, (before, after) in sorted(request["transitions"].items()):
        old = renders[before]
        assert old.metadata is not None
        update = plan_update(
            old.metadata.to_json(),
            old={item.target: item.content for item in old.files},
            new=renders[after],
        )
        transitions[name] = update.model_dump(mode="json")

    any_slug = sorted(payloads)[0]
    document = json.loads(compositions[any_slug]["recorded"])
    unknown = json.loads(json.dumps(payloads[any_slug]))
    unknown["components"]["archetype"] = "nonesuch"
    failures = {
        "invalid-spec": _failure(lambda: parse_project_spec({"protocol_version": 1})),
        "unknown-archetype": _failure(
            lambda: validate_project_spec(parse_project_spec(unknown))
        ),
        "unsupported-metadata": _failure(
            lambda: parse_generation_metadata({**document, "metadata_version": 7})
        ),
        "unavailable-provider": _failure(
            lambda: plan_update(document, old={}, new=renders[any_slug])
        ),
    }

    info = get_engine_info().model_dump(mode="json")
    return {
        "engine_info": info,
        "public_names": sorted(forge_template.__all__),
        "catalogue": [d.model_dump(mode="json") for d in discover_components()],
        "compositions": {
            slug: entry["fingerprint"] for slug, entry in compositions.items()
        },
        "transitions": transitions,
        "failures": failures,
        "modules": sorted(
            name for name in sys.modules if name.startswith("forge_template")
        ),
    }


def main() -> None:
    request = json.loads(sys.stdin.read())
    json.dump(observe(request), sys.stdout, sort_keys=True)


if __name__ == "__main__":
    main()
