# 82. Implement the independent batch archetype

Date: 2026-09-29

## Status

Accepted

Records implementation choices for
[FT-28.01](https://github.com/Sandsy09/forge-template/issues/201), the first
child of [FT-EPIC-28](https://github.com/Sandsy09/forge-template/issues/190).
[ADR 0080](0080-batch-project-shape.md) and
[ADR 0081](0081-batch-composition-compatibility-and-acceptance.md) fixed the
shape and the composition/version/protocol decisions this record carries over
unchanged; nothing here re-litigates them.

## Context

FT-27.01/.02 left an exact, unambiguous implementation target: a `batch`
archetype, `id = "batch"`, `kind = "archetype"`, `version = "1.0.0"`,
`manifest_version = 2`, no `requires`/`conflicts`/options, `requires_python
= ">=3.11"`, and eight Foundation contributions
(`pyproject-build-system`, `pyproject-archetype-metadata`,
`pyproject-build-configuration`, `pyproject-classifiers`,
`pyproject-entry-points`, `pyproject-task-definitions`,
`readme-project-shape`, `gitignore-project-shape`). This mirrors
[ADR 0070](0070-streamlit-archetype-implementation.md) (Streamlit's own first
implementation record): a decision contract fixed the shape and the
extension-point table in advance, so this issue's own choices are narrow --
how the code inside `job.py` and its test actually reads, not what the
component looks like from outside.

## Decision

Implement `src/forge_template/components/batch/` exactly as
[docs/batch-archetype.md](../batch-archetype.md) specifies, and record two
choices the contract left to the code:

1. **`job.py`'s malformed-record check is "has a non-empty string `id`
   field".** ADR 0080 choice 8 fixed the fail-fast behaviour and the log
   levels but not the exact validity predicate. A record with no `id`, a
   non-string `id`, or an empty `id` is malformed; every other field passes
   through unchanged. Rejected: validating the whole record against a schema
   (the contract's transformation is deliberately trivial -- one derived
   field -- and a schema library is exactly the kind of dependency choice 3
   of ADR 0080 forecloses).
2. **The atomic write's temporary file is `<name>.tmp` in the same
   directory** (`os.replace` requires the same filesystem for its atomicity
   guarantee on all supported platforms). Rejected: `tempfile.NamedTemporaryFile`
   in the system temp directory (risks crossing filesystems, which turns
   `os.replace` into a non-atomic copy-then-delete on some platforms).

Every other file, path and contribution matches
[docs/batch-archetype.md](../batch-archetype.md) verbatim: no discovery or
composition code changed, because the engine already loads any
`components/*/component.toml` generically.

This decision changes no public engine signature, `EngineErrorCode`, protocol
integer, or `copier.yml`/`template/` file. The package stays `0.6.0` and
untagged; `batch` is discovered on `main` but not yet published.

## Consequences

- `discover_components()` returns sixteen components; the full composition
  sweep grows from 2880 to 3520 valid compositions, exactly as
  [ADR 0081](0081-batch-composition-compatibility-and-acceptance.md)
  projected.
- `tests/test_batch_contract.py` and `tests/test_batch_gates.py` are updated
  to assert the shipped, discovered state rather than the pre-implementation
  baseline, following the same discipline
  `test_streamlit_contract.py`/`test_streamlit_gates.py` followed through
  Stage 20. Their remaining package-version-line assertions stay at the
  `0.6.0` baseline until FT-28.03 publishes `0.7.0`.
- `scripts/check_wheel.py` and `docs/compatibility-policy.md`'s current-state
  table are updated with the new component; the wheel's smoke import now
  renders a `batch` composition alongside `library` and `streamlit`.
- FT-28.02 inherits a real, discoverable component to validate exhaustively
  (the sweep, the endpoint harness, the wheel/sdist audit, and provenance and
  update evidence) and FT-28.03 inherits an unambiguous target for the
  `0.7.0` release.
- `docs/roadmap-v5/**` and its hash-pinned issue mirrors are untouched.
  FT-EPIC-28 stays open until FT-28.03 is complete.
- The wheel now measures 128,922 bytes, within 2,150 bytes of
  `scripts/check_wheel.py`'s 131,072-byte (128 KiB) ceiling. `poe check:wheel`
  still passes, but the margin is now small enough that FT-28.02/FT-28.03
  should re-check it rather than assume headroom; raising the ceiling itself
  needs the same deliberate review any bound change does, not a reflexive
  bump.
