# 81. Define batch composition, compatibility and acceptance

Date: 2026-09-29

## Status

Accepted

Classifies one compatibility-line transition against the rules in
[ADR 0041](0041-forge-blueprint-compatibility-policy.md), which continues to
govern how every axis moves and is not superseded. Closes
[FT-EPIC-27](https://github.com/Sandsy09/forge-template/issues/189).

## Context

[FT-27.02](https://github.com/Sandsy09/forge-template/issues/200) is the
second and last child of the Stage 27 epic. [ADR 0080](0080-batch-project-shape.md)
fixed the archetype's shape and deliberately left the capability matrix, the
manifest protocol, the Python and dependency window, the provider
compatibility line and the acceptance matrix to it. Stage 28
([FT-EPIC-28](https://github.com/Sandsy09/forge-template/issues/190)) and its
children FT-28.01–03, already filed, cannot start until they are answered,
and its first child is blocked on this decision.
[streamlit-compatibility-and-acceptance.md](../streamlit-compatibility-and-acceptance.md)
(FT-19.02 / ADR 0069) is the direct precedent for the shape: an axis table,
an executable matrix and named gates.

Facts were verified against the live engine on 29 September 2026: published
`create-forge` `0.5.0` declares `forge-template>=0.6,<0.7` (per project
memory of its release), so it cannot drift into a new minor line; the batch
archetype declares no runtime dependency (ADR 0080), so there is no
dependency-resolution evidence to gather — the only Python-support question
is whether the standard-library job runs at the supported endpoints, which it
trivially does; and a synthetic-descriptor projection against the live
`discover_components()` catalogue (the same technique ADR 0069 §10 used for
Streamlit's pre-implementation count) shows that a `batch` archetype with no
`requires` or `conflicts` adds exactly **640** valid compositions — the same
shape as `cli` and `streamlit`, because `documentation` (which requires
`library`) is unavailable to it and no other edge touches it. Six choices had
to be made.

## Decision

Publish the classification as a living contract,
[batch-compatibility-and-acceptance.md](../batch-compatibility-and-acceptance.md),
and record the choices here.

1. **The batch line publishes `forge-template` `0.7.0`**, a new minor
   compatibility line. Published `create-forge` `0.5.0` declares
   `>=0.6,<0.7`, so it cannot drift into `0.7.0` and adopts deliberately at a
   future `CF-29.01` (already filed as
   [create-forge#204](https://github.com/Sandsy09/create-forge/issues/204)),
   the same opt-in step the Streamlit line used at CF-21.01. Rejected: `0.6.1`
   (a new archetype is client-observable through `discover_components()`, and
   the policy already treats that as needing a minor bump, not a patch);
   `1.0.0` (still a later decision, as ADR 0061 and ADR 0069 §1 both left it).

2. **`batch` enters at component version `1.0.0` on manifest protocol `2`**,
   with no option schema, `requires`, `conflicts`, rename or regeneration
   record. `job.py` is owner-edited starter code exactly like `cli.py`,
   `app.py` and the Data Science notebook — none of which accumulate content
   across updates the way `CHANGELOG.md` does — so it follows `library`,
   `cli`, `data-science` and `streamlit` onto the default `replace`
   disposition. Rejected: protocol `3` with `skip-if-exists` on `job.py`
   (this was considered because batch's *runtime output* has overwrite
   semantics, but `data/output.json` is produced by running the generated
   job, not by the templating engine — it is never a manifest-owned
   `[[regeneration]]` target at all, so there is nothing for protocol `3` to
   protect here; ADR 0080 §7 already gives the runtime output its own
   atomic-overwrite rule, which is a different mechanism at a different
   layer).

3. **All `2^10` capability subsets and the `github` platform are available to
   `batch` under their own existing rules, with no relationship declared on
   the batch manifest**, giving exactly 640 valid compositions — proven
   against the live catalogue by the synthetic-descriptor projection in
   Context. `batch` + `documentation` is rejected by that capability's
   existing `requires` edge to `library`, exactly as it is for `cli` and
   `streamlit`. Rejected: a hard `requires` on any capability (batch's
   contract, per ADR 0080, needs no capability to function); a `conflicts`
   edge with `scientific-python` or `jupyter` (batch has no runtime
   dependency to collide with either).

4. **The Python floor is `>=3.11` and the executable endpoints are 3.11 and
   3.14**, the Data Science and Streamlit precedent. Unlike those two, batch
   declares no runtime dependency, so there is no third-party resolution
   evidence to gather — the standard-library-only job trivially resolves and
   runs at every supported endpoint. Rejected: skipping endpoint evidence
   entirely (the generated project's own lock, build and `poe check` still
   need proving at the floor and the ceiling, even with an empty dependency
   set).

5. **Build and install requirements are module-only.** The wheel and sdist
   contain `src/<package_name>/` and not `data/sample_input.json`, so the
   sample input is a source-tree file, exactly as Streamlit's launcher and
   configuration are. Rejected: shipping the sample data in the distribution
   (blurs the no-deployment boundary for no benefit — an installed wheel is
   not where the job is run from).

6. **The deterministic smoke is bounded at 5 seconds per job run and 600
   seconds for the whole project check**, tighter than Streamlit's 10-second
   `AppTest` bound because the job does strictly less work (no UI framework
   import or page render, just reading, transforming and writing a handful of
   JSON records). A timeout is a failure, never a retry. Rejected: reusing
   Streamlit's 10-second bound unexamined (batch's own workload is smaller,
   and a bound should reflect the thing it measures, not a borrowed number).

The batch line therefore moves exactly two axes — the package version to
`0.7.0` and the discovered components from fifteen to sixteen. Every other
axis and the whole public facade is unchanged, and that is a requirement on
Stage 28, not a prediction.

This decision changes no runtime code, generated content, engine module,
public signature, `EngineErrorCode`, protocol integer, component, dependency,
extension point, `copier.yml`, `template/` file or `foundation.toml`. The
package stays `0.6.0` and untagged.

## Consequences

- FT-EPIC-27 closes with both children complete. Its criteria are evidenced
  in the closing comment, not by editing the frozen issue bodies.
- FT-28.01 is unblocked with a fixed identity, manifest shape, capability
  matrix and provider line, and Stage 28 inherits a fully bounded scope: its
  three children (already filed as #201–#203) map directly onto this
  contract's acceptance matrix.
- The composition sweep will grow from 2880 to 3520 compositions when
  `batch` ships; `tests/composition_matrix.py`'s `EXPECTED_COMPOSITION_COUNT`,
  `scripts/check_wheel.py`'s component list and the compatibility-policy
  component rows are known tripwires Stage 28 must update in the change that
  moves them, the same discipline Stage 20 followed for Streamlit.
- `create-forge` Stage 29 has a named target: CF-29.01 (already filed) moves
  its engine bound from `>=0.6,<0.7` to `>=0.7,<0.8` once `0.7.0` is
  published.
- The sample input is documented as a source-tree file, so a wheel-installed
  project has the typed package but not the tracked example data.
- No template, Copier answer, component resource, engine module, dependency,
  golden digest, `foundation.toml`, tag or release changes.
