"""Production dependency analysis: downstream impact of a delay along a stage DAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class StageNode:
    id: int | str
    name: str
    work_center: str
    sequence: int
    duration_days: float
    planned_start: date | None = None
    planned_end: date | None = None
    status: str = "PLANNED"
    depends_on: list[int | str] = field(default_factory=list)
    slot_based: bool = False
    slot_interval_days: int = 0


@dataclass
class ImpactStep:
    stage_id: int | str
    stage_name: str
    work_center: str
    delay_days: float
    reason: str
    original_end: date | None
    new_end: date | None

    def as_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "stage": self.stage_name,
            "work_center": self.work_center,
            "delay_days": self.delay_days,
            "reason": self.reason,
            "original_end": self.original_end.isoformat() if self.original_end else None,
            "new_end": self.new_end.isoformat() if self.new_end else None,
        }


@dataclass
class ImpactResult:
    origin_stage_id: int | str
    initial_delay_days: float
    final_delay_days: float
    chain: list[ImpactStep]
    original_completion: date | None
    new_completion: date | None
    deadline: date | None
    deadline_missed_by_days: float | None

    def as_dict(self) -> dict:
        return {
            "origin_stage_id": self.origin_stage_id,
            "initial_delay_days": self.initial_delay_days,
            "final_delay_days": self.final_delay_days,
            "chain": [s.as_dict() for s in self.chain],
            "original_completion": self.original_completion.isoformat() if self.original_completion else None,
            "new_completion": self.new_completion.isoformat() if self.new_completion else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "deadline_missed_by_days": self.deadline_missed_by_days,
        }


def _build_graph(stages: list[StageNode]) -> dict[int | str, list[int | str]]:
    """Return successors map. If no explicit dependencies, use linear order by sequence."""
    by_id = {s.id: s for s in stages}
    has_explicit = any(s.depends_on for s in stages)
    successors: dict[int | str, list[int | str]] = {s.id: [] for s in stages}
    if has_explicit:
        for s in stages:
            for dep in s.depends_on:
                if dep in by_id:
                    successors[dep].append(s.id)
    else:
        ordered = sorted(stages, key=lambda s: s.sequence)
        for prev, nxt in zip(ordered, ordered[1:], strict=False):
            successors[prev.id].append(nxt.id)
    return successors


def propagate_delay(
    stages: list[StageNode],
    origin_stage_id: int | str,
    delay_days: float,
    deadline: date | None = None,
) -> ImpactResult:
    """Propagate a delay from one stage to all downstream stages.

    Rules:
    - a stage's delay = max(delay of its predecessors)
    - slot-based work centers (e.g. powder coating batches) add extra waiting time
      when the incoming delay pushes the stage past its planned slot: wait = slot_interval - (delay mod interval)
    """
    by_id = {s.id: s for s in stages}
    if origin_stage_id not in by_id:
        raise ValueError(f"Unknown stage {origin_stage_id}")
    successors = _build_graph(stages)
    delays: dict[int | str, float] = {origin_stage_id: float(delay_days)}
    chain: list[ImpactStep] = []
    origin = by_id[origin_stage_id]
    chain.append(
        ImpactStep(
            origin.id,
            origin.name,
            origin.work_center,
            float(delay_days),
            "Исходная задержка",
            origin.planned_end,
            origin.planned_end + timedelta(days=delay_days) if origin.planned_end else None,
        )
    )
    # Kahn-style traversal in topological order restricted to the reachable subgraph
    order = sorted(stages, key=lambda s: s.sequence)
    for st in order:
        if st.id == origin_stage_id:
            continue
        preds = [p for p, succ in successors.items() if st.id in succ]
        incoming = [delays[p] for p in preds if p in delays]
        if not incoming:
            continue
        inherited = max(incoming)
        extra = 0.0
        reason = "Сдвиг из-за предыдущего этапа"
        if st.slot_based and st.slot_interval_days > 0 and inherited > 0:
            remainder = inherited % st.slot_interval_days
            if remainder:
                extra = st.slot_interval_days - remainder
                reason = f"Пропущен слот ({st.work_center}), ожидание следующего окна +{extra:g} дн."
        total = inherited + extra
        delays[st.id] = total
        chain.append(
            ImpactStep(
                st.id,
                st.name,
                st.work_center,
                total,
                reason,
                st.planned_end,
                st.planned_end + timedelta(days=total) if st.planned_end else None,
            )
        )
    final_delay = max(delays.values()) if delays else 0.0
    last = max(stages, key=lambda s: s.sequence)
    original_completion = last.planned_end
    new_completion = original_completion + timedelta(days=delays.get(last.id, 0)) if original_completion else None
    missed = None
    if deadline and new_completion:
        missed = float(max(0, (new_completion - deadline).days))
    return ImpactResult(
        origin_stage_id=origin_stage_id,
        initial_delay_days=float(delay_days),
        final_delay_days=float(final_delay),
        chain=chain,
        original_completion=original_completion,
        new_completion=new_completion,
        deadline=deadline,
        deadline_missed_by_days=missed,
    )


def remaining_duration_days(stages: list[StageNode]) -> float:
    """Sum of remaining work for not-done stages (linear approximation, progress-aware)."""
    total = 0.0
    for s in stages:
        if s.status == "DONE":
            continue
        total += s.duration_days
    return total
