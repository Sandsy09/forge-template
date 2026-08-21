"""Checks for ``copier.yml`` against the invariants documented in CLAUDE.md.

These used to be an inline ``python -c`` heredoc in
``.github/workflows/test-template.yml`` (layout only) plus two invariants
that nothing enforced at all (computed defaults, the ``versioning`` /
``versioning_resolved`` indirection). Both CI and ``uv run poe check`` now
run them via :func:`check_all`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment

REPO_ROOT = Path(__file__).resolve().parents[2]

# `versioning_resolved` is the only thing template/ may read; a bare
# `versioning` reference would silently reintroduce the invalid
# uv_build + vcs combination for anyone running `copier update`. `\b` does
# not match between "versioning" and "_resolved" (both word characters), so
# this pattern naturally skips the name it must not flag.
_BARE_VERSIONING = re.compile(r"\bversioning\b")


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


def check_all(cfg: dict[str, Any] | None = None) -> list[str]:
    """Run every check and return the combined list of errors."""
    cfg = cfg if cfg is not None else load_schema()
    return [*check_layout(cfg), *check_computed(cfg), *check_versioning_indirection()]


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
