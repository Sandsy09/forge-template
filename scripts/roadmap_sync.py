"""Import a filed roadmap from GitHub into a pack and reconcile its live metadata.

FT-24.03 / ADR 0078. The filed GitHub issues of roadmap 5 (Stages 22 to 29) are
authoritative. This script:

`export`
    Writes the checked-in pack (docs/roadmap-v5): every filed body exactly as
    filed, the manifest, the issue indexes, the direct dependency matrix, the
    obligation traceability and the proposed waves. Read-only towards GitHub.

`reconcile`
    Computes, and with `--apply` performs, the live metadata the filed issues
    lack: `roadmap:N` labels, stage milestones, native sub-issue and blocked-by
    relationships, and status labels that match the open predecessors. It is
    read-first, idempotent and add-only for relationships; it never edits a
    body and never deletes an unrelated edge.

`verify`
    Read-after-write check that GitHub matches the pack: bodies unchanged,
    labels, milestones, native parents and blockers, and status labels.

Usage:
    uv run python scripts/roadmap_sync.py reconcile            # dry run
    uv run python scripts/roadmap_sync.py reconcile --apply
    uv run python scripts/roadmap_sync.py verify
    uv run python scripts/roadmap_sync.py export --state filed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
import check_roadmaps  # noqa: E402

REPOS = ("Sandsy09/forge-template", "Sandsy09/create-forge")
PACK_STAGES = tuple(range(22, 30))
SNAPSHOT_STAGES = (21, *PACK_STAGES)
PACK_DIR = ROOT / "docs" / "roadmap-v5"
_TITLE = re.compile(r"^((?:FT|CF)-(?:EPIC-)?(\d+)(?:\.\d+)?) — (.+)$")
_BLOCKED = re.compile(r"Blocked\s+by\s+\[([^\]]+)\]")

Runner = Callable[[Sequence[str]], str]


class SyncError(Exception):
    """GitHub state or the pack could not be read, written or trusted."""


def default_runner(command: Sequence[str]) -> str:
    """Run a command and return its stdout; the command is built here."""
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SyncError(f"cannot run {command[0]!r}: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()[:300]
        raise SyncError(f"{' '.join(command[:4])} failed: {detail}")
    return result.stdout.decode("utf-8")


# ---------------------------------------------------------------------------
# GitHub access
# ---------------------------------------------------------------------------


class GitHub:
    """A thin `gh api` wrapper with an injectable runner."""

    def __init__(self, runner: Runner) -> None:
        """Bind the runner every request goes through."""
        self.runner = runner

    def get(self, path: str, *, paginate: bool = False) -> Any:
        """GET a path; paginated arrays are merged into one list."""
        command = ["gh", "api", path]
        if paginate:
            command.append("--paginate")
        text = self.runner(command)
        if not paginate:
            return json.loads(text)
        decoder = json.JSONDecoder()
        merged: list[Any] = []
        index = 0
        while index < len(text):
            while index < len(text) and text[index].isspace():
                index += 1
            if index >= len(text):
                break
            value, index = decoder.raw_decode(text, index)
            merged.extend(value if isinstance(value, list) else [value])
        return merged

    def send(self, method: str, path: str, fields: Mapping[str, Any]) -> Any:
        """Send a write; integers and booleans use typed `-F`, text uses `-f`."""
        command = ["gh", "api", "-X", method, path]
        for key, value in fields.items():
            if isinstance(value, bool):
                command += ["-F", f"{key}={str(value).lower()}"]
            elif isinstance(value, int):
                command += ["-F", f"{key}={value}"]
            elif isinstance(value, list):
                for item in value:
                    command += ["-f", f"{key}[]={item}"]
            else:
                command += ["-f", f"{key}={value}"]
        text = self.runner(command)
        return json.loads(text) if text.strip() else None


# ---------------------------------------------------------------------------
# The filed issues
# ---------------------------------------------------------------------------


@dataclass
class Issue:
    """One filed issue: its identity, exact body and current live state."""

    identifier: str
    repo: str
    number: int
    rest_id: int
    url: str
    title: str
    stage: int
    state: str
    body: str
    labels: list[str]
    milestone: str | None
    milestone_number: int | None

    @property
    def is_epic(self) -> bool:
        """Whether this is a stage epic."""
        return "-EPIC-" in self.identifier

    @property
    def short_repo(self) -> str:
        """`forge-template` or `create-forge`."""
        return self.repo.split("/")[1]

    @property
    def closed(self) -> bool:
        """Whether the issue is closed on GitHub."""
        return self.state == "closed"


def epic_title(title: str) -> str:
    """The part of a filed title after `<ID> — `."""
    match = _TITLE.match(title)
    if match is None:
        raise SyncError(f"title does not follow the filed pattern: {title!r}")
    return match[3]


_ONE_SECTION = 2


def _section(body: str, heading: str) -> str:
    parts = re.split(rf"(?m)^## {re.escape(heading)}\n", body)
    if len(parts) != _ONE_SECTION:
        raise SyncError(f"body has no single '## {heading}' section")
    return parts[1].split("\n## ")[0]


def parse_labels(body: str) -> list[str]:
    """The labels a filed body lists, in order."""
    return re.findall(r"`([^`]+)`", _section(body, "Labels"))


def parse_blocked_by(body: str) -> list[str]:
    """The identifiers a filed body says it is blocked by, in order."""
    return _BLOCKED.findall(_section(body, "Dependencies and blocking requirements"))


def parse_parent(body: str) -> str | None:
    """The parent epic identifier, or None for a repository-owned epic."""
    match = re.search(r"\[([^\]]+)\]\(", _section(body, "Parent epic"))
    return match[1] if match else None


def load_issues(
    gh: GitHub, stages: Sequence[int] = SNAPSHOT_STAGES
) -> dict[str, Issue]:
    """Every filed issue of the given stages in both repositories."""
    found: dict[str, Issue] = {}
    for repo in REPOS:
        rows = gh.get(f"repos/{repo}/issues?state=all&per_page=100", paginate=True)
        for row in rows:
            if "pull_request" in row:
                continue
            match = _TITLE.match(row.get("title") or "")
            if not match or int(match[2]) not in stages:
                continue
            identifier = match[1]
            if identifier in found:
                raise SyncError(f"duplicate filed identifier {identifier}")
            milestone = row.get("milestone") or {}
            found[identifier] = Issue(
                identifier=identifier,
                repo=repo,
                number=row["number"],
                rest_id=row["id"],
                url=row["html_url"],
                title=row["title"],
                stage=int(match[2]),
                state=row["state"],
                body=row.get("body") or "",
                labels=[label["name"] for label in row.get("labels", [])],
                milestone=milestone.get("title"),
                milestone_number=milestone.get("number"),
            )
    return found


@dataclass
class Graph:
    """The filed graph, read from the bodies (GitHub bodies are authoritative)."""

    issues: dict[str, Issue]
    parent: dict[str, str | None]
    blocked_by: dict[str, list[str]]
    filed_labels: dict[str, list[str]] = field(default_factory=dict)

    def children(self, epic: str) -> list[str]:
        """The epic's children, in identifier order."""
        return sorted(k for k, v in self.parent.items() if v == epic)


