# 68. Define the Streamlit project shape and ownership

Date: 2026-09-19

## Status

Accepted

Records the decisions for
[FT-19.01](https://github.com/Sandsy09/forge-template/issues/157), the first
child of [FT-EPIC-19](https://github.com/Sandsy09/forge-template/issues/144).
The epic stays open: [FT-19.02](https://github.com/Sandsy09/forge-template/issues/158)
is not yet decided.

## Context

Roadmap-v4 begins only after the cutover contracts are accepted, and
[CF-16.03](https://github.com/Sandsy09/create-forge/issues/157) closed that
gate on 10 September 2026. The roadmap's architecture note deliberately
preselects nothing about Streamlit: layout, entry point, dependency ownership
and the validation strategy are all left to Stage 19, and the decision-only
exclusions forbid preselecting a Streamlit layout without an accepted decision.
This record supplies it.

The released `0.5.0` catalogue contains no Streamlit component, resource or
generated content. The direct precedent for the shape is
[ADR 0045](0045-data-science-project-shape.md), which fixed an independent
archetype's identity, packaging and ownership map as a living contract ahead of
its implementation. [ADR 0049](0049-foundation-capability-tooling-extension-points.md)
already lets an archetype, not only a capability, use Foundation's task and
dependency points.

The review obligations are **FT-ROADMAP-02-AC-01** (an accepted contract defines
the project shape, entry point, dependency and task ownership and deployment
boundary, shared with FT-19.02), **FT-ROADMAP-02-EX-01** (no cloud deployment,
container orchestration, authentication, database or FastAPI surface) and
**FT-ROADMAP-02-EX-04** (no arbitrary Streamlit plugin ecosystem). Nine choices
had to be made and were confirmed with the maintainer before drafting.

## Decision

Publish the shape as the living contract
[streamlit-archetype.md](../streamlit-archetype.md) and record the choices here.

1. **Identity is `streamlit` / Streamlit**, an optionless archetype. Rejected:
   `streamlit-app` (longer, and breaks the one-word pattern `library`, `cli`
   and `data-science` set; the component ID and the PyPI distribution are
   separate namespaces).

2. **The entry point is a tracked root `app.py` launcher** that calls
   `main()` from `src/<package_name>/app.py` under an `if __name__` guard, run
   by `streamlit run app.py`. Rejected: a package module run by path (a long,
   non-idiomatic command, and the target is executed as a script); a console
   script that shells out to `streamlit run` (hides Streamlit's own flags and
   adds a launcher module no other archetype has an analogue for).

3. **Packaging is `uv-build-static`** — `uv_build>=0.12,<0.13`, static
   `0.1.0`, `src/` layout, wheel and sdist, `py.typed`. Rejected: a
   non-packaged application with no `[build-system]` (leaves two extension
   points unfilled, diverges from every archetype and needs a Foundation
   decision about a pyproject with no build backend).

4. **The runtime dependency is exactly `streamlit>=1.63,<2`**, fixed here rather
   than in FT-19.02, as the CLI contract fixed `typer`. `1.63.0` was reviewed
   against PyPI on 19 September 2026 (`Requires-Python >=3.10`). Rejected:
   `>=1.64` (a floor four days old, narrowing the resolver for no stated
   benefit); `>=1.50` (a floor with no precedent this far from a reviewed
   release, weakening the claim the bound makes).

5. **Configuration tracks `.streamlit/config.toml` with
   `gatherUsageStats = false` and ignores `.streamlit/secrets.toml`; no secrets
   example is generated.** The `.env` file stays the single secret channel:
   Foundation ignores the `.env` family and negates `!.env.example`, and the
   optional `dotenv-example` capability owns the tracked `.env.example` file.
   Rejected: a tracked `secrets.toml.example` (a second channel
   to document, validate and keep in step, needing its own ignore negation);
   tracking no configuration (leaves Streamlit's telemetry at its upstream
   default and gives the archetype no deterministic configuration surface).

6. **The starter is a single page** — title, short introduction, one widget —
   with the `pages/` convention documented but not generated. Rejected: a
   starter `pages/` tree (commits a second page's content and naming, enlarges
   what FT-20.03 must validate, and tracks a file most projects delete); a bare
   title (demonstrates nothing and gives the test almost nothing to assert).

7. **The archetype contributes a `run` task and nothing to the aggregate
   `check`.** `run = "streamlit run app.py"` goes through
   `pyproject-task-definitions`; `check` must terminate, and a server task in it
   would hang every generated project's gate and CI. Rejected: naming it `app`
   (less conventional); contributing no task (leaves the project's primary
   action the one thing `poe` cannot do).

8. **Tests use `streamlit.testing.v1.AppTest` in `tests/test_app.py`.** It runs
   the script in process with no port, browser or subprocess, and ships inside
   `streamlit`, so it adds no dependency. A relative path passed to
   `from_file` resolves against the calling file, so the test builds the
   launcher path from `__file__`. Rejected: an import-and-version smoke test
   alone (never executes the app); owning both files (two owned tests where
   every archetype owns one, largely duplicating `AppTest`).

9. **The pin is `tests/test_streamlit_contract.py`, a tripwire.** It asserts
   against the live engine that `streamlit` is not yet in the catalogue and that
   every Foundation point the contract names exists, so it fails deliberately
   when FT-20.01 lands. Rejected: documents only, as ADR 0045 did (a
   document-consistency check that never fires, the failure
   [ADR 0061](0061-provider-compatibility-failure-and-release-gates.md)
   rejected).

The contract excludes cloud deployment, containers and orchestration,
authentication, databases, FastAPI and arbitrary Streamlit plugins or components
by name.

This decision changes no runtime code, generated content, engine module, public
signature, `EngineErrorCode`, protocol integer, component, dependency,
extension point, `copier.yml`, `template/` file or `foundation.toml`. The
package stays `0.5.0` and untagged.

## Consequences

- FT-19.02 is unblocked with a fixed shape on which to build its capability
  matrix, Python window, lock restoration and smoke strategy. It still decides
  the component version and the target provider line, which are not fixed here.
- FT-20.01 has an exact file list, manifest identity and set of Foundation
  contributions, and inherits the rule that no sibling archetype's resources
  are read.
- No new extension point is needed; the sixteen Foundation points already cover
  every concern, so the extension-point inventory and its pin are unchanged.
- `tests/test_streamlit_contract.py` fails when `streamlit` first appears in
  `discover_components()`, forcing the contract and implementation into step.
- Four documents that named the Streamlit layout as reserved for another owner
  now point at the accepted contract; the statements that no archetype ships yet
  remain true and are unchanged.
- `docs/roadmap-v4/**` and its hash-pinned issue mirrors are untouched.
  `FT-EPIC-19` stays open until FT-19.02 is complete.
