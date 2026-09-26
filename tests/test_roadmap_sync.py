"""Tests for the roadmap reconciler using an in-memory GitHub."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
# roadmap_sync imports check_roadmaps by name, so scripts/ must be importable.
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sync = _load("roadmap_sync")

FT = "Sandsy09/forge-template"
CF = "Sandsy09/create-forge"


def _body(labels: list[str], parent: str | None, blockers: list[str]) -> str:
    parent_text = f"[{parent}](https://example.test/{parent})" if parent else "None."
    blocked = "\n".join(
        f"Blocked by [{b}](https://example.test/{b})." for b in blockers
    )
    return (
        "## Outcome\n\nx\n\n"
        f"## Parent epic\n\n{parent_text}\n\n"
        f"## Dependencies and blocking requirements\n\n{blocked or 'None.'}\n\n"
        f"## Labels\n\n{' '.join(f'`{x}`' for x in labels)}\n"
    )


def _issue(
    identifier: str,
    repo: str,
    number: int,
    *,
    state: str = "open",
    parent: str | None = None,
    blockers: list[str] | None = None,
    labels: list[str] | None = None,
    title: str = "Thing",
) -> Any:
    return sync.Issue(
        identifier=identifier,
        repo=repo,
        number=number,
        rest_id=number * 1000 + (0 if repo == FT else 1),
        url=f"https://example.test/{identifier}",
        title=f"{identifier} — {title}",
        stage=int(identifier.split("-")[-1].split(".")[0]),
        state=state,
        body=_body(["area:ci"], parent, blockers or []),
        labels=list(labels or []),
        milestone=None,
        milestone_number=None,
    )


def make_issues() -> dict[str, Any]:
    issues = [
        _issue("FT-EPIC-24", FT, 1, title="Provider"),
        _issue("FT-24.01", FT, 2, state="closed", parent="FT-EPIC-24"),
        _issue(
            "FT-24.02",
            FT,
            3,
            parent="FT-EPIC-24",
            blockers=["FT-24.01"],
            labels=["status:blocked"],
        ),
        _issue("CF-EPIC-24", CF, 1, title="Client"),
        _issue("CF-24.01", CF, 2, parent="CF-EPIC-24", blockers=["FT-24.02"]),
        _issue(
            "CF-24.02",
            CF,
            3,
            state="closed",
            parent="CF-EPIC-24",
            labels=["status:in-progress"],
        ),
    ]
    return {i.identifier: i for i in issues}


class FakeGitHub:
    """Applies each write to the in-memory issues, like GitHub would."""

    def __init__(self, graph: Any) -> None:
        self.graph = graph
        self.native = sync.NativeState({}, {})
        self.milestones: dict[tuple[str, str], dict[str, Any]] = {}
        self._next = 100

    def _by_rest_id(self, rest_id: int) -> Any:
        return next(i for i in self.graph.issues.values() if i.rest_id == rest_id)

    def send(self, method: str, path: str, fields: Any) -> Any:
        parts = path.split("/")
        repo = "/".join(parts[1:3])
        if parts[3] == "milestones":
            if method == "POST":
                self._next += 1
                row = {"number": self._next, "state": "open"}
                self.milestones[(repo, fields["title"])] = row
                return row
            for row in self.milestones.values():
                if row["number"] == int(parts[4]):
                    row["state"] = fields["state"]
            return None
        issue = next(
            i
            for i in self.graph.issues.values()
            if i.repo == repo and i.number == int(parts[4])
        )
        tail = parts[5:]
        if tail[:1] == ["labels"] and method == "POST":
            issue.labels += fields["labels"]
        elif tail[:1] == ["labels"]:
            issue.labels.remove(unquote(tail[1]))
        elif tail == ["sub_issues"]:
            child = self._by_rest_id(fields["sub_issue_id"])
            self.native.sub_issues.setdefault(issue.identifier, set()).add(child.number)
        elif tail == ["dependencies", "blocked_by"]:
            blocker = self._by_rest_id(fields["issue_id"])
            self.native.blocked_by.setdefault(issue.identifier, set()).add(
                (blocker.repo, blocker.number)
            )
        else:
            issue.milestone = next(
                title
                for (r, title), row in self.milestones.items()
                if r == repo and row["number"] == fields["milestone"]
            )
        return None


@pytest.fixture
def world() -> tuple[Any, FakeGitHub]:
    graph = sync.build_graph(make_issues())
    return graph, FakeGitHub(graph)


def _plan(graph: Any, fake: FakeGitHub) -> list[Any]:
    return list(
        sync.plan_actions(graph, fake.native, fake.milestones, pack_stages=(24,))
    )


def _reconcile(graph: Any, fake: FakeGitHub) -> list[str]:
    actions = _plan(graph, fake)
    return list(
        sync.apply_actions(fake, graph, actions, fake.milestones, lambda _: None)
    )


def _converge(graph: Any, fake: FakeGitHub) -> None:
    for _ in range(3):
        assert _reconcile(graph, fake) == []


def _verify(graph: Any, fake: FakeGitHub, bodies: Any = None) -> list[str]:
    bodies = bodies or {k: v.body for k, v in graph.issues.items()}
    return list(
        sync.verify_state(
            graph, fake.native, fake.milestones, bodies, pack_stages=(24,)
        )
    )


def test_graph_is_read_from_bodies(world: tuple[Any, FakeGitHub]) -> None:
    graph, _ = world
    assert graph.parent["FT-24.02"] == "FT-EPIC-24"
    assert graph.blocked_by["CF-24.01"] == ["FT-24.02"]
    assert graph.children("CF-EPIC-24") == ["CF-24.01", "CF-24.02"]


def test_waves_put_closed_issues_in_wave_zero(world: tuple[Any, FakeGitHub]) -> None:
    graph, _ = world
    grouped = sync.waves(graph)
    assert {"FT-24.01", "CF-24.02"} <= set(grouped[0])
    assert "FT-24.02" in grouped[1]
    assert "CF-24.01" in grouped[2]


def test_plan_covers_every_category_and_writes_nothing(
    world: tuple[Any, FakeGitHub],
) -> None:
    graph, fake = world
    categories = {a.category for a in _plan(graph, fake)}
    assert categories == {
        "milestone-create",
        "label",
        "milestone",
        "sub-issue",
        "blocked-by",
        "status",
    }
    assert fake.milestones == {}


def test_stale_in_progress_on_closed_issue_is_removed(
    world: tuple[Any, FakeGitHub],
) -> None:
    graph, fake = world
    _converge(graph, fake)
    assert "status:in-progress" not in graph.issues["CF-24.02"].labels


def test_blocked_label_follows_open_blockers(world: tuple[Any, FakeGitHub]) -> None:
    graph, fake = world
    _converge(graph, fake)
    assert "status:blocked" in graph.issues["CF-24.01"].labels
    # FT-24.01 is closed, so it no longer justifies FT-24.02's label.
    assert "status:blocked" not in graph.issues["FT-24.02"].labels


def test_reconcile_is_idempotent(world: tuple[Any, FakeGitHub]) -> None:
    graph, fake = world
    _converge(graph, fake)
    assert _plan(graph, fake) == []


def test_verify_is_clean_after_reconcile(world: tuple[Any, FakeGitHub]) -> None:
    graph, fake = world
    _converge(graph, fake)
    assert _verify(graph, fake) == []


def test_verify_reports_a_dropped_native_edge(world: tuple[Any, FakeGitHub]) -> None:
    graph, fake = world
    _converge(graph, fake)
    fake.native.blocked_by["CF-24.01"].clear()
    assert _verify(graph, fake) == ["CF-24.01: missing native blocked-by FT-24.02"]


def test_verify_reports_drift_wrong_parent_and_stale_milestone(
    world: tuple[Any, FakeGitHub],
) -> None:
    graph, fake = world
    _converge(graph, fake)
    bodies = {k: v.body for k, v in graph.issues.items()}
    bodies["FT-24.02"] += "drift\n"
    fake.native.sub_issues["FT-EPIC-24"].discard(graph.issues["FT-24.02"].number)
    fake.native.sub_issues["FT-EPIC-24"].add(99)
    graph.issues["CF-24.01"].milestone = "Old — Stage 24"
    problems = _verify(graph, fake, bodies)
    assert "FT-24.02: body differs from the pack" in problems
    assert "FT-24.02: not a native sub-issue of FT-EPIC-24" in problems
    assert any(p.startswith("CF-24.01: milestone is 'Old") for p in problems)
    assert any("unexpected native sub-issues [99]" in p for p in problems)


def test_open_milestone_of_a_complete_stage_is_reported(
    world: tuple[Any, FakeGitHub],
) -> None:
    graph, fake = world
    _converge(graph, fake)
    for issue in graph.issues.values():
        issue.state = "closed"
    assert any("but its stage is complete" in p for p in _verify(graph, fake))


def test_failed_write_is_a_partial_failure(world: tuple[Any, FakeGitHub]) -> None:
    graph, fake = world

    def boom(method: str, path: str, fields: Any) -> Any:
        raise sync.SyncError("denied")

    fake.send = boom  # type: ignore[method-assign]
    failures = _reconcile(graph, fake)
    assert failures
    # Dependent writes (a milestone attach) fail too, and are still reported.
    assert any("denied" in f for f in failures)


def test_unknown_reference_is_rejected() -> None:
    issues = make_issues()
    issues["FT-24.02"].body = _body(["area:ci"], "FT-EPIC-24", ["FT-99.01"])
    with pytest.raises(sync.SyncError, match=r"unknown issue FT-99\.01"):
        sync.build_graph(issues)


def test_matrix_is_deterministic(world: tuple[Any, FakeGitHub]) -> None:
    graph, _ = world
    assert sync.render_matrix(graph) == sync.render_matrix(graph)
    assert "CF-24.01" in sync.render_matrix(graph)


def test_committed_pack_bodies_are_exact_lf_text() -> None:
    """Every v5 body is on disk exactly as the manifest pins it."""
    pack = ROOT / "docs/roadmap-v5"
    manifest = json.loads(
        (pack / "github-issues/filing-manifest.json").read_text(encoding="utf-8")
    )
    bodies = sync.read_pack_bodies(pack)
    assert set(bodies) == {row["id"] for row in manifest["issues"]}
    for row in manifest["issues"]:
        assert b"\r" not in (pack / row["body"]).read_bytes(), row["id"]
