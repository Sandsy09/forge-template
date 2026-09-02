# Forge Python Support Policy

This document defines the CPython versions Forge offers to generated projects,
how their defaults and tested range are derived, and how that support window
moves forward. It complements the [Foundation guarantees](foundation-guarantees.md):
those guarantees require a clean supported environment, while this policy
defines what “supported” means for Python.

The policy governs Forge-produced output and future compositions. It does not
set the interpreter support of the `forge-template` repository itself or the
`create-forge` CLI, and it does not prevent the owner of an independent
generated project from adopting a different policy after handoff.

## Supported implementation and release window

Forge's support contract covers final CPython feature releases. It does not
claim support for prereleases, PyPy, or other Python implementations. Those
interpreters may be used for exploratory compatibility work, but they do not
become supported merely because a project happens to run on them.

The active Forge window is the latest four final CPython feature releases.
Upstream release status comes from the
[CPython developer guide](https://devguide.python.org/versions/), and the
annual cadence is defined by [PEP 602](https://peps.python.org/pep-0602/).
Forge's rolling window is deliberately narrower than CPython's complete
upstream support lifetime.

A deprecated release may remain temporarily available alongside the four
active releases during the notice period described below. It remains tested
and supported during that overlap, but new projects should use an active
release.

## Generated-project version controls

The current Copier contract uses four related values:

| Value | Contract |
| --- | --- |
| `python_all` | The ordered final CPython releases Forge can currently render, including any release in its deprecation overlap. |
| `python_min_version` | The generated project's compatibility floor. Its default is the oldest active release. |
| `python_version` | The generated project's development interpreter and tested upper edge. Its default is the final release immediately before the newest active release. |
| `python_matrix` | Every feature release from `python_min_version` through `python_version`, inclusive. |

The minimum may not be newer than the development interpreter. A user may
select another offered combination that satisfies that ordering.

The selected minimum supplies the lower bound in `requires-python`, the static
analysis language targets, and the first entry in the generated test matrix.
The selected development version supplies `.python-version`, the interpreter
used for single-version quality and build jobs, and the last entry in that
matrix. Classifiers describe the tested inclusive range.

`requires-python` deliberately has no upper cap. A newer interpreter may work,
but Forge does not claim it as tested for that generated project until it is
inside the selected range. The distinction lets libraries remain installable
on forward-compatible Python releases without overstating what their generated
CI has exercised.

## Current support state

This table is a living snapshot, reviewed on 2026-08-24. Changing it in line
with the lifecycle below does not change the durable policy.

| Concern | Current state |
| --- | --- |
| Active choices | CPython 3.11, 3.12, 3.13, and 3.14 |
| Deprecated choices | None |
| Default minimum | CPython 3.11 |
| Default development version | CPython 3.13 |
| Default tested range | CPython 3.11 through 3.13 |
| Newest opt-in development choice | CPython 3.14 |

These values match the existing `copier.yml`; adopting this policy changes no
question, answer, generated file, or runtime behaviour.

Future Data Science dependencies follow the same floor. The canonical
[initial capability contracts](data-science-capabilities.md#dependency-evidence)
record the reviewed lower-release metadata for the Jupyter and Scientific
Python lines, including the NumPy 2.4 ceiling needed to retain Python 3.11.
The
[compatibility and acceptance contract](data-science-compatibility-and-acceptance.md#python-endpoint-checks)
makes an executable Python 3.11 and 3.14 endpoint sweep a required Stage 11
and Stage 12 acceptance check, and requires a superseding ADR rather than a
silent bound change if a dependency set fails to resolve at either endpoint.

## Admitting a new CPython release

A CPython release enters the active window only after its final release and a
Forge transition change demonstrate all of the following:

- Forge's locked dependencies resolve on the new interpreter;
- schema and rendering validation accept the new value;
- every scaffold combination passes its generated quality and build contract;
- a boundary scenario exercises the new interpreter selection; and
- the generated CI workflow passes on the new interpreter.

Prerelease testing may help prepare that change, but is neither required by
this policy nor a support claim. There is no fixed delay after the final
release: the validation evidence is the adoption gate.

When that gate passes, the transition change:

1. adds the new final release as an active choice;
2. moves the default minimum to the oldest release in the new four-release
   active window;
3. moves the default development version to the release immediately before
   the new final release; and
4. marks the outgoing oldest release deprecated while retaining it through the
   notice period.

For example, admitting CPython 3.15 would make 3.12–3.15 active, default new
projects to a 3.12 minimum and 3.14 development interpreter, and retain 3.11
temporarily as deprecated.

Changed defaults apply to new generations. Copier replays recorded answers
when an existing project updates, so a default change must not rewrite that
project's chosen minimum or development interpreter.

## Deprecation and removal

The outgoing release remains available, tested, and supported for at least 90
days after deprecation is announced. Removal happens only in a later tagged
Forge release after that notice period has elapsed.

The deprecation change must provide layered notice through:

- this document's current support table;
- a tracking issue and pull request;
- the relevant generated prompt or guidance;
- the Forge release notes; and
- migration guidance for affected project owners.

The later removal pull request carries the `breaking-change` label and repeats
the migration path in its release notes. Removing a value from the supported
window never authorises silently raising recorded Copier answers. The removal
must either preserve safe replay for an existing answer or stop before
rendering with actionable guidance and require the project owner to choose the
upgrade. The detailed migration mechanism belongs to the transition that can
test it against the then-current Copier contract.

## Non-guarantees

This policy does not promise:

- support for every CPython release still receiving upstream security fixes;
- support for prerelease or alternative Python implementations;
- that an interpreter newer than a generated project's tested upper edge has
  been validated;
- an upper-bound dependency constraint for speculative future incompatibility;
  or
- that a generated project's owner will retain Forge's policy after handoff.

A semantic change to the four-release window, default selection, interpreter
scope, notice period, or no-silent-update rule requires a new ADR superseding
[ADR 0013](adr/0013-python-support-policy.md). The living table and examples
may advance without a new ADR when they follow these rules.
