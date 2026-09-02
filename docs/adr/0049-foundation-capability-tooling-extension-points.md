# 49. Publish Foundation extension points for capability tooling

Date: 2026-09-02

## Status

Accepted

## Context

Foundation publishes eight content extension points. Six sit on
`content/pyproject.toml.jinja` and exist for one purpose: letting a selected
archetype attach its packaging shape — build system, metadata, build
configuration, runtime dependencies, classifiers, entry points. The other two
are `readme-project-shape` and `gitignore-project-shape`.

[ADR 0046](0046-initial-data-science-capabilities.md) fixed a `jupyter`
capability that must contribute four development dependencies, a `notebook`
and a `notebook:check` Poe task, and an entry joining `notebook:check` to the
aggregate `check` contract. [ADR 0047](0047-notebook-data-and-model-safeguards.md)
left the extension point a capability uses to contribute a `.gitignore` entry
"FT-11.01's to define". None of that is expressible today: no published point
covers Foundation's `dev` dependency group, its `[tool.poe.tasks]` table, or
its `check` array, and the existing points are only ever contributed to by an
archetype.

[FT-11.02 / #106](https://github.com/Sandsy09/forge-template/issues/106) and
[FT-11.03 / #107](https://github.com/Sandsy09/forge-template/issues/107)
cannot author their manifests until the points exist.

The engine's extension marker is a whole-line token
(`_EXTENSION_TOKEN_RE`). The aggregate `check` task is currently a single
inline array, so a marker cannot be placed inside it without the array
becoming multi-line.

## Decision

Publish three additional extension points on
`content/pyproject.toml.jinja`, declared in `foundation.toml`:

- `pyproject-development-dependencies` — PEP 508 requirement strings into
  Foundation's existing `dev` dependency group.
- `pyproject-task-definitions` — `"name" = "command"` lines into
  `[tool.poe.tasks]`, before the aggregate `check`.
- `pyproject-aggregate-check` — task-name strings into the `check` array.

The published inventory grows from eight points to eleven. No other change is
made: `foundation_version` stays `1`, the Foundation source protocol stays
`1`, no engine module changes, no public signature or `EngineErrorCode`
changes, and `library` and `cli` stay at component version `1.0.1` with no
contributions into any new point.

Every existing rule applies unchanged. Foundation keeps ownership of
`pyproject.toml`; contributions are `extend`, never `override` or `merge`.
Any selected owner may contribute — archetype or capability. Multiple
contributions to one point compose in composition order (archetype tier, then
capability tier, lexical within a tier), never last-write-wins. A contribution
to an undeclared point is rejected at catalogue validation independent of
selection. An unfilled point contributes zero bytes, because the marker line
and its trailing newline are removed when nothing targets it.

The aggregate `check` array is reformatted from one inline line to a
multi-line array so a marker line can sit inside it. This is the one
deliberate change to generated output. It is semantics-preserving: the
rendered array parses to exactly the historic
`["lock:check", "format:check", "lint", "typecheck", "test"]` sequence when no
capability contributes, and `tests/test_capability_extension_points.py` pins
that equality alongside the byte-for-byte `library` and `cli` render match
against a Foundation source without the three points at all.

A capability contributes a `.gitignore` entry or root-README guidance through
the existing `gitignore-project-shape` and `readme-project-shape` points under
the same "any selected owner may contribute" rule. No capability-specific
point is added for either, and a capability does not gain its own named
dependency group.

The three points ship in the `0.4.0` line
([ADR 0048](0048-data-science-compatibility-and-acceptance.md)). The points
alone are additive and would not force even a minor bump; they ride the
release that first makes a requirable capability visible.

The rules are recorded in
[extension-points.md](../extension-points.md#capability-tooling-extends-the-same-foundation-content),
which stays the single versioned inventory; this issue adds no new canonical
document.

## Consequences

- `jupyter` and `scientific-python` (FT-11.02, FT-11.03) can now be authored
  against real published points; FT-11.02 can join `notebook:check` to the
  aggregate `check` contract as ADR 0046 requires.
- Generated `pyproject.toml` for `library` and `cli` changes in exactly one
  way — the `check` array is now multi-line — and is otherwise byte-for-byte
  unchanged. Downstream `copier update` is unaffected: this is the engine
  path, not `template/`.
- The published extension-point inventory is now eleven entries;
  `tests/test_extension_points.py` pins the set and
  `tests/test_capability_extension_points.py` pins the additive behaviour.
- Renaming or removing any of the three later is a breaking change under
  [extension-points.md](../extension-points.md#stability-and-versioning), the
  same as for the original eight.
- A capability still cannot declare its own dependency group, replace a
  Foundation file, or reach a point through policy; the extension surface is
  wider by three points, not different in kind.
- No package version, protocol integer, component version, manifest,
  dependency, catalogue entry, public API, generated file beyond the recorded
  `check` reformat, tag, or release changes through this decision.
