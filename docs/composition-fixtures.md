# Composition contract fixtures

This document describes what the composition-contract golden fixtures prove,
what "deterministic" is verified to mean through the stable rendering API,
and how to regenerate them when a contract legitimately changes.
Delivered by [FT-06.06](https://github.com/Sandsy09/forge-template/issues/37)
through [`tests/test_composition_contract.py`](../tests/test_composition_contract.py)
and [`tests/composition_contract.py`](../tests/composition_contract.py), this
document is adopted by [ADR
0028](adr/0028-composition-contract-fixtures.md).

## Scope

This is a test methodology, not another engine contract. It exercises the
[stable template-engine API](template-engine-api.md) over the reference fixture
catalogue in `tests/fixtures/component_manifests/`. A private, test-only seam
redirects package discovery to that catalogue; production clients cannot use
it. The scenarios now prove real contribution splicing and rendering through
`render_project`, not a test-local approximation. Their Library-shaped
`pyproject.toml` also satisfies the canonical
[generated-project validation](generated-project-validation.md), so the
goldens exercise the same automatic pre-return boundary as a public client.
Organisation-policy resolution now has its own executable, test-only proof --
see [organisation-policy-fixtures.md](organisation-policy-fixtures.md) -- but
these golden scenarios remain policy-independent.

## Golden format

Each scenario is one JSON document under `tests/fixtures/golden/`, holding the
public component order, path-free target/owner/extension plan, and every output
target's rendered content as a JSON string.

Storing rendered content inside a JSON string rather than as real files is
deliberate: the root `.pre-commit-config.yaml` runs
`end-of-file-fixer`/`trailing-whitespace`/`mixed-line-ending` over every file
with no exclusions, by design ([docs/invariants.md](invariants.md) invariant
1). A byte a golden fixture
must pin exactly — a missing trailing newline, deliberate trailing whitespace
— would otherwise be silently rewritten by the hook, and the resulting test
failure would look like a renderer bug rather than a hook edit. A newline
inside a JSON string is escaped (`\n`) and never sits at a physical
end-of-file or line-end, so the outer file stays a normal, hook-compliant
JSON document while its content field can pin anything.

## Scenarios

| Scenario | Selection | Proves |
| --- | --- | --- |
| `minimal` | `library` only | The floor: one archetype, empty capability and platform tiers, a schema-supplied default alongside a required option. |
| `extension` | `library`, `coverage`, `github` | The canonical case that runs against tier order: `coverage` (a capability) contributes to `github` (a platform)'s extension point, even though capabilities apply before platforms. |
| `full` | `library`, `changelog`, `coverage`, `documentation`, `github` | The kitchen-sink pattern that has already caught real bugs the narrower combos missed for the template-scaffolding suite (CLAUDE.md); here it selects every reference component at once. |

None of the three fixture components' manifests contribute to the implicit
Foundation content source (FT-08.02), so these goldens do not exercise it;
`PlannedFile.owner` on every entry here is always a `ComponentOwner`. Dedicated
Foundation-aware fixtures and tests
(`tests/fixtures/foundation/`, `tests/test_foundation_source.py`,
`tests/test_engine.py`) cover that mechanism directly instead of extending
these golden scenarios.

## Invalid catalogues

`tests/fixtures/invalid_components/` holds on-disk fixtures for three
distinct validation layers, each individually well-formed TOML — a checked-in
malformed-TOML fixture would be rejected outright by the root
`check-toml` pre-commit hook, so that case stays built in `tmp_path` inside
`tests/test_component_manifest.py`, as it already was:

- **`cycle-a` / `cycle-b`** — a `requires` cycle, rejected catalogue-wide by
  `validate_manifest_set` regardless of any particular selection.
- **`conflicting-first` / `conflicting-second`** — a declared `conflicts`
  edge, rejected by `validate_manifest_selection` only once both are
  selected together.
- **`colliding-first` / `colliding-second`** — two components whose owned
  content maps to the same output target, with no declared relationship
  between them at all. Both load and select cleanly; the collision only
  exists once `resolve_output_plan` resolves the whole plan, proving
  rejection happens before any file operation even when nothing about the
  manifests themselves was invalid.

## Determinism

[composition-order.md's determinism
guarantee](composition-order.md#determinism-guarantee) names manifest input
order, `dict`/`set` iteration order, `PYTHONHASHSEED`, and the enumerating
filesystem explicitly. `test_composed_output_is_invariant_to_manifest_input_order`
covers the first two in-process, over the full composed artefact rather than
composition order alone. `PYTHONHASHSEED` is fixed for the lifetime of one
Python process, so no in-process test can vary it — `test_composed_output_is_invariant_to_pythonhashseed`
instead spawns fresh subprocesses across several explicit seed values and
compares a hash of each one's composed output, the only way to actually
exercise that half of the guarantee rather than leave it a prose claim.

## Regenerating goldens

```bash
uv run pytest tests/test_composition_contract.py --update-goldens
```

Rewrites every golden fixture from the current composed output, then skips
the comparison for that run. Review the diff like any other change — the
deliberateness lives in that review, not in the regeneration step itself.
`--update-goldens` is a `pytest` option registered in `tests/conftest.py`,
alongside the existing `--from-git` option.

The same option also regenerates
`tests/fixtures/archetype_regression/digests.json` — the per-target SHA-256
map `tests/test_data_science_composition.py` pins `library` and `cli` output
against across every capability selection (FT-12.03, ADR 0055). Unlike the
goldens above, that fixture is generated from the **production** catalogue,
not `tests/fixtures/component_manifests/`, so any deliberate change to
`library`, `cli`, `jupyter`, `scientific-python`, or Foundation output must
regenerate it:

```bash
uv run pytest tests/test_data_science_composition.py --update-goldens
```

## Remaining boundary

These fixtures do not define organisation-policy resolution; that is
[organisation-policy-fixtures.md](organisation-policy-fixtures.md)'s own,
separate test-only proof, and remains no shipped public API either way. The
current CLI continues to pass its plain answer mapping directly to Copier,
and no generated project depends on `tests/composition_contract.py`
— it is test-only and ships in no package.
