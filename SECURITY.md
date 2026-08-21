# Security Policy

## Scope

Copier's `_tasks` in [copier.yml](copier.yml) run shell commands (`git init`,
first commit) against the machine scaffolding a project — this is why
scaffolding requires `--trust`, and why a change to `_tasks` or anything it
calls is treated as a trust-boundary change, not an ordinary edit.

`template/` content itself only ever becomes files in a *generated* project;
it has no ability to execute anything on its own.

## Supported versions

Only the latest tagged release is supported. There is no backport policy —
`copier update` is the intended way for an existing project to pick up a fix.

## Reporting a vulnerability

Do not open a public issue. Use
[GitHub private vulnerability reporting](https://github.com/Sandsy09/forge-template/security/advisories/new)
to report privately.

You should get an acknowledgement within a few business days.
