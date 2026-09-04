# Data Science Roadmap Architecture

The accepted public-engine architecture remains unchanged. The roadmap adds a
third archetype and the first production capabilities through existing
package-bound component contracts.

```text
User
  ↓
create-forge --engine-preview
  │ discovery-driven selections and options
  │ strict ProjectSpec protocol
  ↓
forge-template public engine
  │ implicit Foundation
  │ exactly one archetype
  │ zero or more capabilities and platforms
  ↓
validated in-memory project
  ↓
create-forge staging, uv lock, atomic finalisation
```

## Accepted direction

- The [Data Science contract](../data-science-archetype.md) defines an
  optionless, package-backed, notebook-oriented archetype with independently
  owned package, test, notebook, and ignored working-tree paths.
- Reusable optional concerns become capabilities rather than Foundation
  defaults or duplicated archetype content.
- FT-10.01 fixes the minimal shape: the archetype owns the starter notebook
  and working-tree conventions. FT-10.02's [initial capability
  contracts](../data-science-capabilities.md) define reusable `jupyter`
  development tooling and the independently optional `scientific-python`
  runtime stack. FT-10.03's
  [notebook, data, and model safeguards](../notebook-data-and-model-safeguards.md)
  fix the fail-closed `notebook:check` order, deterministic failures, safe
  diagnostics, and the prose-only working-tree guidance. FT-10.04's
  [compatibility and acceptance contract](../data-science-compatibility-and-acceptance.md)
  classifies every versioned axis for the `0.4.0` line, fixes the executable
  acceptance matrix and its owners, and states the release gates, completing
  Stage 10.
- FT-11.01 publishes the three capability-tooling Foundation points. FT-11.02
  ships the optionless `jupyter` component and its safe generated notebook
  validator; FT-11.03 ships the independent `scientific-python` runtime stack
  and import test; FT-11.04 proves their composition end to end. FT-12.01
  then ships the independent `data-science` archetype, declaring the hard
  `jupyter` requirement, and FT-12.02 completes its generated shape with the
  output-free starter notebook and the ignored working trees. FT-12.03
  validates both compositions across Python 3.11 and 3.14 and byte-pins
  `library`/`cli` output. FT-12.04 published the complete catalogue in
  [`forge-template 0.4.0`](https://github.com/Sandsy09/forge-template/releases/tag/v0.4.0).
  Create-forge Stage 13 now consumes ProjectSpec behind `--engine-preview`.
- Capabilities remain bundled, reviewed forge-template components. This
  roadmap does not introduce plugins or remote component registries.
- create-forge consumes public descriptors and never recreates component
  semantics or catalogue metadata.

## Compatibility boundary

ProjectSpec, component-manifest, option-schema, Foundation-source, component,
and engine-package versions remain independently governed by the canonical
compatibility policy. Stage 10 has classified every required version change in
the
[compatibility and acceptance contract](../data-science-compatibility-and-acceptance.md):
only the package version and the discovered-component set move. FT-14.01's
[three-archetype review](../composition-architecture-review.md) confirms the
resulting line without changing any versioned surface; FT-14.02 next validates
the two repositories together before final rollout.

The default Copier path, `template/`, `copier.yml`, and stored Copier answers
are outside this roadmap unless a later, separately accepted cutover changes
that boundary.
