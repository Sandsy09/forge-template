# Environment-variable and local dotenv conventions

This is the canonical living contract for environment-backed runtime
configuration in generated Forge projects. It extends the
[configuration ownership conventions](configuration-ownership.md), which
define who owns configuration and how typed fragments are assembled and
injected. [ADR 0016](adr/0016-owner-local-environment-inputs.md) records why
Forge adopted this contract.

The contract describes generated-project behaviour that future archetypes and
capabilities must preserve. It does not add environment-backed configuration
to the current v0.1.x Library scaffold or define a ProjectSpec or component
manifest field.

## Apply the convention only where needed

An archetype or capability uses this convention only when it owns runtime
behaviour that needs environment-backed input. The same owner retains
responsibility for the fields, types, validation, defaults, documentation, and
secret classification in its typed configuration fragment.

A configuration-light project needs no environment variables, dotenv loader,
example file, or supporting runtime dependency. Foundation supplies only the
neutral safeguard that keeps the conventional secret-bearing `.env` file out
of version control; it does not supply an environment schema or loader.

## Names belong to runtime owners

Each environment-backed owner declares a stable uppercase prefix. Its variable
names use `<OWNER_PREFIX>_<SETTING>`, with uppercase ASCII letters, digits, and
underscores. The prefix is part of the owner's documented runtime interface
and does not change merely because a project is renamed.

Forge imposes no project-wide runtime prefix. In particular, generated
projects must not use `FORGE_*` as a runtime namespace: that name belongs to
Forge tooling, while generated projects remain independent after handoff.

An owner that faithfully integrates an established external standard may use
that standard's canonical variable names instead of translating them behind
its own prefix. It must document the exception and the external contract being
implemented. The exception does not create a general unprefixed namespace.

One variable has one owner. A consumer that needs another owner's value uses
the provider's typed public interface rather than declaring a second spelling
or reading the variable independently. Duplicate names, incompatible standard
claims, and ambiguous aliases are unsupported collisions; future composition
must reject them instead of applying last-write-wins replacement.

## Input resolution and validation

An environment-backed owner resolves inputs from lowest to highest precedence:

1. owner-defined, non-sensitive defaults;
2. an explicitly enabled project-root `.env` local-development fallback;
3. variables already present in the process environment; and
4. explicit runtime-entrypoint inputs.

The runtime entrypoint then constructs and validates each owner's typed
fragment once, following the
[assembly convention](configuration-ownership.md#assemble-once-and-inject-explicitly).
Importing a module must not read the environment or trigger dotenv loading.

A present variable with an empty value is still supplied. The owning field's
validation must accept or reject that value explicitly; it must not silently
treat the value as absent and fall through to a lower-precedence source or
default.

Copier answers, ProjectSpec fields, profiles, and organisation policies are
generation-time selection inputs, not runtime secret sources. They do not join
this precedence chain or render secret values into generated content.

## One optional local dotenv file

An environment-backed project may offer one project-root `.env` as a local
development convenience and one tracked `.env.example` as its safe reference.
The `.env` file is not the deployment contract:

- Forge never generates, commits, or overwrites it;
- loading it requires an explicit local-development entrypoint option;
- existing process variables override values from it;
- deployed environments supply process variables through their own
  provider-specific mechanisms;
- an environment label never selects a dotenv file; and
- there is no implicit `.env.development`, `.env.staging`, or
  `.env.production` cascade.

The entrypoint must treat `.env` as data, never source or execute it as a shell
script. The generated `.env.example` relies only on a portable subset: blank
lines, comments, and simple `NAME=value` assignments. It must not require
`export`, interpolation, command substitution, executable statements,
multiline syntax, or other loader-specific behaviour. The entrypoint owner
documents the selected loader and any literal quoting or escaping its users
need.

The [path and resource ownership conventions](paths-and-resources.md) define
how the runtime entrypoint locates this single logical location: never by
runtime project-root discovery, but from a path the entrypoint is explicitly
given.

## Safe examples and user documentation

The tracked `.env.example` is assembled only when at least one selected owner
uses environment-backed configuration. Every entry remains owned by the
component that contributed it, even though the project presents one root file.

Secret-bearing entries show the exact name as a commented empty assignment,
for example:

```dotenv
# PAYMENTS_API_KEY=
```

They never contain a real, plausible, generated, profile-supplied, or
organisation-supplied secret value. Safe non-sensitive defaults may use active
assignments. The example must remain safe to commit and is never itself loaded
as runtime input.

User and contributor documentation identifies, for every variable:

- its owning archetype or capability and purpose;
- its type, accepted format or values, and validation rules;
- whether it is required and any non-sensitive default;
- whether it is secret-bearing and therefore redacted; and
- which sources may provide it and how precedence applies.

Validation errors may identify a variable and source so the user can correct
them, but must not echo secret-bearing values — the same boundary the
[exception ownership conventions](exception-ownership.md) apply to exception
messages generally. Broader generated-project secret safeguards and optional
scanning are defined by the
[secret-handling safeguards](secret-handling.md).

## Provider-neutral environment identity

A runtime owner may expose an environment identity when its behaviour truly
needs one. The identity is an open, provider-neutral logical label. Conventional
examples include `development`, `test`, `staging`, and `production`, while
projects and organisations may define other documented values.

No universal environment variable or closed Forge enum is required. If
multiple owners need the same identity, one owner publishes it through its
typed interface and the others consume that interface explicitly.

An environment label is descriptive context, not an authorisation or security
boundary. It must not implicitly weaken validation, enable unsafe behaviour,
choose credentials, select a dotenv file, or encode a cloud or deployment
provider. Any behaviour that varies by label is owner-local, explicit, and
documented.

In particular, the
[structured logging capability](structured-logging.md) exposes level and
format through its own typed configuration. An environment identity never
selects or implies either setting. If the logging owner exposes those settings
through environment variables, their names and precedence follow this
contract.

## Composition and current Library evidence

Future composition will assemble owner-contributed sections into the root
`.env.example` and reject duplicate names or incompatible contributions.
[component-manifests.md](component-manifests.md),
[composition-order.md](composition-order.md), and
[file-conflicts.md](file-conflicts.md) now define the component metadata,
ordering, extension-point, and collision mechanics that target requires; a
stable discovery and rendering API (FT-06.07) is what remains before it can
be implemented.

The v0.1.x Library scaffold remains configuration-light and unchanged:

- generated `.gitignore` ignores `.env`;
- Copier lists `.env` under `_skip_if_exists`, so template maintenance does
  not overwrite a project owner's local file;
- the tracked `.env.example` contains only a commented empty placeholder;
- generated code neither reads that file nor loads the process environment;
  and
- the generated runtime dependencies include no settings or dotenv library.

The current `.env.example` is therefore an inert artefact of the monolithic
scaffold, not a Library runtime configuration contract. Its conditional
ownership and any generated-file migration remain later component work. This
decision changes no template file, Copier answer, generated output, runtime
dependency, schema, or public API.
