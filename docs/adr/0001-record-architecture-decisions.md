# 1. Record architecture decisions

## Status

Accepted

## Context

We need to record the architectural decisions made on this project so future
contributors (including ourselves) understand why the repo looks the way it
does, not just what it currently looks like. `CLAUDE.md` had been absorbing
this reasoning as compressed bullets — a sentence or two per decision — and it
kept getting shorter and less useful as the file grew.

## Decision

We will use Architecture Decision Records, as described by Michael Nygard in
[Documenting Architecture
Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

Each ADR is a numbered Markdown file in `docs/adr/`. Records are immutable:
once accepted, a decision is changed by writing a new ADR that supersedes it,
not by editing this one.

This is deliberately the same format the `library` archetype gives scaffolded
projects as their own ADR 0001 (see
`template/{% if use_docs %}docs{% endif %}/adr/0001-record-architecture-decisions.md.jinja`).
This repo dogfoods its own scaffold's practice rather than inventing a
different one for itself.

## Consequences

Anyone wanting to understand a past design decision can read the ADR instead
of reverse-engineering it from code, git history, or asking around.
`CLAUDE.md` keeps the operational rules and links out here for rationale,
rather than carrying both. Decisions that turn out to be wrong are recorded
as history, not silently erased.
