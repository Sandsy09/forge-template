# No-copy downstream inheritance

This document records the executable no-copy boundary for a Blueprint-style
downstream client. It is the canonical result of
[FT-09.05 / #48](https://github.com/Sandsy09/forge-template/issues/48),
adopted by
[ADR 0042](adr/0042-validate-no-copy-downstream-inheritance.md), and proved by
[`tests/test_no_copy_inheritance.py`](../tests/test_no_copy_inheritance.py).

Blueprint remains a conceptual, organisation-facing client. The proof uses a
small test-only client harness; it does not add a Blueprint repository, public
policy resolver, plugin mechanism, or second engine distribution.

## The no-copy contract

A conformant downstream client supplies policy, records explicit choices,
constructs project metadata and component options, and orchestrates the
result. It consumes only the supported top-level
[`forge_template`](template-engine-api.md) facade for discovery, ProjectSpec
parsing, planning, and rendering.

Foundation and component source remain reviewed, package-bound resources in
`forge-template`. A downstream client:

- does not copy, vendor, inherit from, or directly read that source;
- does not import `create-forge` or private `forge_template.*` modules;
- does not inject a private catalogue root, arbitrary file overlay, or
  post-render replacement as an extension mechanism; and
- never makes either Forge package a generated-project runtime dependency.

Two clients that construct equivalent effective ProjectSpecs receive
byte-identical `GenerationPlan` and `RenderedProject` values. Their
`SelectionProvenance` may name different policy paths without affecting
planning or rendering. Downstream output may differ only through:

1. selected components;
2. declared options owned by those selected components; and
3. those components' reviewed contributions to published extension points.

Organisation policy remains selection-only. It cannot carry files, template
content, component options, code, or an override grant. Organisation-specific
executable content therefore requires a reviewed `forge-template`
distribution or fork until a separately accepted public component-
distribution mechanism exists. This validation introduces no plugin,
registry, arbitrary-directory discovery, or remote catalogue contract.

## Executable proof

The test-only
[`tests/no_copy_downstream.py`](../tests/no_copy_downstream.py) harness reuses
the protocol-1 reference resolver from
[`tests/organisation_policy_contract.py`](../tests/organisation_policy_contract.py).
It then uses only public top-level Forge imports to construct the effective
ProjectSpec and call `plan_generation()` and `render_project()`.

### Real production catalogue

The existing `example-production-library` policy resolves against the real
installed catalogue. The test compares that policy-derived request with a
directly constructed, otherwise equivalent Library ProjectSpec and proves:

- plans, rendered targets, and rendered bytes are equal;
- the only ProjectSpec difference is recorded policy provenance;
- Foundation targets retain `FoundationOwner`;
- Library targets retain `ComponentOwner(id="library")`; and
- the generated project has no runtime dependency on `forge-template` or
  `create-forge`.

This is the public no-copy proof. It uses no test catalogue or catalogue-root
override.

### Additive fixture composition

The neutral `example-no-copy-inheritance` policy deliberately uses the
existing private test catalogue:

```json
{
  "policy_version": 1,
  "id": "example-no-copy-inheritance",
  "defaults": {
    "archetype": "library-v2",
    "capabilities": ["coverage"],
    "platforms": ["github"]
  },
  "required": {
    "capabilities": ["coverage"],
    "platforms": ["github"]
  },
  "forbidden": {
    "capabilities": ["documentation"]
  }
}
```

The client supplies the selected components' options, including the neutral
placeholder `example-org`; policy does not. The test proves:

| Result | Owner or contribution |
| --- | --- |
| `pyproject.toml` | Foundation-owned |
| `pyproject-build-system` content | contributed by `library-v2` |
| `.coveragerc` | owned by `coverage` |
| `ci.yml` | owned by `github` |
| `github:ci-steps` content | contributed by `coverage` |

Files common to the unextended and extended fixture generations remain
byte-identical. Every delta is either a selected component's owned file or a
declared extension contribution. The private catalogue overrides used by the
test module remain unsupported test seams; the downstream harness neither
imports nor knows about them.

## Client-owned responsibilities

No-copy reuse removes duplicated engine content, not client responsibilities.
A downstream client still owns:

- policy-source discovery, authenticity, and trust;
- tracking whether each selection was explicitly supplied;
- policy parsing and resolution until a public resolver is accepted;
- construction of the effective ProjectSpec and its provenance;
- compatibility negotiation and user-facing unsupported-version reporting;
- destination selection, staging, atomic replacement, and cleanup; and
- finalisation artefacts such as `uv.lock`.

These are orchestration responsibilities. They are not copies of Foundation,
component source, composition rules, or rendering logic. `create-forge` is one
reference client and may implement them independently; another client need
not import it.

## Ownership and change process

`forge-template` owns the package-bound Foundation/component content, public
engine facade, ProjectSpec and manifest protocols, compatibility rules, and
the no-copy invariant. Downstream clients own selection inputs and
orchestration on their side of that boundary.

A future public resolver or component-distribution mechanism requires its own
contract and ADR. It must not be inferred from the private test catalogue or
from this proof. The current API, package version `0.3.2`, and every protocol
version remain unchanged.
