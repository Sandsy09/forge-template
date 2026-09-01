"""Checks for ``copier.yml`` against the rules documented in CLAUDE.md.

These used to be an inline ``python -c`` heredoc in
``.github/workflows/test-template.yml`` (layout only) plus two rules
that nothing enforced at all (computed defaults, the ``versioning`` /
``versioning_resolved`` indirection). Both CI and ``uv run poe check`` now
run them via :func:`check_all`.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment
from jinja2 import meta as jinja_meta

from forge_template.github_actions import check_action_pins

REPO_ROOT = Path(__file__).resolve().parents[2]

# `versioning_resolved` is the only thing template/ may read; a bare
# `versioning` reference would silently reintroduce the invalid
# uv_build + vcs combination for anyone running `copier update`. `\b` does
# not match between "versioning" and "_resolved" (both word characters), so
# this pattern naturally skips the name it must not flag.
_BARE_VERSIONING = re.compile(r"\bversioning\b")

# Context Copier injects into every template that no question declares.
_COPIER_BUILTINS = frozenset(
    {
        "_copier_answers",
        "_copier_conf",
        "_copier_operation",
        "_copier_python",
        "_folder_name",
    }
)

# Questions that exist only to feed a `when: false` computed value
# (python_all -> python_matrix, versioning -> versioning_resolved) and are
# deliberately never read directly by template/**. Named and commented so a
# genuinely unused question still gets flagged rather than silently excused.
_COMPUTED_INPUTS = frozenset({"python_all", "versioning"})

_VALID_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _identity_filter(value: Any, *_args: Any, **_kwargs: Any) -> Any:
    return value


class _PermissiveFilters(dict[str, Any]):
    """A filters mapping that treats every name as defined.

    ``meta.find_undeclared_variables`` fully compiles the template (not just
    parses it) to track scope correctly, which means Jinja's compiler
    insists every filter it encounters actually exists -- including Copier's
    own ``to_nice_yaml`` and the Tera-only filters inside the git-cliff
    ``{% raw %}`` block. Since :func:`_undeclared_names` only cares about
    *names*, not runtime behaviour, every filter is safe to treat as a no-op.
    """

    def __missing__(self, _key: str) -> Any:
        return _identity_filter

    def __contains__(self, _key: object) -> bool:
        return True

    def get(self, key: str, default: Any = None) -> Any:
        # dict.get() bypasses __missing__, so it needs its own override --
        # this is exactly the lookup Jinja's compiler uses for filters.
        return dict.get(self, key, _identity_filter)


def _permissive_jinja_env() -> Environment:
    env = Environment(autoescape=False)
    env.filters = _PermissiveFilters(env.filters)
    return env


def _undeclared_names(env: Environment, text: str) -> set[str]:
    """Every Jinja name referenced in `text`, excluding loop/set-scoped
    locals -- e.g. `versioning` from `{{ versioning_resolved }}`, but not
    the `v` in `{% for v in python_matrix %}`.
    """  # noqa: D205
    tree = env.parse(text)
    names: set[str] = jinja_meta.find_undeclared_variables(tree)
    return names - _COPIER_BUILTINS


def load_schema(path: Path | str = REPO_ROOT / "copier.yml") -> dict[str, Any]:
    """Parse and return the copier.yml question set."""
    with Path(path).open(encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)
    return cfg


def check_layout(cfg: dict[str, Any]) -> list[str]:
    """Verify the settings `copier update` depends on are present and correct."""
    errors = []
    if cfg.get("_subdirectory") != "template":
        errors.append("_subdirectory must be 'template'")
    if "_answers_file" not in cfg:
        errors.append(
            "_answers_file missing -- template/.copier-answers.yml.jinja "
            "will not be usable by `copier update`"
        )
    return errors


def check_computed(cfg: dict[str, Any]) -> list[str]:
    """Every `when: false` question must carry a `default` (CLAUDE.md: 'Computed
    values use `when: false` with the value in `default`').
    """  # noqa: D205
    errors = []
    for name, question in cfg.items():
        if name.startswith("_") or not isinstance(question, dict):
            continue
        if question.get("when") is False and "default" not in question:
            errors.append(f"{name}: when: false but no default set")
    return errors


def check_versioning_indirection(
    template_dir: Path = REPO_ROOT / "template",
) -> list[str]:
    """No file under template/ may read bare `versioning` -- only
    `versioning_resolved` (CLAUDE.md: 'All templates read
    `versioning_resolved`, never `versioning`.').
    """  # noqa: D205
    errors = []
    for path in sorted(template_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _BARE_VERSIONING.search(line):
                rel = path.relative_to(template_dir)
                errors.append(
                    f"template/{rel}:{lineno}: bare 'versioning' reference: "
                    f"{line.strip()}"
                )
    return errors


def _collect_template_used_names(template_dir: Path) -> set[str]:
    """Every Jinja name referenced anywhere under `template_dir` -- in file
    and directory names as well as file contents.
    """  # noqa: D205
    env = _permissive_jinja_env()
    used: set[str] = set()
    components: set[str] = set()
    for path in sorted(template_dir.rglob("*")):
        components.update(
            part for part in path.relative_to(template_dir).parts if "{" in part
        )
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "{{" in text or "{%" in text:
            used |= _undeclared_names(env, text)
    for component in components:
        used |= _undeclared_names(env, component)
    return used


def check_question_usage(
    cfg: dict[str, Any], template_dir: Path = REPO_ROOT / "template"
) -> list[str]:
    """Every declared question must be referenced somewhere under
    template/**, and every name referenced there must be a declared question.

    Would have caught `codeowners_team` being asked of every user while its
    only consumer was an empty CODEOWNERS file. `python_all` and
    `versioning` are the deliberate exceptions -- see `_COMPUTED_INPUTS`.
    """  # noqa: D205
    declared = {name for name in cfg if not name.startswith("_")}
    used = _collect_template_used_names(template_dir)
    errors = []
    for name in sorted(declared - used - _COMPUTED_INPUTS):
        errors.append(
            f"{name}: declared in copier.yml but never referenced under template/**"
        )
    for name in sorted(used - declared):
        errors.append(
            f"{name}: referenced under template/** but not declared in copier.yml"
        )
    return errors


def _candidate_values(cfg: dict[str, Any], name: str) -> list[Any]:
    """Representative values to probe a question's referenced conditionals
    with -- both booleans for `type: bool`, every option for `choices`.
    """  # noqa: D205
    question = cfg.get(name, {})
    if question.get("type") == "bool":
        return [True, False]
    choices = question.get("choices")
    if isinstance(choices, dict):
        return list(choices.values())
    if isinstance(choices, list):
        return list(choices)
    return [True, False]


def check_conditional_filenames(
    cfg: dict[str, Any], template_dir: Path = REPO_ROOT / "template"
) -> list[str]:
    """Every `{% if ... %}name{% endif %}` path component must render to
    either a valid filename or the empty string (Copier skips the
    file/directory in that case) -- never something in between, which would
    mean broken Jinja shipped in a rendered project.
    """  # noqa: D205
    env = _permissive_jinja_env()
    components: set[str] = set()
    for path in template_dir.rglob("*"):
        components.update(
            part for part in path.relative_to(template_dir).parts if "{%" in part
        )

    errors = []
    for component in sorted(components):
        var_names = sorted(_undeclared_names(env, component) & set(cfg))
        if not var_names:
            continue
        value_lists = [_candidate_values(cfg, name) for name in var_names]
        rendered_template = env.from_string(component)
        for combo in itertools.product(*value_lists):
            context = dict(zip(var_names, combo, strict=True))
            rendered = rendered_template.render(**context)
            check_value = (
                rendered[: -len(".jinja")] if rendered.endswith(".jinja") else rendered
            )
            if check_value == "":
                continue
            if not _VALID_FILENAME_RE.match(check_value):
                errors.append(
                    f"{component!r} rendered to {check_value!r} under {context} -- "
                    "neither a valid filename nor empty"
                )
    return errors


def check_all(cfg: dict[str, Any] | None = None) -> list[str]:
    """Run every check and return the combined list of errors."""
    cfg = cfg if cfg is not None else load_schema()
    return [
        *check_layout(cfg),
        *check_computed(cfg),
        *check_versioning_indirection(),
        *check_question_usage(cfg),
        *check_conditional_filenames(cfg),
        *check_action_pins(REPO_ROOT / ".github" / "workflows"),
        *check_action_pins(REPO_ROOT / "template" / ".github" / "workflows"),
    ]


def render_default(question: dict[str, Any], context: dict[str, Any]) -> Any:
    """Render a `when: false` question's Jinja `default` under the given context.

    Used to test the computed-value expressions themselves (e.g.
    `python_matrix`, `versioning_resolved`) rather than just their presence.
    """
    env = Environment(autoescape=False)
    return env.from_string(str(question["default"])).render(**context)


def main() -> int:
    """Print any failures and return a process exit code."""
    errors = check_all()
    for error in errors:
        print(f"::error::{error}")
    if errors:
        print(f"{len(errors)} schema check(s) failed.")
        return 1
    print("Schema checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
