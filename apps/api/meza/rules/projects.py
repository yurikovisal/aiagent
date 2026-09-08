"""Task/project dependency chain analysis (§19): 'почему задерживается проект X?' needs a causal
chain, not just a list of overdue tasks — deterministic graph walk, same pattern as production
delay propagation (meza/rules/production.py)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskNode:
    id: int
    title: str
    status: str
    due_at: datetime | None
    depends_on_task_id: int | None
    assignee: str | None = None


@dataclass
class BlockerChainStep:
    task_id: int
    title: str
    status: str
    due_at: datetime | None
    is_overdue: bool
    assignee: str | None

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id, "title": self.title, "status": self.status,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "is_overdue": self.is_overdue, "assignee": self.assignee,
        }


@dataclass
class ProjectDelayAnalysis:
    root_cause: BlockerChainStep | None
    chain: list[BlockerChainStep] = field(default_factory=list)
    overdue_task_count: int = 0
    blocked_task_count: int = 0

    def as_dict(self) -> dict:
        return {
            "root_cause": self.root_cause.as_dict() if self.root_cause else None,
            "chain": [s.as_dict() for s in self.chain],
            "overdue_task_count": self.overdue_task_count,
            "blocked_task_count": self.blocked_task_count,
        }


def analyze_project_delay(tasks: list[TaskNode], now: datetime) -> ProjectDelayAnalysis:
    """Walks each unfinished task's dependency chain back to its root: the earliest ancestor
    task that is itself overdue/blocked with no unmet dependency of its own. That root is the
    actual cause; everything downstream is just inheriting the delay."""
    by_id = {t.id: t for t in tasks}
    overdue = [t for t in tasks if t.status != "DONE" and t.due_at and t.due_at < now]
    blocked = [t for t in tasks if t.status == "BLOCKED"]

    def is_overdue(t: TaskNode) -> bool:
        return t.status != "DONE" and bool(t.due_at) and t.due_at < now

    def walk_to_root(t: TaskNode, seen: set[int]) -> TaskNode:
        if t.id in seen:
            return t  # cycle guard
        seen.add(t.id)
        if t.depends_on_task_id and t.depends_on_task_id in by_id:
            dep = by_id[t.depends_on_task_id]
            if dep.status != "DONE":
                return walk_to_root(dep, seen)
        return t

    candidates = sorted(overdue + [t for t in blocked if t not in overdue], key=lambda t: (t.due_at or now))
    if not candidates:
        return ProjectDelayAnalysis(root_cause=None, chain=[], overdue_task_count=0, blocked_task_count=len(blocked))

    worst = candidates[0]
    root = walk_to_root(worst, set())

    chain: list[BlockerChainStep] = []
    node: TaskNode | None = root
    seen_chain: set[int] = set()
    while node and node.id not in seen_chain:
        seen_chain.add(node.id)
        chain.append(BlockerChainStep(node.id, node.title, node.status, node.due_at, is_overdue(node), node.assignee))
        # walk forward from root towards the originally-worst task via reverse dependency lookup
        next_node = next((t for t in tasks if t.depends_on_task_id == node.id and t.id not in seen_chain), None)
        node = next_node

    return ProjectDelayAnalysis(
        root_cause=chain[0] if chain else None, chain=chain,
        overdue_task_count=len(overdue), blocked_task_count=len(blocked),
    )
