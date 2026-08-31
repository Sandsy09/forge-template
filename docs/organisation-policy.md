# Organisation Policy Protocol v1

Organisation policy is a downstream, versioned input that constrains the
component selection from which a client constructs an effective
[ProjectSpec](project-spec.md). It is not a component, does not render content,
and never becomes a generated-project runtime dependency.

This document defines the strict JSON protocol and resolution semantics
accepted by [FT-09.01](https://github.com/Sandsy09/forge-template/issues/44).
[ADR 0038](adr/0038-organisation-policy-selection-model.md) records the
decision. The protocol is normative, but no parser, resolver, or public Python
API is implemented yet. The Stage 09 reference fixture and downstream-client
work will implement and validate this contract without changing ProjectSpec
protocol `1`.

## Wire model

An organisation-policy document is a JSON object with this shape:

```json
{
  "policy_version": 1,
  "id": "example-baseline",
  "description": "Optional human-facing explanation.",
  "defaults": {
    "archetype": "library",
    "capabilities": ["capability-a"],
    "platforms": ["platform-a"]
  },
  "required": {
    "archetype": "library",
    "capabilities": ["capability-b"],
    "platforms": []
  },
  "forbidden": {
    "archetypes": ["cli"],
    "capabilities": ["capability-c"],
    "platforms": ["platform-b"]
  }
}
```

The top-level fields are:

| Field | Requirement | Meaning |
| --- | --- | --- |
| `policy_version` | Required integer literal `1` | Organisation-policy wire protocol. |
| `id` | Required lower-case kebab-case string | Stable identifier recorded in ProjectSpec provenance. |
| `description` | Optional string | Human-facing context with no resolution authority. |
| `defaults` | Optional object | Component selections used when no higher-authority selection for that kind was supplied. |
| `required` | Optional object | Component selections the effective request must contain. |
| `forbidden` | Optional object | Component selections the effective request must not contain. |

At least one rule must be present across `defaults`, `required`, and
`forbidden`. An empty policy is invalid.

`defaults` and `required` each permit:

- zero or one `archetype` identifier;
- a unique set of `capabilities`; and
- a unique set of `platforms`.

`forbidden` permits unique sets named `archetypes`, `capabilities`, and
`platforms`. Multiple archetypes can be forbidden, but an effective
ProjectSpec still selects exactly one permitted archetype.

Every identifier uses ProjectSpec's lower-case kebab-case component syntax.
Component versions are absent: the installed engine release and its manifests
own component versions and compatibility.

## Strictness and canonical form

Protocol v1 rejects:

- omitted or unsupported `policy_version` values;
- unknown fields or implicit type coercion;
- malformed policy or component identifiers;
- duplicate identifiers within a collection;
- references to Foundation, profiles, or other policies as components; and
- documents with no selection rule.

JSON object-key order has no meaning. Capability, platform, forbidden-
archetype, and applied-policy collections are unordered sets. A canonical
serializer emits them in lexical order. The order of policy documents has no
precedence meaning.

The protocol deliberately contains no project metadata, Python selection,
component options, component versions, secrets, credentials, paths, file
content, import/include directives, executable hooks, or remote sources.
Those values cannot be smuggled through a selection policy.

## Resolution and authority

Policy is applied before a downstream client constructs the effective
ProjectSpec. The client must retain whether the user explicitly supplied each
selection kind; ProjectSpec itself contains only the resolved result and
cannot reconstruct that intent.

For each selection kind, authority remains:

```text
profile default
  < merged organisation-policy default
  < explicit user choice
  < required or forbidden organisation constraint
```

- A policy default replaces the lower-authority profile default for that
  selection kind.
- An explicit archetype or explicit capability/platform list replaces the
  applicable policy default. An explicitly empty list is still an explicit
  choice.
- Required and forbidden rules validate the resulting selection. They never
  silently add, remove, or replace an explicit selection.
- A violation fails before ProjectSpec construction, rendering, or filesystem
  work. A client may present required choices as fixed UI state, but the
  canonical outcome remains validation rather than hidden mutation.

On success, the client constructs the existing ProjectSpec protocol `1` and
records every applied policy ID in
`SelectionProvenance.policies`. That collection is canonicalised lexically;
it records provenance only and neither embeds a policy document nor grants
rendering authority.

## Multiple policies

Applied policies merge without caller-order precedence:

- policy IDs must be unique;
- capability and platform defaults, requirements, and prohibitions union as
  sets;
- forbidden archetypes union as a set;
- identical archetype defaults or requirements may coexist; and
- all canonical collections are sorted after merging.

The policy set is invalid when:

- distinct archetype defaults are declared;
- distinct required archetypes are declared;
- an archetype default differs from a required archetype;
- any default selection is also forbidden; or
- any required selection is also forbidden.

These contradictions fail independently of input order. No policy wins by
being loaded last.

For example, these documents combine deterministically:

```json
{
  "policy_version": 1,
  "id": "delivery-baseline",
  "required": {"platforms": ["platform-a"]}
}
```

```json
{
  "policy_version": 1,
  "id": "quality-baseline",
  "defaults": {"capabilities": ["capability-a"]},
  "forbidden": {"capabilities": ["capability-c"]}
}
```

The merged defaults contain `capability-a`, the required platforms contain
`platform-a`, and `capability-c` remains forbidden regardless of document
order.

By contrast, this policy cannot be combined with `delivery-baseline` because
the same platform is both required and forbidden:

```json
{
  "policy_version": 1,
  "id": "restricted-delivery",
  "forbidden": {"platforms": ["platform-a"]}
}
```

## Catalogue and ProjectSpec validation

Policy syntax alone cannot prove that a component exists or has the declared
kind. Application validates every referenced ID against the installed engine
catalogue and rejects unknown IDs, kind mismatches, or a rule set that leaves
no permitted archetype.

After policy resolution, the normal ProjectSpec and component-manifest
validation remains authoritative. Policy cannot bypass component dependencies,
conflicts, protocol or Python compatibility, option validation, file-conflict
rules, or Foundation guarantees. The current production catalogue contains
only the `library` and `cli` archetypes; capability and platform identifiers
in the examples are neutral placeholders for later fixture/catalogue work.

## Structured failures

Future policy resolution exposes deterministic, safe structured failures with
operation `resolve-organisation-policy`. Three categories separate failure
ownership:

| Category | Meaning |
| --- | --- |
| `invalid-organisation-policy` | One policy document violates the wire contract. |
| `organisation-policy-conflict` | Individually valid policies contradict one another. |
| `organisation-policy-violation` | A policy set is valid, but the proposed effective selection does not satisfy it or the installed catalogue. |

Each failure contains lexically/path-sorted details with `code`, `path`, and a
safe human-readable `message`. Stable detail codes are:

- document: `unsupported-policy-version`, `invalid-policy-id`,
  `invalid-field-type`, `unknown-field`, `duplicate-selection-id`, and
  `empty-policy`;
- policy set: `duplicate-policy-id`, `conflicting-archetype-default`,
  `conflicting-archetype-requirement`, `default-requirement-conflict`,
  `default-forbidden-conflict`, and `required-forbidden-conflict`; and
- effective selection: `unknown-component`, `component-kind-mismatch`,
  `required-selection-missing`, `forbidden-selection-selected`, and
  `no-permitted-archetype`.

Paths begin at the relevant policy ID or effective selection field. Messages
must not echo secrets or arbitrary external content. Existing
`ForgeEngineError`, `EngineErrorCode`, and public engine operations remain
unchanged until later Stage 09 work implements this contract.

## Ownership and deferred implementation

`forge-template` owns this generic policy wire contract and the future shared
validation semantics. A downstream client owns policy-source configuration,
trust decisions, user interaction, explicit-choice tracking, ProjectSpec
construction, diagnostics presentation, and filesystem orchestration.

Policy is not an arbitrary overlay. File replacement, merge/override grants,
and supported extension points are now defined by
[extension-points.md](extension-points.md), delivered through
[FT-09.02](https://github.com/Sandsy09/forge-template/issues/45): no override
grant exists, and the complete sanctioned extension surface is published
there. The generic reference fixture is owned by
[FT-09.03](https://github.com/Sandsy09/forge-template/issues/46), and the
downstream consumption hook by
[create-forge#53](https://github.com/Sandsy09/create-forge/issues/53).
