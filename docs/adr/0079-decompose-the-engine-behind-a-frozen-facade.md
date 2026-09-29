# 79. Decompose the engine behind a frozen facade

Date: 2026-09-29

## Status

Accepted

## Context

[FT-25.01](https://github.com/Sandsy09/forge-template/issues/194): the 21
September 2026 engineering review found that `src/forge_template/engine.py`
(1,678 lines) combines the public result models and errors, catalogue and
Foundation discovery, selection and option validation, plan preparation,
extension-contract checks, template assembly and rendering, output
validation, generation-metadata construction and verification, and update
planning. FT-25.02 splits it; FT-25.03 verifies the result. Neither may change
what a client sees: public exports, signatures, structured errors, protocols,
the component catalogue, or generated output.

Before this record the repository pinned the public name set, the error-code
values, parameter names and kinds, and result-model field names. It did not
pin annotations, defaults, overloads, model schemas, the `operation` and
message of each failure, import side effects, or the rendered bytes of more
than about eight compositions. Twelve test modules also patched private names
directly on `forge_template.engine`, so any move would have touched all of
them.

## Decision

1. **Freeze a compatibility baseline before any move.** The following are
   recorded and asserted, and a change to any of them is a behaviour change
   that has to be explained, not a fixture to regenerate:
   - `tests/fixtures/engine_facade_baseline.json`
     (`tests/test_engine_facade_contract.py`): each public callable's full
     signature and the `parse_project_spec` overloads, each public model's
     configuration and JSON schema, the protocol constants, and the
     structured-error identity (`code`, `operation`, message, detail codes and
     paths) of 29 documented failure paths reaching every `EngineErrorCode`.
   - `tests/fixtures/composition_fingerprints.json`: one sha256 per accepted
     composition (2,880) over its plan, rendered bytes, and generation
     metadata (provider version normalised), asserted by the `sweep` marker
     and, for one composition per archetype, by `poe check`.
   - `tests/fixtures/update_classifications.json`: `plan_update` results for
     five transitions per archetype.
2. **Import paths are contractual; `__module__` is not.** Every documented
   name stays importable from `forge_template`, and every name reachable from
   `forge_template.engine` in `0.6.0` stays reachable there as the same
   object. Importing the package loads no check-only module, no component or
   Foundation package, and writes nothing. The defining module of a class is
   an implementation detail and may change.
3. **Private seams.** `engine.py` stays the facade: protocol constants,
   payload aliases, re-exports, and the public function definitions (with
   their overloads and docstrings) delegating to private modules:
   - `_models.py` — the public result models;
   - `_errors.py` — `EngineErrorCode`, `EngineErrorDetail`,
     `ForgeEngineError` and the error-detail helpers;
   - `_discovery.py` — the test-only root overrides, catalogue and Foundation
     loading, descriptors, ProjectSpec parsing, and selection and option
     validation;
   - `_rendering.py` — plan preparation, the extension contract, template
     assembly and rendering, and rendered-output validation;
   - `_provenance.py` — package identity, generation-metadata construction,
     parsing, negotiation and verification, rename windows, classification,
     and update planning;
   - `_legacy_answers.py` — the legacy Copier answer mapping.

   Dependencies are acyclic (facade, then the three responsibility modules,
   then models and errors). Resources are still read through
   `importlib.resources`. No private module writes files, spawns processes,
   or merges; destination, Git and merge behaviour stay with the client.
4. **One test seam.** Tests reach the private overrides and the catalogue
   loader only through `tests/engine_seams.py`, so moving them changes one
   line.
5. **One record for the epic.** FT-25.02 implements this decision without a
   new ADR unless it has to deviate from it. FT-25.03 is validation only.

## Consequences

- FT-25.02 can move code in small steps, each checked against the same
  recorded baseline; `poe check` catches facade and representative output
  drift, and the sweep catches drift in any composition.
- A deliberate public change (a new name, field, error path or output byte)
  now also updates a reviewed baseline file, which makes it visible in review.
- The sweep checks one more assertion per composition; its budget is
  unchanged. The fingerprint baseline and the seam helper are
  composition-sensitive paths.
- A client relying on `__module__`, `repr` of a class, or a private name was
  never supported and may break in `0.6.x`.
- No change to exports, protocols, the catalogue, generated output, or the
  package version.