def build_graph(issues: Mapping[str, Issue]) -> Graph:
    """Parse parents, blockers and filed labels out of every body."""
    graph = Graph(dict(issues), {}, {})
    for identifier, issue in issues.items():
        if issue.stage not in PACK_STAGES:
            # Stage 21 was filed in the older body layout and belongs to the
            # frozen roadmap-v4 pack; only its live labels are reconciled.
            graph.parent[identifier] = None
            graph.blocked_by[identifier] = []
            graph.filed_labels[identifier] = []
            continue
        graph.parent[identifier] = parse_parent(issue.body)
        graph.blocked_by[identifier] = parse_blocked_by(issue.body)
        graph.filed_labels[identifier] = parse_labels(issue.body)
        for reference in [*graph.blocked_by[identifier], graph.parent[identifier]]:
            if reference is not None and reference not in issues:
                raise SyncError(f"{identifier} references unknown issue {reference}")
    return graph


def milestone_title(graph: Graph, issue: Issue) -> str:
    """`<this repository's epic title> — Stage N`, per the milestone convention."""
    epic = next(
        (
            i
            for i in graph.issues.values()
            if i.is_epic and i.stage == issue.stage and i.repo == issue.repo
        ),
        None,
    )
    if epic is None:
        raise SyncError(
            f"{issue.identifier}: no epic for stage {issue.stage} in {issue.repo}"
        )
    return f"{epic_title(epic.title)} — Stage {issue.stage}"


