"""The supported Forge template-engine API and repository tooling.

Nothing in this package is copied into generated projects. Public engine
clients should import the names re-exported here rather than reaching into
the low-level composition modules directly.
"""

from forge_template.engine import (
    SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS,
    SUPPORTED_PROJECTSPEC_PROTOCOLS,
    ComponentDescriptor,
    ComponentOption,
    ComponentRelation,
    EngineErrorCode,
    EngineErrorDetail,
    EngineInfo,
    ForgeEngineError,
    GenerationPlan,
    PlannedExtension,
    PlannedFile,
    RenderedFile,
    RenderedProject,
    discover_components,
    get_engine_info,
    parse_project_spec,
    plan_generation,
    render_project,
    validate_project_spec,
)
from forge_template.project_spec import (
    PROJECT_SPEC_PROTOCOL_VERSION,
    Author,
    ComponentSelection,
    ProjectMetadata,
    ProjectSpec,
    PythonSelection,
    SelectionProvenance,
)

__all__ = [
    "PROJECT_SPEC_PROTOCOL_VERSION",
    "SUPPORTED_COMPONENT_MANIFEST_PROTOCOLS",
    "SUPPORTED_PROJECTSPEC_PROTOCOLS",
    "Author",
    "ComponentDescriptor",
    "ComponentOption",
    "ComponentRelation",
    "ComponentSelection",
    "EngineErrorCode",
    "EngineErrorDetail",
    "EngineInfo",
    "ForgeEngineError",
    "GenerationPlan",
    "PlannedExtension",
    "PlannedFile",
    "ProjectMetadata",
    "ProjectSpec",
    "PythonSelection",
    "RenderedFile",
    "RenderedProject",
    "SelectionProvenance",
    "discover_components",
    "get_engine_info",
    "parse_project_spec",
    "plan_generation",
    "render_project",
    "validate_project_spec",
]
