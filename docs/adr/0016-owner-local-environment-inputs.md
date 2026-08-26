# 16. Keep environment inputs owner-local and dotenv explicit

## Status

Accepted

## Context

[ADR 0015](0015-owner-local-runtime-configuration.md) assigns runtime
configuration to the archetype or capability consuming it and requires the
runtime entrypoint to assemble typed fragments once. It deliberately left
environment-variable names, source precedence, local dotenv behaviour, safe
examples, and environment identity to a later decision.

A universal environment schema would recreate the Foundation settings layer
that ADRs 0012 and 0015 reject. Letting every component choose unqualified
names or load files independently would instead make collisions, precedence,
startup validation, and secret handling unpredictable. Provider-specific
deployment stages or implicit dotenv cascades would also couple generated
runtime behaviour to assumptions that do not hold across platforms.

The current Library scaffold has no runtime configuration consumer or dotenv
dependency. Its ignored `.env` and inert `.env.example` provide security and
documentation evidence, but do not establish a runtime loading contract.

## Decision

Adopt the
[environment-variable and local dotenv conventions](../environment-variables.md)
as the canonical living contract.

Only an archetype or capability with environment-backed runtime configuration
uses the convention. Each owner declares a stable uppercase prefix and names
variables `<OWNER_PREFIX>_<SETTING>`. Forge defines no project-wide runtime
namespace, and `FORGE_*` remains reserved for Forge tooling. An owner may use
canonical external-standard names only for a documented, faithful integration
with that standard. A variable has one owner; incompatible claims fail rather
than overwrite or alias implicitly.

Inputs resolve from owner defaults, then an explicitly enabled project-root
`.env`, then the process environment, then explicit runtime-entrypoint inputs.
The entrypoint validates the assembled typed fragments once. Import-time
environment reads are not allowed, and an explicitly present empty value is
validated rather than treated as absent.

Environment-backed projects use at most one local root `.env` and one tracked
root `.env.example`. Forge never generates, commits, overwrites, or shell-runs
`.env`; deployed environments use process variables, and no environment label
selects a staged dotenv file. Examples use portable assignments and comments,
show secret-bearing names only as commented empty keys, and contain no secret
values. Future composition assembles owner contributions into the example and
rejects collisions.

An optional environment identity is an open provider-neutral logical label,
not a closed enum, provider identifier, authorisation boundary, or switch that
weakens validation. Conventional values may include development, test,
staging, and production, while owners and organisations may document others.

This decision changes no current template file, Copier answer, generated
output, ProjectSpec, component manifest, runtime dependency, schema, public
API, or CLI behaviour.

## Consequences

- Environment-backed components gain predictable names and precedence without
  imposing configuration on projects that do not need it.
- Process variables remain the provider-neutral deployment interface, while
  local dotenv loading is explicit and cannot occur as an import side effect.
- A single example file remains approachable for users even though each entry
  retains component ownership.
- Component authors must document variables, sensitivity, standards
  exceptions, and validation, and must coordinate shared inputs through typed
  interfaces.
- Stage 06 must compose example contributions and reject collisions; FT-04.04
  must define project-root path resolution; FT-05.04 retains broader secret
  safeguards and optional scanning.
- The current Library `.env.example` remains an inert monolithic-scaffold
  artefact until later component migration.
