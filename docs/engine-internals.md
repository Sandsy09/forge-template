# Engine internals and compatibility baseline

This is the living contract for how the engine is organised behind the
supported facade, and for the baseline that proves a reorganisation changed
nothing a client can see.
[ADR 0079](adr/0079-decompose-the-engine-behind-a-frozen-facade.md) records
the decision. The supported API itself is
[template-engine-api.md](template-engine-api.md).

Status: the baseline is in force (FT-25.01), and the module split below is
implemented (FT-25.02) with every recorded baseline unchanged.

## What is frozen

A change to any of these is a public behaviour change. It needs a reason in
the pull request and, where the compatibility policy says so, an ADR. It is
never fixed by regenerating a fixture.

| Surface | Recorded in | Asserted by |
| --- | --- | --- |
| `forge_template.__all__` | `_FROZEN_PUBLIC_API` | `tests/test_cutover_gates.py` |
| `EngineErrorCode` values | `_SHIPPED_ERROR_CODES` | `tests/test_cutover_gates.py` |
| Parameter names and kinds, model field names | `tests/test_engine.py` | `poe check` |
| Full signatures, overloads, model config and JSON schema, protocol constants | `tests/fixtures/engine_facade_baseline.json` | `tests/test_engine_facade_contract.py` |
| Error identity of 29 failure paths | same file, `errors` | same test |
| Names reachable from `forge_template.engine`, as the same objects | `_ENGINE_MODULE_NAMES` | same test |
| No import side effects | subprocess probe | same test |
| Output of every accepted composition | `tests/fixtures/composition_fingerprints.json` | `tests/test_composition_sweep.py` (`sweep`) |
| Output of one composition per archetype | same file | `tests/test_engine_baseline.py` |
| Discovery order | derived | `tests/test_engine_baseline.py` |
| `plan_update` classifications | `tests/fixtures/update_classifications.json` | `tests/test_engine_baseline.py` |
| Independent client: render, reproduce, verify, update | `tests/no_copy_downstream.py` | `tests/test_no_copy_inheritance.py` |

### The error identity

Each characterised failure records `code`, `operation`, the top-level
message, and each detail's `code` and `path`. Detail messages are not pinned
because some carry a local path or a library's wording. The installed package
version is normalised in the one message that names it.

The operations in use are `parse`, `discover`, `validate`, `plan`, `render`,
`validate-output` and `map-legacy-answers`. Two behaviours the baseline
records as they are:

- A metadata *string* that is not JSON reports `operation="validate"` with
  the detail code `json_invalid`, while a payload that is not a string,
  bytes, mapping or document reports `operation="parse"`.
- `plan_update` reports an unavailable historical provider as
  `unsupported-generation-metadata` on the `provider` path.

### Output fingerprints

A fingerprint is the sha256 of canonical JSON holding the plan's component
order, each planned file's target, owner, extensions and regeneration, the
sha256 of every rendered target, and the generation-metadata document with
`provider.version` replaced by a placeholder. It covers the plan, the bytes
and the provenance digests together, and survives a version bump.

Regenerate only for a reviewed output change:

```bash
uv run python -m tests.composition_fingerprints --write
```

The other two baseline files regenerate with `--update-goldens` on their own
test modules. Review each diff before committing it.

## Import behaviour

- Clients import from `forge_template`. Every name documented there is
  supported; nothing else is.
- Every `forge_template.__all__` name reachable from `forge_template.engine`
  in `0.6.0` remains reachable there as the same object.
- `__module__` is not part of the contract. In `0.6.0` the engine models,
  errors and functions report `forge_template.engine`; the metadata models
  report `forge_template.generation_metadata`, the owners
  `forge_template.file_conflicts`, and the ProjectSpec models
  `forge_template.project_spec`. Since FT-25.02 the engine functions still
  report `forge_template.engine`, while the engine models report
  `forge_template._models` and the error types `forge_template._errors`.
- Importing `forge_template` loads none of the check-only modules (`adr`,
  `render`, `schema`, `github_actions`), neither the `components` nor the
  `foundation` package, and writes nothing.

## Module map

| Module | Owns |
| --- | --- |
| `engine.py` | The facade: re-exports and the public functions with their overloads and docstrings, each delegating below. `render_project` still calls the module-level `validate_rendered_project`. |
| `_models.py` | The public result models. |
| `_errors.py` | `EngineErrorCode`, `EngineErrorDetail`, `ForgeEngineError`, and the helpers that build error details. |
| `_discovery.py` | The test-only catalogue and Foundation root overrides, catalogue and Foundation loading, descriptors, ProjectSpec parsing, and selection and option validation. |
| `_rendering.py` | Plan preparation, the extension contract, template assembly, the Jinja environment, rendering, and rendered-output validation. |
| `_provenance.py` | Package identity, the supported protocol constants and the metadata payload alias (re-exported by the facade), generation-metadata construction, parsing, negotiation and verification, rename windows, classification, and update planning. |
| `_legacy_answers.py` | `map_legacy_library_answers`. |

The existing composition modules (`component_manifest`, `composition`,
`file_conflicts`, `foundation_source`, `generation_metadata`, `project_spec`,
`template_variables`) keep their roles.

## Rules for the private modules

- Dependencies point one way: the facade uses the responsibility modules,
  which use `_models` and `_errors`. Nothing imports the facade back.
- No private module writes files, starts a process, or merges. Destination
  staging, Git and conflict handling remain `create-forge`'s.
- Package resources are read through `importlib.resources`, as before.
- A leading underscore means private. No client, example or document may
  import one.
- Tests reach the root overrides and the catalogue loader only through
  `tests/engine_seams.py`.
