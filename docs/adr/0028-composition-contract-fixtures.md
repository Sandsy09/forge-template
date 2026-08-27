# 28. Adopt composition-contract fixtures

## Status

Accepted

## Context

Five accepted contracts each name this issue as the owner of "full
composed-output fixtures": `docs/project-spec.md`, `docs/component-manifests.md`,
`docs/composition-order.md`, `docs/file-conflicts.md`, and
`docs/template-variables.md`. Unlike its five predecessors, this issue is
labelled `type:test`, not `type:decision` — its GitHub scope is "add
golden/snapshot fixtures", "test conflicting component selections", "test
invalid manifests", and "test deterministic rendering", not a new normative
vocabulary. It still carries real methodology decisions that deserve a
record: how to store rendered content without a checked-in golden getting
silently rewritten by this repo's own pre-commit hooks, how far to go on
"deterministic rendering" when no stable rendering API exists yet, and where
this issue's own boundary against [FT-06.07](https://github.com/Sandsy09/forge-template/issues/38)
falls.

`forge_template.composition`, `forge_template.file_conflicts`, and
`forge_template.template_variables` had never been exercised together in one
test before this issue — each of their own test modules constructs manifests
and specs independently, so no test proved the three contracts actually
compose into one coherent, deterministic output for a realistic selection.

## Decision

- **Golden fixtures are one JSON document per scenario**, holding
  composition order, the resolved output plan, resolved template variables,
  and every output target's rendered content as a JSON string —
  `tests/fixtures/golden/{minimal,extension,full}.json`. Storing rendered
  content inside a JSON string, rather than as real files, is what keeps it
  immune to the root `.pre-commit-config.yaml`'s `end-of-file-fixer`,
  `trailing-whitespace`, and `mixed-line-ending` hooks, which deliberately
  cover every file with no exclusions (CLAUDE.md invariant 1): a byte a
  golden must pin exactly can never sit at a physical line-end once it is
  inside an escaped JSON string, so no exclusion needs carving out of a hook
  set that stays broad on purpose.
- **Three scenarios**: `minimal` (one archetype, the floor), `extension`
  (a capability contributing to a platform's extension point — the case
  that runs against tier order), and `full` (every reference component at
  once, the kitchen-sink pattern already credited with catching real bugs
  the narrower combos missed).
- **Composition is aggregated by a test-only helper**,
  `tests/composition_contract.py`, not a new `src/forge_template` module.
  It chains `composition_plan` → `resolve_output_plan` →
  `resolve_template_variables`, then renders each output target's *base*
  contribution through a test-local Jinja environment with
  `StrictUndefined` — matching the undefined-must-fail rule
  `docs/template-variables.md` already states normatively. It never splices
  an extension's contribution into its base's content, because the in-file
  marker syntax an extension point splices into is undecided until
  FT-06.07. Keeping this helper out of `src/forge_template` means FT-06.07
  keeps undivided ownership of the stable, public composition/rendering
  facade it is chartered to expose; this issue reads "test deterministic
  rendering" as proving the composed plan and a demonstration rendering are
  both deterministic, not as pre-empting that facade.
- **Invalid catalogues are on-disk fixtures, one per validation layer**:
  `cycle-a`/`cycle-b` (catalogue-wide, kind-independent — rejected by
  `validate_manifest_set`), `conflicting-first`/`conflicting-second`
  (selection-dependent — rejected by `validate_manifest_selection`), and
  `colliding-first`/`colliding-second` (output-plan-dependent — rejected by
  `resolve_output_plan` despite each manifest loading and selecting
  cleanly on its own). Each fixture is valid TOML — a malformed-TOML
  fixture would be rejected outright by the root `check-toml` pre-commit
  hook, so that case stays exercised in `tmp_path`, as
  `tests/test_component_manifest.py` already does.
- **Determinism is proven, not just asserted in prose.** In-process
  permutation of manifest input order covers `dict`/`set` iteration order;
  a `PYTHONHASHSEED` sweep across several explicit seed values, run in
  subprocesses (a single pytest process has one fixed seed, so no
  in-process test can vary it), covers the half of
  `docs/composition-order.md`'s determinism guarantee that names
  `PYTHONHASHSEED` explicitly.
- **Goldens regenerate via a `--update-goldens` pytest flag**, registered
  in `tests/conftest.py` alongside the existing `--from-git` option, rather
  than a separate script or hand-editing. The deliberateness a golden
  change needs lives in reviewing the diff afterwards, not in gatekeeping
  the regeneration step itself.

## Consequences

- The five contracts' forward references to "full composed-output fixtures
  (FT-06.06)" now resolve to `docs/composition-fixtures.md` and this record.
- `forge_template.composition`, `forge_template.file_conflicts`, and
  `forge_template.template_variables` are now proven, in one place, to
  compose into one coherent, deterministic artefact for a realistic
  selection — not just correct individually.
- FT-06.07 remains the sole owner of a public rendering function, the
  extension-point marker syntax, component discovery, and structured engine
  errors; nothing here is exported from `forge_template`, and
  `tests/composition_contract.py` ships in no package.
- FT-06.07's blockers (`#32`–`#37`) are now all complete, so it becomes the
  final open Stage 06 issue.
- The current v0.1.x Copier path, template tree, generated output, and CLI
  behaviour do not change.
