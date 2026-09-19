# 69. Define Streamlit composition, compatibility and acceptance

Date: 2026-09-19

## Status

Accepted

Classifies one compatibility-line transition against the rules in
[ADR 0041](0041-forge-blueprint-compatibility-policy.md), which continues to
govern how every axis moves and is not superseded. Closes
[FT-EPIC-19](https://github.com/Sandsy09/forge-template/issues/144).

## Context

[FT-19.02](https://github.com/Sandsy09/forge-template/issues/158) is the second
and last child of the Stage 19 epic. [ADR 0068](0068-streamlit-project-shape.md)
fixed the archetype's shape and deliberately left five questions to it: which
capability selections are valid, the Python and dependency window with the build,
lock and smoke requirements, the provider compatibility line, whether any cutover
implementation is genuinely required first, and the release gates. Stage 20 cannot
start until they are answered, and its first child is blocked on this decision.

The review obligations are **FT-ROADMAP-02-AC-01** (shared with FT-19.01),
**FT-ROADMAP-02-AC-04** (shared with FT-20.02 and FT-20.03) and
**FT-ROADMAP-02-EX-03** (no engine-default cutover, owned solely here). The stage
is contract-only: its exclusions forbid runtime implementation, generated-content
change, a protocol increment, a version bump or a release.
[data-science-compatibility-and-acceptance.md](../data-science-compatibility-and-acceptance.md)
(FT-10.04 / [ADR 0048](0048-data-science-compatibility-and-acceptance.md)) is the
direct precedent for the shape: an axis table, an executable matrix and named
gates.

Facts were verified rather than assumed, on 19 September 2026: `forge-template`
`0.5.0` and `create-forge` `0.4.0` are both published, `create-forge` declares
`forge-template>=0.5,<0.6` and has made the engine its default path; Streamlit
`1.63.0` requires `numpy<3` and `pandas<4` and so does not collide with the
Scientific Python capability; all four selections resolve, wheels exist at Python
3.11 to 3.14, and the `1.63.0` floor itself resolves; and `uv_build` ships only
the module tree. Seven choices had to be made and were confirmed with the
maintainer before drafting.

## Decision

Publish the classification as a living contract,
[streamlit-compatibility-and-acceptance.md](../streamlit-compatibility-and-acceptance.md),
and record the choices here.

1. **The Streamlit line publishes `forge-template` `0.6.0`**, a new minor
   compatibility line. Published `create-forge` declares `>=0.5,<0.6`, so it cannot
   drift into `0.6.0` and adopts deliberately at
   [CF-21.01](https://github.com/Sandsy09/create-forge/issues/165), the opt-in
   step the `0.3.2` to `0.4.0` line used. Rejected: `0.5.1` (a new archetype would
   appear inside a range a released client already accepts, with no adoption step
   and no client-side validation); `1.0.0` (still a later decision, as
   [ADR 0061](0061-provider-compatibility-failure-and-release-gates.md) left it).

2. **`streamlit` enters at component version `1.0.0` on manifest protocol `2`**,
   with no option schema, `requires`, `conflicts`, rename or regeneration record.
   It follows `library`, `cli` and `data-science`, whose user-edited starter code
   keeps the default `replace` disposition. Rejected: protocol `3` with
   `skip-if-exists` on `app.py` and `config.toml` (makes Streamlit the second
   protocol-`3` component, is inconsistent with `cli.py` and the notebook, and
   would need cutover work no other archetype does).

3. **All four selections are valid** — none, `jupyter`, `scientific-python` and
   both — with no relationship declared on the Streamlit manifest. `streamlit` with
   `documentation` is rejected by that capability's existing `requires` edge to
   `library`. Rejected: a hard `requires` on `jupyter` (the Data Science pattern;
   Streamlit owns no notebook and the criterion asks for a no-capability selection);
   a `conflicts` edge with either capability (both resolve and pass).

4. **The Python floor is `>=3.11` and the executable endpoints are 3.11 and 3.14**,
   the Data Science precedent. Rejected: all four versions 3.11 to 3.14 (doubles
   the real project builds for a window where resolution evidence shows no interior
   gap). `streamlit>=1.63,<2` stands unchanged; admitting CPython 3.15 stays with
   [python-support.md](../python-support.md).

5. **Build and install requirements are module-only.** The wheel and sdist contain
   `src/<package_name>/` and not the root `app.py`, `.streamlit/config.toml` or any
   secret, so the launcher and configuration are source-tree files. Rejected:
   shipping them in the distribution (needs build configuration that blurs the
   no-deployment boundary and would install configuration into environments).

6. **Committed-lock restoration reuses the Data Science pattern**:
   `uv lock --python <endpoint>`, `uv sync --all-groups --locked` from a clean copy,
   then `uv run --locked poe check`. Rejected: leaving restoration to the client
   alone (the provider could then not prove a project restores).

7. **The non-serving smoke is bounded at 10 seconds per `AppTest` run and 600
   seconds for the whole project check, and a timeout is a failure, never a
   retry.** A prototype ran two cases in about 3 seconds; Streamlit's own default is
   3 seconds. Rejected: 5 s and 300 s (a thin margin invites flaky failures that get
   fixed by loosening); 30 s and 900 s (so loose a real server start would sit
   inside the bound).

8. **Release gates are provider-first, and cutover completion is not one.**
   `0.6.0` is published (FT-20.04) before the client adopts it (CF-21.01), validates
   it installed (CF-21.02) and releases (CF-21.03). Cutover has shipped on both
   sides, so the roadmap's "if cutover is not shipped, use the engine-preview path"
   clause is recorded as not applicable to the released client. Rollback follows
   [ADR 0061](0061-provider-compatibility-failure-and-release-gates.md) decision 5:
   immutable-forward, with `0.5.x` kept installable. Rejected: making FT-EPIC-18 a
   blocking gate (the roadmap forbids whole-epic gates that create a cycle).

9. **No cutover implementation dependency is added.** Manifest protocol `2`, the
   published extension points and the metadata contract all shipped in `0.5.0`, so
   `docs/roadmap-v4/**`, its hash-pinned mirrors and every `blocked_by` edge stay
   untouched. Rejected: adding an edge "to be safe" (needs both mirrors and their
   hashes rewritten and a checker change, for no scope gain).

10. **The pin is `tests/test_streamlit_gates.py`, a derived tripwire.** It reads its
    numbers from the contract's constants table, proves the four selections and the
    2880 count against the engine's own rule using a synthetic no-edge descriptor,
    and fails when the line or catalogue moves. Rejected: a document-consistency-only
    check (asserts nothing against the real engine, never fires).

The Streamlit line therefore moves exactly two axes — the package version to `0.6.0`
and the discovered components from fourteen to fifteen. Every other axis and the
whole public facade is unchanged, and that is a requirement on Stage 20, not a
prediction.

This decision changes no runtime code, generated content, engine module, public
signature, `EngineErrorCode`, protocol integer, component, dependency, extension
point, `copier.yml`, `template/` file or `foundation.toml`. The package stays
`0.5.0` and untagged.

## Consequences

- `FT-EPIC-19` closes with both children complete. Its criteria are evidenced in the
  closing comment, not by editing the frozen issue bodies: every mapped review
  criterion is owned and evidenced, and no release is claimed.
- FT-20.01 is unblocked with a fixed identity, manifest shape and provider line, and
  Stage 20 inherits a fully bounded scope: each child has a "fixed / still owned"
  row and every acceptance row names a real filed issue.
- The composition sweep will grow from 2240 to 2880 compositions when `streamlit`
  ships; `tests/composition_matrix.py`, `tests/test_cutover_gates.py`,
  `scripts/check_wheel.py` and the compatibility-policy component rows are known
  tripwires Stage 20 must update in the change that moves them.
- `create-forge` Stage 21 has a named target: CF-21.01 moves its engine bound from
  `>=0.5,<0.6` to `>=0.6,<0.7` once `0.6.0` is published.
- The launcher and `.streamlit/config.toml` are documented as source-tree files, so
  a wheel-installed project has the typed package but not a `streamlit run` target.
- No template, Copier answer, component resource, engine module, dependency, golden
  digest, `foundation.toml`, tag or release changes.
