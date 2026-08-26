# Secret-handling safeguards

This is the canonical living contract for secret-handling safeguards in
generated Forge projects. It extends the
[environment-variable conventions](environment-variables.md), which define the
`.env` / `.env.example` local dotenv contract this decision hardens. [ADR
0020](adr/0020-generated-project-secret-safeguards.md) records why Forge
adopted this contract.

Unlike the other Stage 04/05 runtime-ownership decisions, this one **does**
change generated output: it broadens `template/.gitignore`, adds one
already-pinned pre-commit hook, and documents secret handling in the
generated `SECURITY.md`. It defines no new Copier question, runtime
dependency, or ProjectSpec/component-manifest field.

## Foundation provides neutral safeguards only

Foundation ignores conventional secret-bearing local files and warns against
committing a recognisable private key. It does not provide a vault client,
secrets manager, encryption helper, credential rotation, or any runtime
dependency. This is the [Foundation scope](foundation-scope.md#runtime-ownership)'s
existing distinction between a neutral safeguard and a runtime concern applied
concretely: the safeguard is Foundation's; the variable names, values, and any
schema around them stay with the component that consumes them, following the
[environment-variable conventions](environment-variables.md#names-belong-to-runtime-owners).

## Secret-bearing files stay out of version control

The generated `.gitignore` ignores the `.env` family (`.env`, `.env.*`) and
conventional credential and key artefacts (`*.pem`, `*.key`, `*.p12`, `*.pfx`,
`*.keystore`, `id_rsa`, `id_rsa.*`, `credentials.json`, `.direnv/`).

An ignore rule must never shadow a file the project intentionally tracks. The
broad `.env.*` rule is paired with an explicit `!.env.example` negation for
exactly this reason: without it, the tracked example would be silently
untracked the first time a project's own `.env.example` renders, and no
build or test step would notice, because an ignored file is invisible to
`git status`, not merely absent. Any future addition to this ignore list
must audit for the same hazard before merging.

## The tracked example carries placeholders only

[environment-variable conventions](environment-variables.md#safe-examples-and-user-documentation)
already states that `.env.example` "never contains a real, plausible,
generated, profile-supplied, or organisation-supplied secret value." This
decision makes that rule mechanically enforced rather than merely documented:
every non-comment, non-blank line in the generated `.env.example` must be a
bare `NAME=` assignment with an empty right-hand side.

## Local defence at commit time

The generated pre-commit configuration adds `detect-private-key` from the
already-pinned `pre-commit/pre-commit-hooks` repository. It satisfies every
[Foundation inclusion condition](foundation-scope.md#inclusion-rule): every
archetype benefits, it needs no new third-party dependency or `rev` to
maintain, it is provider- and framework-neutral, and its outcome — no
recognisable private key in a commit — is stable and testable. It is a local
safeguard only: it inspects the files being committed, not history, and does
not run in CI.

## Optional secret scanning

Broader scanning fails Foundation's universal, provider-neutral, and
stable-and-testable conditions: no single scanner is right for every project,
and a mandatory bundled scanner would put a third-party binary and its
false-positive surface in every commit path. Any scanner a project adopts
should have these properties:

- it runs at the pre-commit stage, not only in CI;
- it can scan full history, not only the current diff;
- it supports a reviewable allowlist or baseline for accepted false
  positives; and
- it produces the same result locally and in CI.

[gitleaks](https://github.com/gitleaks/gitleaks) is named as the
provider-neutral reference for a future optional capability satisfying these
properties. GitHub push protection and secret scanning (repository settings,
no generated file) are the parallel GitHub-platform contribution, following
the [platform](terminology.md#platform) boundary: an adapter to an external
hosting or delivery target, not part of the project's primary shape. Forge
generates neither today; both remain deferred implementation mechanics below.

## Generation-time inputs are never secret sources

Copier answers, ProjectSpec fields, profiles, and organisation policy are
generation-time selection inputs, exactly as
[environment-variable conventions](environment-variables.md#input-resolution-and-validation)
already states for runtime configuration. The concrete consequence for this
contract: `.copier-answers.yml` is committed by
[Foundation's update and provenance state](foundation-scope.md#forge-update-and-provenance-state),
so any answer supplied at generation time is permanently public in the
generated repository's history. A generation-time input must never carry a
real secret value.

## Secrets in diagnostics

Ignore rules and the private-key hook protect files; they say nothing about
values that reach logs, tracebacks, or CI output during normal operation.
That boundary is already stated in full by the
[exception ownership conventions](exception-ownership.md#messages-and-diagnostics-carry-no-secrets)
and reinforced, not replaced, by
[structured logging's defensive redaction](structured-logging.md#sensitive-fields-and-defensive-redaction):
both remain defence in depth, not a reason to relax the safeguards in this
document.

## Current Library evidence

Before this decision, the v0.1.x Library scaffold ignored only `.env` and
carried an inert, unenforced `.env.example` placeholder. After this decision:

- generated `.gitignore` ignores the `.env` family and conventional
  credential/key artefacts, with the `.env.example` negation described above;
- generated `.pre-commit-config.yaml` runs `detect-private-key` alongside the
  existing hooks from the same already-pinned repository;
- generated `SECURITY.md` documents the `.env`/`.env.example` split, what the
  ignore rules cover, and how to opt into scanning; and
- `render.check_secret_safeguards` and `render.check_env_example_tracked`
  verify these properties for every combo this repository scaffolds.

No Copier question, runtime dependency, ProjectSpec field, or component
manifest is added.

## Deferred implementation mechanics

This contract does not generate a scanner, add a `secret_scanning` Copier
question, define a baseline or allowlist file format, or add a CI job. An
untested conditional was the exact failure mode
[ADR 0008](adr/0008-remove-make-task-runner.md) already removed once; this
decision does not reintroduce one. Stage 06 owns the composition mechanics for
a future optional scanning capability and the GitHub-platform contribution
that would generate host-native scanning configuration.
[FT-05.05](https://github.com/Sandsy09/forge-template/issues/31) owns SBOM and
release-provenance planning, a related but distinct supply-chain concern.
