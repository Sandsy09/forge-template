# 67. Validate the integrated engine-default cutover

Date: 2026-09-14

## Status

Accepted

Executes the two FT-18.01-owned rows of the acceptance matrix
[cutover-compatibility-and-acceptance.md](cutover-compatibility-and-acceptance.md)
(FT-15.04 / [ADR 0061](0061-provider-compatibility-failure-and-release-gates.md))
fixed. It does not supersede any prior record; it is the validation issue
[ADR 0066](0066-validate-provider-parity-reproducibility-and-distributions.md)
(FT-17.05) and
[the `0.5.0` release record](../cutover-provider-release.md) (FT-17.06) each
deferred rows to. Last child of
[FT-EPIC-18](https://github.com/Sandsy09/forge-template/issues/143), and the
gate `create-forge`'s own `CF-18.07` publication was left waiting on.

## Context

FT-17.06 published an immutable provider: `forge-template` `0.5.0` on PyPI,
digests recorded in
[cutover-provider-release.md](../cutover-provider-release.md). Seven
`create-forge` issues (CF-18.01 through CF-18.07) then built a candidate
client — `create-forge` `0.4.0`, engine bound widened to
`forge-template>=0.5,<0.6`, the engine promoted to the default `new` path,
`--engine-preview` removed, a `--legacy` escape hatch added, and a
post-rename `git init` + commit lifecycle (CF-18.03). That candidate is
**prepared but deliberately untagged**: CF-18.07 left its own publication
gated on this issue, so it exists only as a sibling working-tree commit, not
a published artefact.

Nothing had yet proven the two halves work together. Every existing proof is
one-sided:

- FT-17.05 proved the provider Engine/Generated-project rows against its own
  **working tree** ([provider-acceptance-validation.md](../provider-acceptance-validation.md)).
- `create-forge`'s own CF-18.06 proved the client against an **index-resolved**
  `forge-template==0.5.0` (`../create-forge/docs/engine-cutover-validation.md`).
- `poe crossrepo`
  (FT-14.02 / [ADR 0057](0057-validate-the-cross-repository-data-science-line.md))
  still calls the now-removed `--engine-preview` flag and asserts the
  pre-CF-18.03 no-`.git` project shape — broken by the very client changes
  this issue must validate against, and recorded as a further, deepened lag
  in [cutover-provider-release.md](../cutover-provider-release.md#recorded-during-preparation-the-crossrepo-lag-deepened-as-expected).

FT-18.01's own acceptance criteria require pairing the candidate client with
the **immutable released** provider, proving deterministic render/update
inputs, generic descriptor consumption, output ownership and generated
checks/builds without a Forge runtime dependency, and recording exact client
commit, provider artefacts and supported matrix — all without releasing
anything or editing the sibling `create-forge` checkout (the standing
constraint ADR 0066 decision 3 set).

## Decision

Re-execute every acceptance-matrix row observable through the `create-forge`
boundary against the digest-verified, PyPI-published `0.5.0` paired with the
candidate `0.4.0` client, and repair `poe crossrepo` for the CLI and
lifecycle changes that broke it. Record the six confirmed calls here.

1. **Scope the integrated matrix to the client-observable boundary, and
   re-prove the provider-side Engine/Generated-project rows against the
   released artefact rather than the working tree.** Six representative
   compositions (`library-minimal`, `library-github-max` — every compatible
   capability, the one full build-and-`poe check` cell —, `library-renovate`,
   `cli-full`, `data-science-min`, `data-science-rich`), chosen to reach
   catalogue edges the historical ten-composition `crossrepo` set does not
   (the `renovate` arm, a full `github`-platformed `cli` project, both Data
   Science floors). Rejected: re-running the 2240-composition sweep through
   the client (hours, and ADR 0066 decision 2 already proves it provider-side
   with no-resource-read guarantees that do not change at the client
   boundary); repeating all three FT-17.05 full-composition build cells
   (~45 minutes of pure duplication — one maximal cell here is enough to
   prove the *released, client-generated* artefact builds and checks
   cleanly, and the provider-side proof of "every archetype × every capability"
   stands); asserting only that `forge-template==0.5.0` resolves (CF-18.06
   already does exactly that — it proves a version string, not the specific
   published artefact this issue is answerable for).

2. **Verify the published artefacts by digest, three ways, and install the
   wheel from a verified file path, never an index specifier.**
   `tests/released_provider.py` fetches PyPI's own JSON metadata for
   `forge-template==0.5.0`, asserts its reported size and SHA-256 match the
   identities [cutover-provider-release.md](../cutover-provider-release.md)
   recorded *before* downloading a single byte (catches a re-upload or a
   yank immediately), downloads, and re-hashes the bytes themselves. A
   digest mismatch is a hard failure, never a skip; a transport failure
   (network unreachable) skips, since it proves nothing about the artefact
   either way. Rejected: `uv pip install forge-template==0.5.0` (lets the
   resolver choose the bytes off whatever index is configured; cannot detect
   a substituted or re-uploaded file); trusting FT-17.06's own
   published-artefact audit without re-asserting it here (that audit is the
   *input* the identities pinned in this module come from, not a substitute
   for re-checking them at the moment of pairing).

3. **Two suites, two purposes: repair `crossrepo`, add a separate `cutover`
   marker.** `tests/test_cross_repository_validation.py` keeps proving
   *working tree against working tree* — the cheapest, fastest signal a
   provider regression exists before either side releases — repaired for the
   removed `--engine-preview` flag and the CF-18.03 `.git` / committed
   `.forge/generation.json` project shape it now produces.
   `tests/test_released_provider_cutover.py` (row 339) and
   `tests/test_released_client_compatibility.py` (row 338) are new, under a
   new `cutover` marker, proving *released provider against candidate
   client*. Rejected: parametrising one module over both pairings (the
   fixtures — local path install vs. digest-verified download plus a built
   candidate wheel —, the project-shape assertions, and CI eligibility all
   differ enough that a shared parametrisation would obscure more than it
   shares); deleting the crossrepo suite in favour of the new one (it is the
   only proof that catches a provider regression *before* a release exists
   to pair against, and ADR 0057's reasoning for keeping it out of CI is
   unaffected by this issue).

4. **Row 338 (the `0.4.1`-pin regression) gets a CI job; row 339 (the
   integrated pairing) stays opt-in, like `crossrepo`.** Row 338 depends on
   nothing but immutable, already-published PyPI artefacts — the released
   `forge-template 0.5.0` and the released `create-forge 0.3.2` — so ADR
   0057's "CI must not depend on a moving sibling `main`" simply does not
   bind it, and the 90-day `0.4.x` support window
   ([cutover-compatibility-and-acceptance.md](../cutover-compatibility-and-acceptance.md#reproducibility-and-rollback))
   is a standing promise that deserves a standing, automated tripwire rather
   than a manually re-run check. Row 339 needs the unpublished candidate
   client, built from the sibling checkout, so it cannot be hermetic.
   Rejected: putting row 339 in CI behind a checkout of `create-forge` at a
   pinned ref (re-introduces exactly the moving-sibling-`main` coupling ADR
   0057 forbids, and a pinned ref would silently stop tracking CF-18.07's
   eventual publication); leaving row 338 opt-in alongside row 339 (a
   support-window guarantee nobody re-checks automatically is not really a
   guarantee).

5. **The standing no-sibling-edit constraint (ADR 0066 decision 3) is made
   executable, not just promised in prose.** The candidate-client wheel
   fixture captures `git status --porcelain` in the sibling checkout before
   and after `uv build --wheel --out-dir <tmp>`, and asserts the two are
   identical — building the candidate must not leave a `dist/` directory,
   an `.egg-info`, or any other artefact inside the checkout itself. The
   exact commit built is recorded, never pinned, so a later CF-18.07 commit
   does not spuriously red this suite. Rejected: relying only on the
   documented constraint (this is the issue that gives it a first executable
   check).

6. **A provider defect found here is not fixed here.** `0.5.0` is published
   and immutable — unlike ADR 0066's `pre-commit` fix, made when nothing had
   shipped yet, a defect this issue found would require a corrected reviewed
   release (`0.5.1`) through FT-17.06's protected `release.yml` chain, never
   an edit to the tagged `0.5.0`. No defect was found: every row passed on
   the first fully-corrected run. See "What ships" — the three real bugs
   this validation itself surfaced were all in *this issue's own test code*,
   not in either repository's product code, and are recorded below rather
   than in a "defect this validation found" section, since none of them
   affected either release.

### What this validation itself found

Building the six-composition matrix surfaced three genuine bugs in this
issue's own harness — not in `forge_template` or `create_forge` — each
caught by a real, failing run against the released artefacts rather than
assumed correct in advance:

- The `github` platform's one required component option, `organisation`,
  was never supplied to any `github`-platformed composition, so every such
  generation failed at validation. Fixed by passing
  `--component-option github.organisation=<value>` whenever `github` is
  selected — the same requirement
  [platform-and-tooling-parity.md](../platform-and-tooling-parity.md)
  documents and `tests/test_full_composition_build.py` already supplies.
- Three new rejection cases assumed `create-forge`'s client-owned "Add
  `--flag` value." hint text applies to any `requires`/`conflicts`
  violation. Running the `dependabot`-without-`github` case against the
  released pair showed it does not: `_missing_requirement_hint`
  (`create-forge/src/create_forge/cli.py`) covers only the *selected
  archetype's own* direct requirement (e.g. `data-science` → `jupyter`),
  never a capability's `requires` edge onto another component. The
  assertion was corrected to the engine-owned message only, with the
  distinction recorded inline as a comment.
- `CF-18.03`'s post-rename lifecycle creates `.venv` via
  `uv run --directory <dst> pre-commit install --install-hooks` whenever a
  rendered `.pre-commit-config.yaml` is present — a project-shape fact this
  issue's fixture initially got backwards (asserting `.venv` never exists)
  and initially left out of the determinism byte-comparison (`.venv`'s own
  contents, e.g. `activate` scripts, are venv-specific, not rendered bytes).
  Both fixed: the shape assertion is now conditional on whether
  `pre-commit` was selected, and `.venv/**` joins `.git/**` and `uv.lock` in
  the determinism comparison's exclusions.

None of the three affected the released `0.5.0` provider or the candidate
`0.4.0` client — each was a gap in this issue's own new test code, closed
before any row was recorded as passing.

### What ships

- `tests/released_provider.py` — the shared harness: digest-verified PyPI
  download (`download_verified_artefact`), the venv/subprocess helpers both
  new suites share, and the pinned `ArtefactIdentity` records for
  `forge-template` `0.5.0`.
- `tests/test_released_client_compatibility.py` — row 338, `cutover`-marked,
  hermetic (PyPI only). Three tests: the `0.5.0` publication premise, the
  `0.4.1`-pin resolution proof (`create-forge[engine]==0.3.2`), and a
  generation through the released `0.3.2` client.
- `tests/test_released_provider_cutover.py` — row 339, `cutover`-marked,
  sibling-gated like `crossrepo`. Fifteen tests over six compositions:
  artefact identity, paired installation, negotiation facts, the fourteen-
  component catalogue, path-free descriptors, the two generation-metadata
  error codes, isolated import/render, per-composition generation shape,
  per-composition ownership, per-composition reproduction (a `.forge/
  generation.json` a *client* wrote, verified through the released engine
  for the first time), client-boundary update classification, determinism,
  the one full build-install-check cell, seven rejection cases (three new:
  `dependabot`/`github`, the `dependabot`/`renovate` conflict,
  `documentation`/`library`), and the no-resource-read `create-forge list`
  proof.
- `tests/test_cross_repository_validation.py` — repaired: `--engine-preview`
  removed from every invocation; the project-shape assertion now expects
  `.git` and `.forge/generation.json` (CF-18.03); the determinism comparison
  excludes `.git/**` as well as `uv.lock`.
- `tests/conftest.py` — `create_forge_root`'s docstring and
  `--create-forge-root`'s help text now name both sibling-gated consumers.
- `pyproject.toml` — a new `cutover` pytest marker, a `poe cutover` task
  (both modules; the sibling-gated one self-skips), and `poe test`'s
  deselect list extended.
- `.github/workflows/test-template.yml` — a new `released-client` job
  (row 338 only, hermetic) and `all-green`'s `needs` extended.
- `docs/integrated-cutover-validation.md` — the evidence record: validated
  pair, verified artefact identities, both rows' per-test results, what was
  cited rather than re-executed, what `poe crossrepo` now shows, and scope
  held.
- `docs/cutover-provider-release.md` and
  `docs/provider-acceptance-validation.md` — forward-linked to this record
  from the open items they each deferred to FT-18.01.

### Recorded narrowings

- Row 339's exhaustive half (every one of the 2240 compositions, through the
  client) is not re-executed — cited to ADR 0066 decision 2's provider-side
  sweep, which proves the same no-resource-read composition logic the client
  boundary adds no new code path over.
- The two archetypes other than `library` do not get their own full
  build-and-`poe check` cell here — cited to FT-17.05's three provider-side
  cells (`provider-acceptance-validation.md`'s "Full-composition build
  cells").
- The unavailable/out-of-range-provider fail-closed path is not re-proven
  here — already covered client-side by CF-18.06's installed-cutover suite.
- Row 339 cannot run in CI: the candidate client is unpublished and must be
  built from the sibling checkout. This self-resolves once CF-18.07
  publishes `0.4.0` — a future issue could then make the pairing hermetic
  the way row 338 already is.

## Consequences

- No engine, catalogue, protocol, or rendered-content change. No component
  version moves. `main` stays `0.5.0` and already tagged — this issue
  releases nothing.
- `poe check` is unaffected (no new fast tests); `poe crossrepo` returns to
  fully green (20/20, was 1/19 after the `0.5.0` publication per
  [cutover-provider-release.md](../cutover-provider-release.md#recorded-during-preparation-the-crossrepo-lag-deepened-as-expected));
  a new `poe cutover` task and `cutover` marker carry this issue's two new
  suites.
- `.github/workflows/test-template.yml` gains one new required job
  (`released-client`); `all-green` now also requires it.
- The gate row at
  [cutover-compatibility-and-acceptance.md#cross-repository-release-gates](../cutover-compatibility-and-acceptance.md#cross-repository-release-gates)
  moves to done: the released provider paired with the candidate client
  passes the full cross-repository matrix together, with no provider defect
  found and so no corrected release required.
- `FT-EPIC-18` and `CF-EPIC-18` both lose their last blocking child;
  `create-forge`'s own `CF-18.07` publication gate — held open pending this
  record — is released.