def waves(graph: Graph) -> dict[int, list[str]]:
    """Proposed implementation waves: closed issues are wave 0, the rest by depth."""
    level: dict[str, int] = {}

    def depth(identifier: str) -> int:
        if identifier in level:
            return level[identifier]
        if graph.issues[identifier].closed:
            level[identifier] = 0
        else:
            level[identifier] = 1 + max(
                (depth(b) for b in graph.blocked_by[identifier]), default=0
            )
        return level[identifier]

    grouped: dict[int, list[str]] = defaultdict(list)
    for identifier in graph.issues:
        grouped[depth(identifier)].append(identifier)
    return {w: sorted(ids, key=_sort_key) for w, ids in sorted(grouped.items())}


def _sort_key(identifier: str) -> tuple[int, int, str]:
    match = re.search(r"(\d+)", identifier)
    number = int(match[1]) if match else 0
    return (number, 0 if "EPIC" in identifier else 1, identifier)


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Action:
    """One GitHub write: a category, what it does and the request."""

    category: str
    summary: str
    method: str
    path: str
    fields: tuple[tuple[str, Any], ...] = ()


@dataclass
class NativeState:
    """The native relationships currently on GitHub."""

    sub_issues: dict[str, set[int]]  # epic identifier -> child issue numbers
    blocked_by: dict[str, set[tuple[str, int]]]  # identifier -> {(repo, number)}


def load_native(gh: GitHub, graph: Graph) -> NativeState:
    """Read the native sub-issue and blocked-by relationships of the pack."""
    native = NativeState({}, {})
    for identifier, issue in graph.issues.items():
        if issue.stage not in PACK_STAGES:
            continue
        if issue.is_epic:
            rows = gh.get(
                f"repos/{issue.repo}/issues/{issue.number}/sub_issues?per_page=100",
                paginate=True,
            )
            native.sub_issues[identifier] = {row["number"] for row in rows}
        rows = gh.get(
            f"repos/{issue.repo}/issues/{issue.number}/dependencies/blocked_by?per_page=100",
            paginate=True,
        )
        native.blocked_by[identifier] = {
            (
                row["repository"]["full_name"] if "repository" in row else issue.repo,
                row["number"],
            )
            for row in rows
        }
    return native


def load_milestones(gh: GitHub) -> dict[tuple[str, str], dict[str, Any]]:
    """Every milestone of both repositories, keyed by (repo, title)."""
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for repo in REPOS:
        for row in gh.get(
            f"repos/{repo}/milestones?state=all&per_page=100", paginate=True
        ):
            found[(repo, row["title"])] = row
    return found


def _open_blockers(graph: Graph, identifier: str) -> list[str]:
    return [b for b in graph.blocked_by[identifier] if not graph.issues[b].closed]


def desired_status_labels(graph: Graph, identifier: str) -> set[str]:
    """The live `status:*` labels an issue should carry, from its open blockers."""
    issue = graph.issues[identifier]
    current = {label for label in issue.labels if label.startswith("status:")}
    if issue.closed:
        return current - {"status:blocked", "status:in-progress"}
    return (current - {"status:blocked"}) | (
        {"status:blocked"} if _open_blockers(graph, identifier) else set()
    )


def _stage_complete(graph: Graph, repo: str, stage: int) -> bool:
    members = [i for i in graph.issues.values() if i.repo == repo and i.stage == stage]
    return bool(members) and all(i.closed for i in members)


