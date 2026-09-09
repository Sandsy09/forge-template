# 60. Platform composition and generated-tooling parity

Date: 2026-09-09

## Status

Accepted

Extends the extension-point inventory in
[ADR 0049](0049-foundation-capability-tooling-extension-points.md) and reverses
exactly one limitation it recorded: a capability may now declare a named
dependency group, through two reserved Foundation points. ADR 0049 otherwise
stands, and it is not edited.

## Context

[FT-15.01](https://github.com/Sandsy09/forge-template/issues/146) /
[ADR 0058](0058-inventory-default-copier-parity.md) inventoried every
default-Copier behaviour in
[engine-default-parity.md](../engine-default-parity.md) and assigned each to the
provider, the client, or an explicit exclusion.
[FT-15.02](https://github.com/Sandsy09/forge-template/issues/147) /
[ADR 0059](0059-generation-provenance-and-reproducible-updates.md) closed the
four provenance rows.

What the matrix leaves open is the whole optional-tooling and host-integration
half of the scaffold. Twenty-six provider-owned `gap` rows point at
`FT-15.03 → FT-17.02`, `FT-15.03 → FT-17.03`, or the literal marker
`needs a bounded issue`, and the inventory reserved three design calls by name
for this issue: the concrete GitHub platform descriptor and its Foundation
extension points; whether `type_checking` becomes a capability or an accepted
mypy-only narrowing; and the MkDocs / documentation layout. The engine's
`ProjectSpec` already accepts a `platforms` tuple, but `discover_components()`
returns no platform at all, so generated CI, CODEOWNERS, issue and
pull-request templates, and every host-scoped link have nowhere to live.

[FT-15.03](https://github.com/Sandsy09/forge-template/issues/148) is the
`type:decision` issue that assigns them. Its review obligations are
**FT-ROADMAP-01-AC-03** (platform selection and composition stay
manifest/catalogue-owned and are exposed only through public path-free
descriptors, shared with
[FT-17.02](https://github.com/Sandsy09/forge-template/issues/151)) and
**FT-ROADMAP-01-EX-03** (no Streamlit or other new archetype, owned solely
here).

The stage is contract-only. Its exclusions forbid any runtime implementation,
generated-content change, protocol increment, package version bump or release,
and forbid preselecting Streamlit layout, merge algorithms or deprecation dates
without an accepted decision. The routing table in
[foundation-scope.md](../foundation-scope.md#routing-non-foundation-concerns)
already assigns GitHub adapters to a platform and coverage / pre-commit / docs /
changelog / dependency-update automation / configuration examples to
capabilities; this decision makes that concrete, it does not re-open it.

Nine choices had to be made and were confirmed with the maintainer before
planning.

## Decision

Publish the assignment as a living contract,
[platform-and-tooling-parity.md](../platform-and-tooling-parity.md), and record
the choices here.

1. **One `github` platform component** owns every GitHub-specific file. Its
   content is tiered internally against `engine-default-parity.md`:
   `.github/workflows/ci.yml` and `.github/CODEOWNERS` are `cutover-blocking`;
   the three `.github/ISSUE_TEMPLATE/` forms and
   `.github/pull_request_template.md` are `deferred`. Rejected: a separate
   `github` / `github-actions` split (contradicts six living docs that already
   name one `github` platform, and doubles the surface FT-17.02 builds); a
   host-neutral `ci` capability behind the platform (invents a second
   abstraction layer before a second host exists, and no filed issue scopes
   it).

2. **The platform takes exactly one required `organisation` option.** The
   repository URL (`https://github.com/<organisation>/<repository_name>`) and
   the CODEOWNERS handle are derived inside the platform's own templates from
   `organisation` and `project.repository_name`. Expressible in option-schema
   protocol `2` today — the existing `github` reference fixture already declares
   exactly this option — so no protocol increment and no new `ProjectSpec`
   field. Rejected: an optional `codeowners_team` and/or `repository_url`
   override (a non-github.com URL arguably means a different platform
   component, and the contract would have to state how a template safely reads
   an option that resolves to an omitted key — deferred to FT-17.02 if a real
   need appears). Copier's `codeowners_team` free-text override is a recorded
   parity narrowing.

3. **Three new Foundation extension points carry host links**, for full parity:
   `pyproject-project-urls` on `content/pyproject.toml.jinja`,
   `contributing-project-shape` on `content/CONTRIBUTING.md.jinja`, and
   `security-project-shape` on `content/SECURITY.md.jinja`. README host links
   reuse the existing `readme-project-shape`. This reverses
   [extension-points.md](../extension-points.md)'s statement that
   `CONTRIBUTING.md.jinja` and `SECURITY.md.jinja` are sole-owner content with
   no point — additive, exactly as ADR 0049 grew the inventory from eight
   points to eleven. Rejected: one point (`pyproject-project-urls` only), which
   would leave the CONTRIBUTING and SECURITY host links as an accepted parity
   narrowing rather than rebuilding them.

4. **A `pyright` capability**, not an accepted mypy-only narrowing. It
   contributes the pyright development dependency, its configuration, and a
   chained `typecheck` task on top of Foundation's unconditional mypy gate —
   the same shape [ADR 0006](0006-mypy-default-pyright-optional.md) already
   defined for the Copier path's `both` answer. Because Foundation's mypy gate
   cannot be switched off, Copier's mypy-*less* `pyright` answer stays
   unreachable in the engine path; the contract records that as a deliberate
   narrowing. Rejected: accepting a mypy-only engine (drops the `pyright` and
   `both` answers entirely); deferring the row to FT-15.04 (the parity
   inventory routes it here by name).

5. **One capability per concern, plus `dotenv-example`.** The capability set is
   `coverage`, `changelog`, `documentation`, `pre-commit`, `pyright`,
   `dotenv-example`, and the two dependency-update owners below — eight IDs,
   reusing the three (`coverage`, `changelog`, `documentation`) the reference
   fixture catalogue already models. `dotenv-example` owns a placeholder-only
   `.env.example` under [secret-handling.md](../secret-handling.md); it is a
   thin owner, but it gives that `cutover-blocking` parity row a concrete owner
   now rather than leaving it to a future runtime component that consumes
   environment input. Rejected: bundling into `quality-tooling` and
   `project-docs` (couples independent concerns and cannot reproduce Copier's
   four independent answers).

6. **Two dependency-update capabilities with real edges.** `dependabot` owns
   `.github/dependabot.yml` and declares
   `requires = [{ id = "github", version = ">=1,<2" }]`; `renovate` owns
   `renovate.json` and declares no host requirement; the two declare a mutual
   `conflicts`. Selecting neither reproduces Copier's `none`. This is the first
   production use of `conflicts` and the concrete instance of the cross-tier
   `requires` case
   [composition-order.md](../composition-order.md#cross-tier-dependencies)
   already documents. Rejected: one `dependency-updates` capability with a
   `provider` option (makes one capability own a GitHub-specific path with no
   way to express the host dependency); splitting Dependabot onto the platform
   and Renovate into a capability (splits one question across two tiers and
   needs a second platform option to express `none`).

7. **Two new Foundation points inside `[dependency-groups]`** —
   `pyproject-named-dependency-groups` for a new `name = [ ... ]` group and
   `pyproject-dependency-group-includes` for an `{ include-group = "name" }`
   line in Foundation's `dev` group — so the `documentation` capability
   declares a real `docs` group that `uv sync --group docs` resolves. This
   **reverses ADR 0049's stated limitation** that "a capability still cannot
   declare its own named dependency group"; the rest of ADR 0049 stands.
   Rejected: contributing the mkdocs dependencies straight into Foundation's
   `dev` group (loses the separately installable `--group docs` target that
   the Copier scaffold provides); a named group not included in `dev` (a
   generated project's default `uv sync` would stop installing the docs
   toolchain).

8. **The pin is a doc-derived check plus a synthetic fixture catalogue**,
   following FT-11.04 / ADR 0052's precedent. Four test-only components under
   `tests/fixtures/platform_composition/`, deliberately *not* named
   `github` / `dependabot` / `renovate` — naming them so would be
   indistinguishable from shipping the decided catalogue, which the exclusions
   forbid — overlay a copy of the real production catalogue with the real
   Foundation source live. Rejected: a doc-only pin (proves nothing about how
   the decided descriptors compose); extending
   `tests/fixtures/component_manifests/` (churns the golden fixtures this
   contract-only issue must leave alone).

9. **The `github` platform publishes both `ci-jobs` and `ci-steps`** on its own
   `ci.yml` content. `library-archetype.md` already names `ci-jobs` for a whole
   workflow job; `file-conflicts.md` and `no-copy-inheritance.md` describe a
   `coverage`-style capability contributing a single *step* into `ci-steps`,
   and the reference fixture publishes `ci-steps`. Publishing both is the only
   outcome that leaves every existing document true and needs no
   golden-fixture change. It also adds `api-reference` on the `documentation`
   capability, already named by `library-archetype.md`.

The net extension-point effect is Foundation eleven → sixteen, plus `ci-jobs` /
`ci-steps` on `github` and `api-reference` on `documentation`. **All eight are
reserved, not published.** `foundation.toml` is unchanged by this issue;
FT-17.02 and FT-17.03 publish them when they build the components.

This decision changes no runtime code, no generated content, no protocol
integer, no component or package version, no `copier.yml` question, and no
`foundation.toml`. It adds one living contract, this record, one test module
with a four-component synthetic fixture catalogue, and the wiring that links
them.

## Consequences

- FT-17.02 inherits a bounded scope: implement one `github` platform with one
  option, the two CI points, and the three Foundation host-link points; wire
  `PythonSelection.tested_versions` into a Linux-only CI matrix under
  [github-action-pinning.md](../github-action-pinning.md). FT-17.03 inherits
  the eight-capability set, the two dependency-group points, and the
  `api-reference` point.
- FT-15.04's remaining scope shrinks to the compatibility-line classification
  and the bounded issues the `needs a bounded issue` rows still require —
  which now all resolve to `documentation` (the MkDocs rows) or the
  `dependabot` / `renovate` pair, so FT-15.04 may be able to close them by
  reference rather than filing new issues.
- The five reserved Foundation points are a backward-compatible addition to the
  extension-point-inventory axis in
  [compatibility-policy.md](../compatibility-policy.md); publishing each still
  requires the package-version bump that document already mandates for any
  Foundation change a client can observe.
- `engine-default-parity.md`'s row cells are unchanged: those surfaces are
  still gaps until FT-17.02 / FT-17.03 ship, and
  `tests/test_parity_inventory.py` still pins every row against a real render.
- Copier's mypy-less `pyright` type-checking answer and its free-text
  `codeowners_team` override are recorded parity narrowings, not rebuilt.
- `tests/test_platform_composition.py` fails deliberately when
  `foundation.toml` gains one of the five reserved points, or when
  `discover_components()` returns anything other than exactly three archetypes,
  two capabilities and zero platforms — keeping the contract and the
  implementation in step, and enforcing FT-ROADMAP-01-EX-03.
- No template, Copier answer, component resource, engine module, dependency,
  golden digest, `foundation.toml`, tag, or release changes.
