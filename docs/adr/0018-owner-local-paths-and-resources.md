# 18. Keep path and resource access owner-local and context-free

## Status

Accepted

## Context

[ADR 0012](0012-conservative-foundation-scope.md) keeps Foundation runtime-free
and assigns path, resource, and exception conventions to Stage 04. [ADR
0015](0015-owner-local-runtime-configuration.md) assigns runtime configuration
to the archetype or capability consuming it and requires the runtime
entrypoint to assemble typed fragments once. [ADR
0016](0016-owner-local-environment-inputs.md) defines environment-backed
configuration but deliberately left project-root discovery and path handling
to this decision, noting only that a local `.env` occupies one logical
project-root location.

None of those boundaries yet says how a runtime owner should locate its own
packaged files, or where it should read or write at runtime, without every
owner inventing incompatible conventions. A shared Foundation path helper
would recreate the runtime layer ADR 0012 rejects. Leaving owners free to walk
parent directories for a project-root marker, or to derive behaviour from the
process working directory, would instead make generated code fragile: it would
behave differently depending on the invocation directory and break outright
once installed as a wheel, zipped, or run from a container image with no
source-tree markers present.

The current Library scaffold has no runtime path or resource behaviour: its
package reads no files, its only non-Python packaged file (`py.typed`) is a
byte-empty build/type-checker marker, and its build backend declares no
resource inclusion. A decision can therefore define the future
generated-project contract without changing current output.

## Decision

Adopt the [path and resource ownership conventions](../paths-and-resources.md)
as the canonical living contract.

The archetype or capability contributing runtime behaviour owns how it locates
its own packaged files and where it reads or writes at runtime; Foundation
supplies no path helper, resource loader, project-root finder, or directory
registry. Reusable code resolves no paths at import time and derives no
behaviour from the process working directory, `sys.argv[0]`, `__main__`, or
the installed package directory; only the runtime entrypoint may interpret a
user-supplied relative path, and only as part of its own documented interface.

Installed code never discovers a project root by walking parent directories
for `pyproject.toml`, `.git`, or another marker. This resolves ADR 0016's
deferral: the optional local-development `.env` is loaded by the runtime
entrypoint from an explicitly supplied path, never by search. An owner that
ships packaged non-Python files reads them through `importlib.resources`
rather than `__file__` arithmetic or `pkg_resources`, and treats them as
read-only and potentially non-extracted.

A writable location — cache, generated output, or user data — is never the
installed package directory or an implicit path relative to the working
directory. It is an explicit field on the owner's typed configuration
fragment, assembled and injected once by the runtime entrypoint under ADR
0015's convention; an owner may use an OS-convention directory library as its
own runtime dependency to compute a default, without that dependency becoming
Foundation's. One writable location has one owner; implicit sharing is an
unsupported collision. Documented path interfaces use `pathlib.Path`,
resolved to absolute form at validation, and must work identically on
Windows, macOS, and Linux.

This decision changes no current template file, Copier answer, generated
output, ProjectSpec, component manifest, runtime dependency, schema, public
API, or CLI behaviour.

## Consequences

- Runtime owners gain a predictable, portable way to locate packaged
  resources and writable locations without a shared Foundation path module.
- Generated code stops depending on the process working directory or a
  source-tree layout, so it keeps working when installed as a wheel, zipped,
  or run from a container image.
- ADR 0016's local `.env` location is now fully resolved: the entrypoint is
  told where it is rather than discovering it.
- Component authors must document their packaged resources, writable
  locations, and any directory-convention dependency they choose.
- One location having one owner means future composition must detect and
  reject collisions rather than allow silent overwrites.
- FT-04.05 retains the exception types raised on path or resource failure, and
  Stage 06 retains composition and collision mechanics.
- The current Library scaffold remains unchanged until later roadmap work
  selects and implements an owning component.