def plan_actions(
    graph: Graph,
    native: NativeState,
    milestones: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    pack_stages: Sequence[int] = PACK_STAGES,
) -> list[Action]:
    """The writes that bring GitHub to the pack's graph; empty once reconciled."""
    actions: list[Action] = []
    for identifier, issue in sorted(
        graph.issues.items(), key=lambda kv: _sort_key(kv[0])
    ):
        in_pack = issue.stage in pack_stages
        base = f"repos/{issue.repo}/issues/{issue.number}"
        if in_pack and f"roadmap:{issue.stage}" not in issue.labels:
            actions.append(
                Action(
                    "label",
                    f"{identifier}: add roadmap:{issue.stage}",
                    "POST",
                    f"{base}/labels",
                    (("labels", [f"roadmap:{issue.stage}"]),),
                )
            )
        for label in sorted(
            {x for x in issue.labels if x.startswith("status:")}
            - desired_status_labels(graph, identifier)
        ):
            actions.append(
                Action(
                    "status",
                    f"{identifier}: remove stale {label}",
                    "DELETE",
                    f"{base}/labels/{quote(label, safe='')}",
                )
            )
        if (
            issue.closed is False
            and "status:blocked" not in issue.labels
            and _open_blockers(graph, identifier)
        ):
            actions.append(
                Action(
                    "status",
                    f"{identifier}: add status:blocked",
                    "POST",
                    f"{base}/labels",
                    (("labels", ["status:blocked"]),),
                )
            )
        if in_pack:
            title = milestone_title(graph, issue)
            if issue.milestone != title:
                actions.append(
                    Action(
                        "milestone",
                        f"{identifier}: attach milestone '{title}'",
                        "PATCH",
                        base,
                        (("milestone", title),),
                    )
                )
        parent = graph.parent[identifier]
        if (
            in_pack
            and parent
            and issue.number not in native.sub_issues.get(parent, set())
        ):
            actions.append(
                Action(
                    "sub-issue",
                    f"{identifier}: attach to {parent} as a native sub-issue",
                    "POST",
                    f"repos/{graph.issues[parent].repo}/issues/{graph.issues[parent].number}/sub_issues",
                    (("sub_issue_id", issue.rest_id),),
                )
            )
        for blocker in graph.blocked_by[identifier]:
            target = graph.issues[blocker]
            if in_pack and (target.repo, target.number) not in native.blocked_by.get(
                identifier, set()
            ):
                actions.append(
                    Action(
                        "blocked-by",
                        f"{identifier}: native blocked-by {blocker}",
                        "POST",
                        f"{base}/dependencies/blocked_by",
                        (("issue_id", target.rest_id),),
                    )
                )
    needed = {
        (issue.repo, milestone_title(graph, issue))
        for issue in graph.issues.values()
        if issue.stage in pack_stages
    }
    for repo, title in sorted(needed - set(milestones)):
        stage = int(title.rsplit("Stage ", 1)[1])
        actions.insert(
            0,
            Action(
                "milestone-create",
                f"{repo}: create milestone '{title}'",
                "POST",
                f"repos/{repo}/milestones",
                (
                    ("title", title),
                    ("description", f"Roadmap stage {stage}; see docs/roadmap-v5."),
                ),
            ),
        )
    for (repo, title), row in sorted(milestones.items()):
        match = re.search(r"Stage (\d+)$", title)
        if not match or int(match[1]) not in (*pack_stages, 21):
            continue
        stage = int(match[1])
        if _stage_complete(graph, repo, stage) and row.get("state") != "closed":
            actions.append(
                Action(
                    "milestone-close",
                    f"{repo}: close complete milestone '{title}'",
                    "PATCH",
                    f"repos/{repo}/milestones/{row['number']}",
                    (("state", "closed"),),
                )
            )
    return actions


def apply_actions(
    gh: GitHub,
    graph: Graph,
    actions: Sequence[Action],
    milestones: Mapping[tuple[str, str], Mapping[str, Any]],
    out: Callable[[str], None],
) -> list[str]:
    """Perform the actions in order; return the failures (empty on success)."""
    numbers = {key: row["number"] for key, row in milestones.items()}
    failures: list[str] = []
    ordered = sorted(actions, key=lambda a: _APPLY_ORDER[a.category])
    for action in ordered:
        try:
            fields = dict(action.fields)
            if action.category == "milestone-create":
                created = gh.send(action.method, action.path, fields)
                repo = action.path.split("/")[1] + "/" + action.path.split("/")[2]
                numbers[(repo, fields["title"])] = created["number"]
            elif action.category == "milestone":
                repo = "/".join(action.path.split("/")[1:3])
                key = (repo, str(fields["milestone"]))
                if key not in numbers:
                    raise SyncError(f"milestone {key[1]!r} does not exist in {repo}")
                gh.send(action.method, action.path, {"milestone": numbers[key]})
            else:
                gh.send(action.method, action.path, fields)
            out(f"ok      {action.summary}")
        except SyncError as exc:
            failures.append(f"{action.summary}: {exc}")
            out(f"FAILED  {action.summary}: {exc}")
    return failures


