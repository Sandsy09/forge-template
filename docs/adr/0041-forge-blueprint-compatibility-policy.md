# 41. Define the Forge-Blueprint compatibility policy

## Status

Accepted

## Context

`forge-template` publishes eight independently versioned surfaces (package,
ProjectSpec protocol, component manifest protocol, per-component PEP 440
version, option-schema protocol, Foundation source protocol,
organisation-policy protocol, extension-point inventory), but no document
stated how any of them are allowed to move, what a downstream client may
depend on, or how long a deprecated surface must keep working.
[python-support.md](../python-support.md) defines a 90-day deprecation window
for CPython releases only.
[template-engine-api.md](../template-engine-api.md) states the package's
current `0.3.x` compatibility line but not a general rule for future lines.
[composition-architecture-review.md](../composition-architecture-review.md)'s
Compatibility section is a point-in-time review record, not a living policy.

[docs/extension-points.md](../extension-points.md) already forward-referenced
[FT-09.04 / #47](https://github.com/Sandsy09/forge-template/issues/47) by
name as the owner of "any versioned commitment about what future Blueprint
releases may assume." [Blueprint](../terminology.md#blueprint) is a future
organisation-facing downstream consumer, not part of the current
two-repository implementation — this decision defines the contract such a
client consumes, not the client itself.

This gap was load-bearing for two open issues:
[create-forge#54 / CF-09.02](https://github.com/Sandsy09/create-forge/issues/54),
which must demonstrate "compatibility negotiation and structured
unsupported-version handling before side effects" and names this issue as its
blocker, and [FT-09.05 / #48](https://github.com/Sandsy09/forge-template/issues/48),
for which this was the last open blocker.

## Decision

Publish [compatibility-policy.md](../compatibility-policy.md) as the
canonical, living compatibility policy, and pin its claims executably in
`tests/test_compatibility_policy.py` — mirroring
[ADR 0039](0039-deny-policy-file-overrides.md)/`tests/test_extension_points.py`'s
precedent of a doc whose claims are asserted against real code, not merely
narrated.

Four scoping decisions:

- **No public API change.** The policy documents axes and constants that
  already exist (`get_engine_info()`, `discover_components()`,
  `PROJECT_SPEC_PROTOCOL_VERSION`, `COMPONENT_MANIFEST_PROTOCOL_VERSIONS`,
  `OPTION_SCHEMA_PROTOCOL_VERSIONS`, `FOUNDATION_SOURCE_PROTOCOL_VERSION`).
  No `EngineInfo` field is added, even though three axes stay unpublished:
  the option-schema and Foundation source protocols move in lockstep with the
  package version rather than independently, and the organisation-policy
  protocol has no executable engine-side parser to negotiate against today.
  Package version stays `0.3.2`; `create-forge`'s declared
  `forge-template>=0.3.1,<0.4` range is untouched.
- **Deprecation window: at least 90 days and at least one further tagged
  release.** Extends `python-support.md`'s existing 90-day notice period from
  CPython releases to every axis this document governs, adding a
  release-count floor because a calendar promise alone does not mean much
  against this repository's manual, irregular release cadence.
- **The policy defines required facts, not presentation.** What a conformant
  unsupported-version report must state (mismatched axis, detected value,
  supported value, remedy, fail closed before any side effect) is
  `forge-template`'s to define; wording, formatting, and exit codes stay
  client-owned. `create-forge`'s own
  [ADR 0011](https://github.com/Sandsy09/create-forge/blob/main/docs/adr/0011-engine-source-and-version-resolution.md)
  already reserves exit status `3` for this case, and this decision does not
  duplicate or reach into that reservation.
- **The direct-Copier `template/` path is out of scope**, pointer-only. Its
  compatibility mechanism — PEP 440 git tags plus `copier update`'s
  three-way merge — is unrelated to these axes and already governed by
  [ADR 0002](0002-copier-over-cookiecutter.md)/[ADR 0003](0003-two-repo-split.md)
  and CLAUDE.md's invariants 3 and 6.

Two findings from investigation directly shaped the document:

- **Foundation's absence of a client-visible version is existing design, not
  a gap this ADR introduces.**
  [component-manifests.md](../component-manifests.md#foundation) already
  states Foundation "carries no independent version a `requires`/`conflicts`
  reference could name." The policy states plainly that Foundation
  compatibility is therefore carried entirely by the package version.
- **The "negotiate before any side effect" guarantee is a provable property,
  not an aspiration.** Verified directly: with the component catalogue
  overridden to a nonexistent path, `get_engine_info()` still returns while
  `discover_components()` raises `ForgeEngineError` — so a client can always
  read package and protocol compatibility before ever touching component
  discovery, planning, or a destination.

## Consequences

- `forge-template` now has one canonical, living answer for what a client may
  depend on across every versioned axis, replacing scattered partial
  statements in `template-engine-api.md`,
  `composition-architecture-review.md`, and `component-manifests.md`, which
  now point at it rather than repeating it.
- This repository now owes every documented axis a 90-day-and-one-release
  deprecation window it did not explicitly owe before this decision.
- `tests/test_compatibility_policy.py` fails if the document's version table
  or negotiation claims drift from the real engine constants — the same
  drift-detection property `test_extension_points.py` already gives
  `extension-points.md`.
- [create-forge#54 / CF-09.02](https://github.com/Sandsy09/create-forge/issues/54)
  and [FT-09.05 / #48](https://github.com/Sandsy09/forge-template/issues/48)
  are unblocked on this decision; #48 was the epic's last blocked issue.
- No `EngineErrorCode` value, public function, or result field is added. No
  package version bump. No template, Copier answer, or generated-project
  behaviour changes.
- A future decision to publish the option-schema, Foundation source, or
  organisation-policy protocols independently, or to change the deprecation
  window or negotiation requirements, requires a new ADR superseding this
  one.
