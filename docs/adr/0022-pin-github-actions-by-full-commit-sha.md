# 22. Pin GitHub Actions by full commit SHA

## Status

Accepted

## Context

The current template-repository and generated-project workflows reference
remote actions through moving major tags such as `actions/checkout@v4` and
`astral-sh/setup-uv@v5`. Those references are convenient and readable, but the
repository owner can move them after review. A compromised upstream account or
repository could therefore change the code executed by an unchanged Forge or
generated-project commit.

Replacing moving tags with opaque SHAs reduces that risk but can make releases
hard to identify and can strand users on old action code. Forge already offers
Renovate, Dependabot, and disabled dependency-update choices, so the decision
also needs a maintenance path that works under every choice. The policy must
remain a GitHub platform concern rather than turning one CI provider into a
Foundation requirement.

## Decision

Adopt the [GitHub Action pinning policy](../github-action-pinning.md) as the
canonical living reference.

Every repository-based remote action and reusable workflow owned or generated
by `forge-template` uses a full 40-character commit SHA with the exact release
tag in a same-line comment. The SHA is authoritative. Same-repository `./...`
references are already bound to the calling commit and remain exempt. Forge
does not permit `docker://` actions until it defines digest pinning and a
maintainable updater path for them.

All action updates require a reviewed pull request. The reviewer examines the
upstream release and source, independently verifies the release tag's commit,
updates the SHA and comment together, and requires CI to pass. Forge-provided
automation does not auto-merge action updates.

Root Dependabot maintains this repository's references. Generated Renovate
configuration enables `helpers:pinGitHubActionDigests`; generated Dependabot
configuration retains its `github-actions` updater; projects selecting no
automation follow the documented manual workflow. Repository validation scans
both source and rendered workflows and rejects mutable or undocumented remote
references.

The initial migration pins the latest patch on each already-selected major:
`actions/checkout` v4.4.0, `astral-sh/setup-uv` v5.4.2, and
`actions/upload-artifact` v4.6.2. It does not combine the security decision
with unrelated action-major upgrades.

## Consequences

- An unchanged workflow commit cannot silently execute code moved behind an
  upstream branch or tag.
- Exact release comments retain human readability and allow Renovate and
  Dependabot to update immutable references.
- Action updates become explicit supply-chain review events and never inherit
  an automated merge path from general dependency tooling.
- Generated projects that disable dependency automation keep a complete
  manual maintenance path without acquiring a background service.
- Adding a remote action, reusable workflow, or Docker action now fails local
  and CI validation unless it satisfies the policy.
- Existing generated projects receive the pin migration through a later tagged
  Copier update and may need to review a normal three-way workflow merge.
- GitHub Actions remains a platform-specific implementation; the Foundation
  quality guarantee and generated-project runtime remain provider-neutral.
- No Copier question, stored answer, ProjectSpec, component manifest, runtime
  dependency, generated Python API, or CLI behaviour changes.
