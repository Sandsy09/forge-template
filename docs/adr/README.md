# Architecture Decision Records

Records of significant decisions, in [Nygard
format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

- [0001 — Record architecture decisions](0001-record-architecture-decisions.md)
- [0002 — Copier over Cookiecutter](0002-copier-over-cookiecutter.md)
- [0003 — Two-repo split](0003-two-repo-split.md)
- [0004 — Build backend + versioning](0004-build-backend-and-versioning.md)
- [0005 — git-cliff over hand-written changelogs](0005-git-cliff-for-changelogs.md)
- [0006 — mypy default, pyright optional](0006-mypy-default-pyright-optional.md)
- [0007 — MkDocs pinned below 2.0](0007-mkdocs-pinned-below-2.md)
- [0008 — Remove `make` as a task_runner choice](0008-remove-make-task-runner.md)
- [0009 — Branch and pull request workflow](0009-branch-and-pr-workflow.md)
- [0010 — Canonical Forge architectural terminology](0010-forge-architectural-terminology.md)
- [0011 — Outcome-based Forge Foundation guarantees](0011-forge-foundation-guarantees.md)
- [0012 — Keep Forge Foundation conservative and runtime-free](0012-conservative-foundation-scope.md)
- [0013 — Adopt a rolling CPython support policy](0013-python-support-policy.md)
- [0014 — Keep Foundation and the default profile editor-neutral](0014-editor-neutral-foundation.md)
- [0015 — Keep runtime configuration owner-local and explicitly injected](0015-owner-local-runtime-configuration.md)
- [0016 — Keep environment inputs owner-local and dotenv explicit](0016-owner-local-environment-inputs.md)
- [0017 — Keep structured logging owner-local and configure it once](0017-owner-local-structured-logging.md)
- [0018 — Keep path and resource access owner-local and context-free](0018-owner-local-paths-and-resources.md)
- [0019 — Keep exceptions owner-local and handle them once](0019-owner-local-exceptions.md)
- [0020 — Ship neutral secret safeguards and keep scanning optional](0020-generated-project-secret-safeguards.md)
- [0021 — Defer SBOM and release provenance to an optional capability](0021-defer-sbom-and-release-provenance.md)
- [0022 — Pin GitHub Actions by full commit SHA](0022-pin-github-actions-by-full-commit-sha.md)
- [0023 — Define strict ProjectSpec protocol v1](0023-projectspec-protocol-v1.md)
- [0024 — Define strict bundled component manifest protocol v1](0024-component-manifest-protocol-v1.md)
- [0025 — Define deterministic composition order](0025-deterministic-composition-order.md)
- [0026 — Define file conflict and override rules](0026-file-conflict-and-override-rules.md)
- [0027 — Design the template variable contract](0027-template-variable-contract.md)
- [0028 — Adopt composition-contract fixtures](0028-composition-contract-fixtures.md)
- [0029 — Expose a stable, side-effect-free template-engine API](0029-stable-template-engine-api.md)
- [0030 — Validate rendered projects before exposing engine success](0030-generated-project-validation.md)
- [0031 — Define Library as a distributable-package archetype over Foundation](0031-library-archetype-contract.md)
- [0032 — Render component and Foundation content paths](0032-render-component-content-paths.md)
- [0033 — Migrate the Library archetype to the production catalogue](0033-migrate-library-production-catalogue.md)
- [0034 — Select CLI Application as the second reference archetype](0034-select-cli-application-reference-archetype.md)
- [0035 — Implement the CLI Application reference archetype](0035-implement-cli-application-archetype.md)
- [0036 — Publish the engine to PyPI, excluding repo-local tooling](0036-publish-the-engine-to-pypi.md)
- [0037 — Align Foundation after the two-archetype composition review](0037-two-archetype-composition-review.md)
- [0038 — Define organisation policy as constrained selection input](0038-organisation-policy-selection-model.md)
- [0039 — Deny policy-granted file overrides; publish the extension-point inventory as a versioned contract](0039-deny-policy-file-overrides.md)
- [0040 — Prove the organisation-policy protocol with a test-only reference fixture](0040-organisation-policy-reference-fixture.md)
- [0041 — Define the Forge-Blueprint compatibility policy](0041-forge-blueprint-compatibility-policy.md)
- [0042 — Validate no-copy downstream inheritance](0042-validate-no-copy-downstream-inheritance.md)
- [0043 — Split invariants out of CLAUDE.md](0043-split-invariants-out-of-claude-md.md)
- [0044 — Plan Data Science as the third production archetype](0044-plan-data-science-as-the-third-archetype.md)
- [0045 — Define Data Science as an independent package-plus-notebooks shape](0045-data-science-project-shape.md)
- [0046 — Define Jupyter and Scientific Python as independent capabilities](0046-initial-data-science-capabilities.md)
- [0047 — Define fail-closed notebook validation and repository safeguards](0047-notebook-data-and-model-safeguards.md)
- [0048 — Fix the Data Science compatibility, acceptance, and release contract](0048-data-science-compatibility-and-acceptance.md)
- [0049 — Publish Foundation extension points for capability tooling](0049-foundation-capability-tooling-extension-points.md)
- [0050 — Ship Jupyter as a production capability](0050-production-jupyter-capability.md)
- [0051 — Ship Scientific Python as a production capability](0051-production-scientific-python-capability.md)

Add a new record by copying the most recent one and incrementing the number.
Records are immutable: supersede them rather than editing.

`uv run poe check` verifies the set stays consistent — filenames match
`NNNN-slug.md`, numbers are contiguous with no gaps or duplicates, every
record is linked here, and each has all four Nygard headings. See
[src/forge_template/adr.py](../../src/forge_template/adr.py).