_MAX_PASSES = 3
_APPLY_ORDER = {
    "milestone-create": 0,
    "label": 1,
    "milestone": 2,
    "sub-issue": 3,
    "blocked-by": 4,
    "status": 5,
    "milestone-close": 6,
}


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_state(
    graph: Graph,
    native: NativeState,
    milestones: Mapping[tuple[str, str], Mapping[str, Any]],
    pack_bodies: Mapping[str, str],
    *,
    pack_stages: Sequence[int] = PACK_STAGES,
) -> list[str]:
    """Every way GitHub differs from the pack; empty when reconciled."""
    problems: list[str] = []
    for identifier, issue in graph.issues.items():
        if issue.stage not in pack_stages:
            stale = {x for x in issue.labels if x.startswith("status:")} - (
                desired_status_labels(graph, identifier)
            )
            problems += [f"{identifier}: stale {label}" for label in sorted(stale)]
            continue
        filed = pack_bodies.get(identifier)
        if filed is None:
            problems.append(f"{identifier}: missing from the pack")
        elif filed.replace("\r\n", "\n") != issue.body.replace("\r\n", "\n"):
            problems.append(f"{identifier}: body differs from the pack")
        if f"roadmap:{issue.stage}" not in issue.labels:
            problems.append(f"{identifier}: missing roadmap:{issue.stage}")
        title = milestone_title(graph, issue)
        if issue.milestone != title:
            problems.append(
                f"{identifier}: milestone is {issue.milestone!r}, expected {title!r}"
            )
        stale = {
            x for x in issue.labels if x.startswith("status:")
        } - desired_status_labels(graph, identifier)
        problems += [f"{identifier}: stale {label}" for label in sorted(stale)]
        if (
            issue.closed is False
            and _open_blockers(graph, identifier)
            and "status:blocked" not in issue.labels
        ):
            problems.append(f"{identifier}: open blocker but no status:blocked")
        parent = graph.parent[identifier]
        if parent and issue.number not in native.sub_issues.get(parent, set()):
            problems.append(f"{identifier}: not a native sub-issue of {parent}")
        for blocker in graph.blocked_by[identifier]:
            target = graph.issues[blocker]
            if (target.repo, target.number) not in native.blocked_by.get(
                identifier, set()
            ):
                problems.append(f"{identifier}: missing native blocked-by {blocker}")
    for issue in graph.issues.values():
        if issue.is_epic and issue.stage in pack_stages:
            expected = {
                graph.issues[c].number for c in graph.children(issue.identifier)
            }
            extra = native.sub_issues.get(issue.identifier, set()) - expected
            if extra:
                problems.append(
                    f"{issue.identifier}: unexpected native sub-issues {sorted(extra)}"
                )
    for (repo, title), row in milestones.items():
        match = re.search(r"Stage (\d+)$", title)
        if match and int(match[1]) in pack_stages:
            complete = _stage_complete(graph, repo, int(match[1]))
            if complete != (row.get("state") == "closed"):
                stage_state = "complete" if complete else "not complete"
                problems.append(
                    f"milestone {title!r} in {repo} is {row.get('state')} "
                    f"but its stage is {stage_state}"
                )
    return problems


# ---------------------------------------------------------------------------
# Pack rendering
# ---------------------------------------------------------------------------


def _link(issue: Issue) -> str:
    return f"[{issue.identifier}]({issue.url})"


def _stage_titles(graph: Graph) -> dict[int, dict[str, str]]:
    titles: dict[int, dict[str, str]] = defaultdict(dict)
    for issue in graph.issues.values():
        if issue.is_epic and issue.stage in PACK_STAGES:
            titles[issue.stage][issue.repo] = epic_title(issue.title)
    return dict(sorted(titles.items()))


def body_path(issue: Issue) -> str:
    """The pack-relative path of an issue's exact body file."""
    return f"github-issues/{issue.short_repo}/{issue.identifier}.md"


