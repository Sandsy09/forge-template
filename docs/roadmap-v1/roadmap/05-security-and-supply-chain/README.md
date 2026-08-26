# Stage 05 — Security and Supply Chain

## Repository ownership

### forge-template

- **FT-05.01 — Define dependency update automation**
- **FT-05.02 — Harden GitHub Actions permissions**
- **FT-05.03 — Define GitHub Action pinning policy**
- [x] [**FT-05.04 — Add secret-handling safeguards**](../../../secret-handling.md)
  ([ADR 0020](../../../adr/0020-generated-project-secret-safeguards.md),
  [#30](https://github.com/Sandsy09/forge-template/issues/30))
- **FT-05.05 — Plan SBOM and release provenance capability**

### create-forge

- **CF-05.01 — Harden create-forge CI and release permissions**
- **CF-05.02 — Define template-engine dependency update policy**

## Stage record

FT-05.04 broadens the generated `.gitignore` to cover the `.env` family and
conventional credential/key artefacts, adds the already-pinned
`detect-private-key` pre-commit hook, documents secret handling in generated
`SECURITY.md`, and mechanically enforces a placeholder-only tracked
`.env.example`. It defines the properties a future optional secret-scanning
capability must have, naming gitleaks as the provider-neutral reference and
GitHub push protection / secret scanning as the parallel platform
contribution, without generating either or adding a Copier question. Unlike
the Stage 04 decisions, this one changes generated output for new and
updating projects alike.

## Stage completion rule

- [ ] Repo-local issues are complete or explicitly deferred.
- [ ] Cross-repository blockers are resolved.
- [ ] Public contracts changed by this stage are documented/versioned.
- [ ] No implementation concern is duplicated across repositories.
