"""Stable, side-effect-free Forge template-engine facade.

The public functions in this module are the supported boundary for
``create-forge`` and other clients. They discover only components bundled in
the installed ``forge-template`` distribution, validate the canonical
ProjectSpec, produce an immutable generation plan, and render an in-memory
file set. Destination orchestration deliberately remains a client concern.

Each function delegates to a private module (ADR 0079,
docs/engine-internals.md): ``_discovery`` for the catalogue and ProjectSpec
validation, ``_rendering`` for planning, rendering and output validation,
``_provenance`` for generation metadata and update planning, and
``_legacy_answers`` for the Copier answer mapping. Clients import every name
from :mod:`forge_template`; the private modules are not supported API.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeAlias, overload

from pydantic import JsonValue

from forge_template import (
    _discovery,
    _legacy_answers,
    _provenance,
    _rendering,
)
from forge_template._errors import EngineErrorCode, EngineErrorDetail, ForgeEngineError
from forge_template._models import (
    ComponentDescriptor,
    ComponentOption,
    ComponentRelation,
    EngineInfo,
    GenerationPlan,
    PlannedExtension,
    PlannedFile,
    RenderedFile,
    RenderedProject,
)
from forge_template._provenance import (
    SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS,
    SUPPORTED_PROJECTSPEC_PROTOCOLS,
    GenerationMetadataPayload,
)
from forge_template.file_conflicts import FoundationOwner
from forge_template.generation_metadata import (
    GENERATION_METADATA_VERSION,
    AppliedRename,
    GenerationMetadata,
    MetadataProtocols,
    OutputRecord,
    ProviderIdentity,
    ReproductionRecord,
    SelectedComponent,
    UpdatePlan,
    UpdateTarget,
)
from forge_template.project_spec import PROJECT_SPEC_PROTOCOL_VERSION, ProjectSpec

__all__ = [
    "GENERATION_METADATA_VERSION",
    "PROJECT_SPEC_PROTOCOL_VERSION",
    "SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS",
    "SUPPORTED_PROJECTSPEC_PROTOCOLS",
    "AppliedRename",
    "ComponentDescriptor",
    "ComponentOption",
    "ComponentRelation",
    "EngineErrorCode",
    "EngineErrorDetail",
    "EngineInfo",
    "ForgeEngineError",
    "FoundationOwner",
    "GenerationMetadata",
    "GenerationMetadataPayload",
    "GenerationPlan",
    "MetadataProtocols",
    "OutputRecord",
    "PlannedExtension",
    "PlannedFile",
    "ProjectSpec",
    "ProjectSpecPayload",
    "ProviderIdentity",
    "RenderedFile",
    "RenderedProject",
    "ReproductionRecord",
    "SelectedComponent",
    "UpdatePlan",
    "UpdateTarget",
    "discover_components",
    "get_engine_info",
    "map_legacy_library_answers",
    "parse_generation_metadata",
    "parse_project_spec",
    "plan_generation",
    "plan_update",
    "render_project",
    "validate_project_spec",
    "validate_rendered_project",
    "verify_generation_metadata",
]

ProjectSpecPayload: TypeAlias = ProjectSpec | Mapping[str, object] | str | bytes
"""Inputs accepted by :func:`parse_project_spec`."""


def get_engine_info() -> EngineInfo:
    """Return package/protocol metadata without discovering components."""
    return EngineInfo(
        package_version=_provenance.package_version(),
        projectspec_protocols=SUPPORTED_PROJECTSPEC_PROTOCOLS,
        component_manifest_protocols=SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS,
        metadata_version=GENERATION_METADATA_VERSION,
    )


def validate_rendered_project(
    spec: ProjectSpec,
    project: RenderedProject,
) -> RenderedProject:
    """Validate an immutable rendered project without filesystem side effects.

    See ``docs/generated-project-validation.md`` for the supported contract.
    """
    return _rendering.validate_output(spec, project)


@overload
def parse_project_spec(payload: ProjectSpec) -> ProjectSpec: ...


@overload
def parse_project_spec(payload: Mapping[str, object]) -> ProjectSpec: ...


@overload
def parse_project_spec(payload: str | bytes) -> ProjectSpec: ...


def parse_project_spec(payload: object) -> ProjectSpec:
    """Strictly parse one ProjectSpec wire payload without catalogue access."""
    return _discovery.parse_spec(payload)


def discover_components() -> tuple[ComponentDescriptor, ...]:
    """Return the installed, reviewed component catalogue in lexical order."""
    return _discovery.discover()


def validate_project_spec(spec: ProjectSpec) -> ProjectSpec:
    """Validate a parsed ProjectSpec against the installed component catalogue."""
    return _discovery.validate_spec(spec)


def plan_generation(spec: ProjectSpec) -> GenerationPlan:
    """Return a deterministic, side-effect-free plan for one ProjectSpec."""
    return _rendering.prepare_generation(spec).plan


def render_project(spec: ProjectSpec) -> RenderedProject:
    """Render one ProjectSpec to immutable in-memory project-relative files."""
    prepared = _rendering.prepare_generation(spec)
    rendered_files = _rendering.render_files(prepared)
    project = RenderedProject(
        plan=prepared.plan,
        files=rendered_files,
        metadata=_provenance.build_generation_metadata(
            spec, prepared.plan, rendered_files, prepared.component_versions()
        ),
    )
    return validate_rendered_project(spec, project)


def map_legacy_library_answers(
    answers: Mapping[str, JsonValue],
) -> dict[str, JsonValue]:
    """Map released Copier Library answers to the ``packaging_mode`` option.

    Implements the mapping documented by
    docs/library-archetype.md#legacy-copier-answer-mapping: the released
    ``build_backend``/``versioning_resolved`` pair, unchanged, to the single
    production ``packaging_mode`` option. Pure and side-effect-free -- it
    takes a plain answer mapping and returns a plain option mapping, taking on
    no prompting or ProjectSpec-construction responsibility, which remain
    ``create-forge``'s. ``answers`` must supply exactly ``build_backend`` and
    ``versioning_resolved``; any other shape is rejected rather than guessed
    at.
    """
    return _legacy_answers.map_answers(answers)


def parse_generation_metadata(
    payload: GenerationMetadataPayload,
) -> GenerationMetadata:
    """Validate one generation-metadata document a client hands back.

    Closed-world structural validation first, then negotiation:
    ``metadata_version`` and every recorded protocol integer must be in this
    engine's supported set, the embedded spec must parse, and every recorded
    component must be a real catalogue entry at the recorded version. This
    never renders, so it never verifies digests -- see
    :func:`verify_generation_metadata`. Failures are
    ``invalid-generation-metadata`` (malformed, inconsistent, or an unknown
    component) or ``unsupported-generation-metadata`` (an out-of-range
    version), always with ``operation`` in ``{"parse", "validate"}`` and a
    fixed safe message -- no rendered content, no absolute path, no secret.
    """
    return _provenance.parse(payload)


def verify_generation_metadata(
    metadata: GenerationMetadata, project: RenderedProject
) -> None:
    """Check a document's digests and coverage against a re-rendered project.

    The caller reproduces the project -- ``render_project`` on the recorded
    spec, provisioned on the recorded release -- and passes the result here.
    Every ``output`` entry's digest must match the reproduced target's bytes,
    and the entry set must cover exactly the rendered targets. A mismatch is
    ``invalid-generation-metadata`` / ``validate``: a local edit, a tampered
    file, or a document from a different render. Never renders or writes.
    """
    _provenance.verify(metadata, project)


def plan_update(
    recorded: GenerationMetadataPayload,
    *,
    old: Mapping[str, bytes],
    new: RenderedProject,
) -> UpdatePlan:
    """Classify an engine-native update from a recorded document and a render pair.

    ``recorded`` is the generation-metadata document a client persisted for
    the project being updated. ``old`` is the bytes that document's provider
    release produced when the client reproduced it -- ``render_project`` on
    the recorded spec, provisioned on the recorded release, keyed by target --
    see docs/generation-provenance.md#identity-and-reproduction. ``new`` is a
    fresh ``render_project(effective_spec)`` result on this release. Neither
    render is performed here.

    Reads ``recorded`` leniently: the same structural check and protocol
    negotiation as :func:`parse_generation_metadata`, but a recorded component
    version that differs from the installed one is expected update input, not
    a failure -- an update is by definition an old document read on a newer
    engine.

    Fails closed, before any classification:

    - an empty ``old`` against a non-empty recorded ``output`` reports an
      unavailable historical provider as ``unsupported-generation-metadata``
      / ``validate``, naming the ``provider`` axis, the recorded version, and
      both remedies -- provision that release and reproduce it, or record an
      explicit degraded two-way update (the client's to make; this engine
      never performs that comparison);
    - a mismatched ``old`` target set, or a digest that does not match the
      recorded one, is ``invalid-generation-metadata`` / ``validate``: the
      supplied old render did not come from this document.

    Reads no filesystem, spawns no process, and returns data only
    (FT-ROADMAP-01-EX-01) -- the client applies the result.
    """
    return _provenance.plan_update(recorded, old=old, new=new)