def build_manifest(
    graph: Graph,
    *,
    state: str,
    verified_at: str,
    milestones: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    """The filing manifest for the pack's issues."""
    pack = [i for i in graph.issues.values() if i.stage in PACK_STAGES]
    pack.sort(
        key=lambda i: (i.stage, 0 if i.is_epic else 1, i.repo != REPOS[0], i.identifier)
    )
    stages = [
        {
            "number": stage,
            "owners": sorted(titles),
            "titles": dict(sorted(titles.items())),
        }
        for stage, titles in _stage_titles(graph).items()
    ]
    entries: list[dict[str, Any]] = []
    for issue in pack:
        entry: dict[str, Any] = {
            "id": issue.identifier,
            "title": issue.title,
            "repository": issue.repo,
            "kind": "epic" if issue.is_epic else "child",
            "stage": issue.stage,
            "milestone": milestone_title(graph, issue),
            "parent": graph.parent[issue.identifier],
            "blocked_by": graph.blocked_by[issue.identifier],
            "labels": graph.filed_labels[issue.identifier],
            "added_labels": [f"roadmap:{issue.stage}"],
            "body": body_path(issue),
        }
        if issue.is_epic:
            entry["children"] = graph.children(issue.identifier)
        if state == "filed":
            entry["number"] = issue.number
            entry["url"] = issue.url
            entry["body_sha256"] = hashlib.sha256(issue.body.encode()).hexdigest()
        entries.append(entry)
    traces: list[dict[str, Any]] = []
    for issue in pack:
        for trace_id, kind, text in check_roadmaps.derive_obligations(
            issue.identifier, issue.body
        ):
            traces.append(
                {
                    "id": trace_id,
                    "source": "filed-body",
                    "kind": kind,
                    "criterion": " ".join(text.split()),
                    "owner": issue.identifier,
                    "epic": graph.parent[issue.identifier] or issue.identifier,
                }
            )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "status": "filed-open" if state == "filed" else "prepared-not-filed",
        "roadmap": 5,
        "name": "Stages 22 to 29",
        "stages": stages,
        "issues": entries,
        "traceability": traces,
    }
    if state == "filed":
        records = []
        for repo, title in sorted({(i["repository"], i["milestone"]) for i in entries}):
            row = milestones[(repo, title)]
            records.append(
                {
                    "repository": repo,
                    "title": title,
                    "number": row["number"],
                    "url": f"https://github.com/{repo}/milestone/{row['number']}",
                }
            )
        manifest["filing"] = {
            "verified_at": verified_at,
            "labels_applied": [f"roadmap:{s['number']}" for s in stages],
            "milestones": records,
            "native": {
                "sub_issues": sum(1 for e in entries if e["parent"]),
                "blocked_by": sum(len(e["blocked_by"]) for e in entries),
                "status": "applied-and-verified",
            },
        }
    return manifest


def render_index(graph: Graph, repo: str) -> str:
    """The issue index of one repository's part of the pack."""
    short = repo.split("/")[1]
    lines = [
        f"# {short} Stages 22 to 29 issue index",
        "",
        "Every entry is a filed GitHub issue whose exact filed body is recorded in",
        "this pack. GitHub is authoritative for live state (open or closed, status",
        "labels); the [status snapshot](../../ROADMAP.md#status-snapshot) is dated.",
        "",
        "| ID | Issue | Title | Parent | Direct blockers | Milestone |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    pack = sorted(
        (i for i in graph.issues.values() if i.repo == repo and i.stage in PACK_STAGES),
        key=lambda i: (i.stage, 0 if i.is_epic else 1, i.identifier),
    )
    for issue in pack:
        parent = graph.parent[issue.identifier]
        blockers = ", ".join(
            _link(graph.issues[b]) for b in graph.blocked_by[issue.identifier]
        )
        lines.append(
            f"| {_link(issue)} | [#{issue.number}]({issue.url}) | "
            f"{epic_title(issue.title)} | "
            f"{_link(graph.issues[parent]) if parent else '—'} | {blockers or '—'} | "
            f"{milestone_title(graph, issue)} |"
        )
    return "\n".join(lines) + "\n"


def render_matrix(graph: Graph) -> str:
    """The direct dependency matrix."""
    lines = [
        "# Direct dependency matrix",
        "",
        "Every direct blocked-by edge stated by the filed bodies, including local",
        "edges for context. Native GitHub blocked-by relationships mirror these",
        "edges and are authoritative once reconciled. Parent membership is recorded",
        "in the issue indexes and is not a blocked-by edge.",
        "",
        "| Blocked issue | Blocked by | Boundary |",
        "| --- | --- | --- |",
    ]
    for identifier in sorted(graph.issues, key=_sort_key):
        issue = graph.issues[identifier]
        if issue.stage not in PACK_STAGES:
            continue
        for blocker in graph.blocked_by[identifier]:
            target = graph.issues[blocker]
            boundary = "Local" if target.repo == issue.repo else "Cross-repo"
            lines.append(f"| {_link(issue)} | {_link(target)} | {boundary} |")
    return "\n".join(lines) + "\n"


