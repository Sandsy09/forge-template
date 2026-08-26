# Path and resource ownership conventions

This is the canonical living contract for path and resource access in
generated Forge projects. It extends the
[configuration ownership conventions](configuration-ownership.md), which
assign runtime settings to the archetype or capability consuming them and
require the runtime entrypoint to assemble them once. [ADR
0018](adr/0018-owner-local-paths-and-resources.md) records why Forge adopted
this contract.

The contract describes generated-project behaviour that future archetypes and
capabilities must preserve. It does not add path or resource handling to the
current v0.1.x Library scaffold or define a ProjectSpec or component manifest
field.

## Paths and resources have a runtime owner

Foundation supplies no path helper, resource loader, project-root finder,
directory registry, or runtime dependency. The archetype or capability
contributing runtime behaviour owns how it locates its own packaged files and
where it reads or writes at runtime. A project with no runtime file access
needs no path configuration or supporting dependency.

## No implicit process context

Reusable code resolves no paths at import time. It does not derive behaviour
from the process's current working directory, `sys.argv[0]`, `__main__`, or
the directory containing the installed package. A module's behaviour must not
change with the directory a user happened to invoke the process from.

The process working directory is user context, not a resolution source. Only
the runtime entrypoint may interpret a user-supplied relative path against it,
and only when accepting that input is itself part of the entrypoint's
documented interface.

## No runtime project-root discovery

Installed code never walks parent directories searching for `pyproject.toml`,
`.git`, or another marker file, and never assumes it is running from a source
checkout, an editable install, or an unpacked archive. Those assumptions break
for a wheel installed into a virtual environment, a zipped application, or a
container image with no such markers present.

This resolves the deferral in the
[environment-variable conventions](environment-variables.md#one-optional-local-dotenv-file):
the optional local-development `.env` file is loaded by the runtime entrypoint
from an explicitly supplied path, never by searching for a project root.
Development tooling that genuinely needs a repository root — this template's
own `uv run poe check`, for example — is a development-time concern outside
this runtime contract.

## Packaged resources

An owner that ships non-Python files inside its own package reads them
through `importlib.resources` (`files()`, and `as_file()` only where a real
filesystem path is genuinely required), never through `__file__` arithmetic or
the deprecated `pkg_resources` API. Packaged resources are read-only at
runtime and may not be ordinary files on disk — a zipped or otherwise
non-extracted install must keep working.

The owner declares its packaged resources in its own build configuration.
Foundation adds no packaging entries for resources it does not own.

## Writable locations are explicit configuration

An owner never writes into its installed package directory, the template
source, or an implicit path relative to the process working directory. A
writable location — a cache, generated output, or user data directory — is a
field on the owner's typed configuration fragment, validated and supplied by
the runtime entrypoint under the
[assemble once and inject explicitly](configuration-ownership.md#assemble-once-and-inject-explicitly)
convention.

An owner may take an OS-convention directory library as its own runtime
dependency to compute a sensible default. That dependency stays owner-local
and never becomes a Foundation dependency or a shared default other owners
must adopt. Temporary files use the standard library and are cleaned up by
whichever owner created them.

One writable location has one owner. Two owners sharing a location implicitly
is an unsupported collision; future composition must reject it rather than
allow silent last-write-wins behaviour.

## Path values and interfaces

An owner's documented path inputs and outputs use `pathlib.Path`. A public
boundary may accept `str` or `os.PathLike` and normalise it once, at
validation, rather than repeatedly at each use. Paths are resolved to absolute
form at that same validation step rather than compared or joined as relative
strings later.

Generated projects support Windows, macOS, and Linux — this repository's own
CI already runs a Windows job. Path handling must not hard-code a path
separator, assume case-sensitive comparison, or otherwise assume a POSIX-only
environment. Validation errors identify the offending path without echoing
secret-bearing configuration values.

## Testing path behaviour

Where an owner implements path or resource behaviour, its tests:

- pass regardless of the directory the test runner was invoked from;
- use `tmp_path` or equivalent isolation rather than writing into the
  repository, the installed package, or another fixed absolute location;
- exercise the packaged-resource access path itself, not only a convenience
  file read directly from the source tree; and
- assert the owner's documented interface rather than an incidental directory
  layout that composition may later change.

The scaffold's own test configuration already runs under
`--import-mode=importlib`
([`pyproject.toml.jinja`](https://github.com/Sandsy09/forge-template/blob/main/template/pyproject.toml.jinja)),
which avoids the same implicit `sys.path`/CWD coupling this contract asks
runtime owners to avoid.

## Current Library evidence

The v0.1.x Library scaffold remains free of runtime path or resource
behaviour:

- its package `__init__.py` reads no files and exposes only
  `importlib.metadata` version lookups;
- the only non-Python file inside the generated package is a byte-empty
  `py.typed` marker, consumed by type checkers and the build backend rather
  than by runtime code;
- the build backend configuration (`[tool.uv.build-backend]`'s module name and
  root, or `[tool.hatch.build.targets.wheel]`'s `packages`) declares only the
  package itself, with no resource inclusion; and
- Copier offers no path or resource-related question or answer.

This decision changes no template file, Copier answer, generated output,
runtime dependency, schema, public API, or CLI behaviour.

## Deferred implementation mechanics

This contract does not define a path or resource helper module, a concrete
resource-loading API, a directory-convention library choice, a
containment-checking algorithm, a ProjectSpec field, a component manifest, or
a migration. Stage 06 owns composition and collision mechanics. The exception
types an owner raises on path or resource failure follow the
[exception ownership conventions](exception-ownership.md). Broader
secret-file safeguards and optional scanning remain owned by
[FT-05.04](https://github.com/Sandsy09/forge-template/issues/30).