def render_traceability(graph: Graph) -> str:
    """The obligation traceability derived from the filed bodies."""
    lines = [
        "# Filed-obligation traceability",
        "",
        "The 21 September 2026 engineering review that motivated these stages is",
        "not available in either repository, so this table does not reconstruct it.",
        "It records what the filed issue bodies themselves state: every checklist",
        "item under Acceptance criteria and every paragraph under Exclusions, each",
        "with a stable ID and its owning issue. The validator recomputes the set",
        "from the bodies, so none can be missing or drift.",
        "",
        "| Obligation | Kind | Text | Owner | Epic |",
        "| --- | --- | --- | --- | --- |",
    ]
    pack = sorted(
        (i for i in graph.issues.values() if i.stage in PACK_STAGES),
        key=lambda i: (
            i.stage,
            0 if i.is_epic else 1,
            i.repo != REPOS[0],
            i.identifier,
        ),
    )
    for issue in pack:
        epic = graph.issues[graph.parent[issue.identifier] or issue.identifier]
        for trace_id, kind, text in check_roadmaps.derive_obligations(
            issue.identifier, issue.body
        ):
            cell = " ".join(text.split()).replace("|", "\\|")
            lines.append(
                f"| {trace_id} | {kind} | {cell} | {_link(issue)} | {_link(epic)} |"
            )
    return "\n".join(lines) + "\n"


def render_roadmap(graph: Graph, snapshot_date: str) -> str:
    """The stage overview, proposed waves and dated status snapshot."""
    lines = [
        "# Stages 22 to 29",
        "",
        "Nothing here promises a release date or a version. Stage titles are the",
        "epic titles; where the two repositories title a stage differently, both",
        "are shown and each repository's milestone uses its own.",
        "",
    ]
    for stage, titles in _stage_titles(graph).items():
        lines += [
            f"## Stage {stage}",
            "",
            "| Repository | Stage title | Epic | Children |",
            "| --- | --- | --- | --- |",
        ]
        for repo, title in titles.items():
            epic = next(
                i
                for i in graph.issues.values()
                if i.is_epic and i.stage == stage and i.repo == repo
            )
            kids = ", ".join(
                _link(graph.issues[c]) for c in graph.children(epic.identifier)
            )
            lines.append(f"| {repo.split('/')[1]} | {title} | {_link(epic)} | {kids} |")
        lines.append("")
    lines += [
        "## Proposed implementation waves",
        "",
        "Derived from the direct dependencies alone, as the snapshot date below:",
        "an issue's wave is one more than its deepest open blocker, and a closed",
        "issue is wave 0. Waves order work; they are not commitments, and a",
        "preferred order is not a technical blocker.",
        "",
        "| Wave | Issues |",
        "| --- | --- |",
    ]
    for number, ids in waves(graph).items():
        pack_ids = [i for i in ids if graph.issues[i].stage in PACK_STAGES]
        if not pack_ids:
            continue
        label = "0 (complete)" if number == 0 else str(number)
        lines.append(
            f"| {label} | {', '.join(_link(graph.issues[i]) for i in pack_ids)} |"
        )
    lines += [
        "",
        "## Status snapshot",
        "",
        f"As of {snapshot_date}. GitHub is authoritative; this section is",
        "regenerated by `scripts/roadmap_sync.py export`.",
        "",
    ]
    stage21 = [i for i in graph.issues.values() if i.stage == 21]
    if stage21:
        state21 = "all closed" if all(i.closed for i in stage21) else "not all closed"
        lines += [
            "### Stage 21 reconciliation",
            "",
            f"Stage 21 (Streamlit client adoption) has {len(stage21)} filed issues in",
            f"create-forge, {state21}. The roadmap-v4 pack records them as filed,",
            "open and blocked, which was true at filing and is preserved unchanged;",
            "live labels and the milestone were reconciled here.",
            "",
        ]
    lines += ["| Stage | Complete | Open |", "| --- | --- | --- |"]
    for stage in _stage_titles(graph):
        members = [i for i in graph.issues.values() if i.stage == stage]
        done = [i for i in members if i.closed]
        open_ids = sorted(
            (i.identifier for i in members if not i.closed), key=_sort_key
        )
        lines.append(
            f"| {stage} | {len(done)} of {len(members)} | "
            f"{', '.join(open_ids) or '—'} |"
        )
    lines += [
        "",
        "## Completion rule",
        "",
        "A child is complete when its acceptance criteria have reviewed evidence on",
        "its issue; an epic closes only after every child is complete. A merged pull",
        "request is not evidence of publication.",
    ]
    return "\n".join(lines) + "\n"


def write_pack(
    graph: Graph,
    *,
    state: str,
    milestones: Mapping[tuple[str, str], Mapping[str, Any]],
    pack: Path = PACK_DIR,
) -> list[Path]:
    """Write every generated pack file; hand-written files are left alone."""
    today = datetime.now(UTC).date().isoformat()
    written: list[Path] = []

    def put(relative: str, text: str) -> None:
        path = pack / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)

    for issue in graph.issues.values():
        if issue.stage in PACK_STAGES:
            put(body_path(issue), issue.body)
    manifest = build_manifest(
        graph, state=state, verified_at=today, milestones=milestones
    )
    put(
        "github-issues/filing-manifest.json",
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n",
    )
    for repo in REPOS:
        put(
            f"github-issues/{repo.split('/')[1]}/ISSUE-INDEX.md",
            render_index(graph, repo),
        )
    put("github-issues/CROSS-REPO-DEPENDENCIES.md", render_matrix(graph))
    put("TRACEABILITY.md", render_traceability(graph))
    put("ROADMAP.md", render_roadmap(graph, today))
    return written


def read_pack_bodies(pack: Path = PACK_DIR) -> dict[str, str]:
    """The exact bodies recorded in the pack, keyed by identifier."""
    bodies: dict[str, str] = {}
    for path in sorted(pack.glob("github-issues/*/*.md")):
        if path.name != "ISSUE-INDEX.md":
            bodies[path.stem] = path.read_text(encoding="utf-8")
    return bodies


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    out: Callable[[str], None] = print,
    pack: Path = PACK_DIR,
) -> int:
    """Run one subcommand; the runner, output and pack directory are injectable."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    export_cmd = sub.add_parser("export", help="write the pack from GitHub")
    export_cmd.add_argument("--state", choices=("prepared", "filed"), default="filed")
    reconcile_cmd = sub.add_parser("reconcile", help="plan or apply live metadata")
    reconcile_cmd.add_argument("--apply", action="store_true")
    reconcile_cmd.add_argument(
        "--only",
        help="comma-separated categories to plan or apply (milestone-create, "
        "label, milestone, sub-issue, blocked-by, status, milestone-close)",
    )
    sub.add_parser("verify", help="check GitHub against the pack")
    args = parser.parse_args(argv)

    gh = GitHub(runner or default_runner)
    try:
        issues = load_issues(gh)
        graph = build_graph(issues)
        milestones = load_milestones(gh)
        if args.command == "export":
            files = write_pack(
                graph, state=args.state, milestones=milestones, pack=pack
            )
            out(f"wrote {len(files)} pack files ({args.state}) under {pack}")
            return 0
        native = load_native(gh, graph)
        if args.command == "verify":
            problems = verify_state(graph, native, milestones, read_pack_bodies(pack))
            for problem in problems:
                out(f"DRIFT   {problem}")
            out(
                "verify: GitHub matches the pack"
                if not problems
                else f"verify: {len(problems)} problem(s)"
            )
            return 0 if not problems else 1
        only = set(args.only.split(",")) if args.only else None
        if only and not only <= set(_APPLY_ORDER):
            raise SyncError(f"unknown categories: {sorted(only - set(_APPLY_ORDER))}")
        applied = 0
        all_failures: list[str] = []
        # Later passes see what the earlier ones created: a milestone can only
        # be closed once it exists. Stop when a pass plans nothing or fails.
        for round_number in range(1, _MAX_PASSES + 1):
            if round_number > 1:
                graph = build_graph(load_issues(gh))
                milestones = load_milestones(gh)
                native = load_native(gh, graph)
            actions = [
                a
                for a in plan_actions(graph, native, milestones)
                if only is None or a.category in only
            ]
            for action in actions:
                out(f"plan    [{action.category}] {action.summary}")
            if not actions:
                out(
                    "reconcile: nothing to do"
                    if round_number == 1
                    else "reconcile: converged"
                )
                break
            if not args.apply:
                out(f"reconcile: {len(actions)} action(s) planned; rerun with --apply")
                return 0
            failures = apply_actions(gh, graph, actions, milestones, out)
            applied += len(actions) - len(failures)
            all_failures += failures
            if failures:
                break
        if args.apply:
            out(f"reconcile: applied {applied}; {len(all_failures)} failure(s)")
        return 1 if all_failures else 0
    except SyncError as exc:
        out(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
