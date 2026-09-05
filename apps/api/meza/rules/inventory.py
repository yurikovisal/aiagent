"""Material availability / shortage calculations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class IncomingShipment:
    quantity: float
    expected_at: date | None
    reference: str = ""
    supplier: str = ""


@dataclass
class AvailabilityResult:
    material: str
    required: float
    on_hand: float
    reserved_by_others: float
    available: float
    shortage: float
    needed_by: date | None
    incoming_in_time: float
    incoming_late: float
    shortage_after_incoming: float
    status: str  # OK | COVERED_BY_INCOMING | SHORTAGE
    incoming: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["needed_by"] = self.needed_by.isoformat() if self.needed_by else None
        return d


def check_availability(
    *,
    material: str,
    required: float,
    on_hand: float,
    reserved_by_others: float = 0.0,
    needed_by: date | None = None,
    incoming: list[IncomingShipment] | None = None,
) -> AvailabilityResult:
    """Deterministic shortage calculation.

    available = on_hand - reserved_by_others
    shortage  = max(0, required - available)
    incoming shipments only count if they arrive on/before needed_by (or if needed_by unknown).
    """
    incoming = incoming or []
    available = max(0.0, on_hand - reserved_by_others)
    shortage = max(0.0, required - available)
    in_time = 0.0
    late = 0.0
    inc_rows = []
    notes: list[str] = []
    for s in incoming:
        arrives_in_time = needed_by is None or (s.expected_at is not None and s.expected_at <= needed_by)
        if s.expected_at is None:
            arrives_in_time = False
            notes.append(f"Поставка {s.reference or ''} без даты прибытия — не учитывается.")
        if arrives_in_time:
            in_time += s.quantity
        else:
            late += s.quantity
            if s.expected_at and needed_by:
                days_late = (s.expected_at - needed_by).days
                notes.append(
                    f"Поставка {s.reference or s.supplier or ''} {s.quantity:g} прибудет {s.expected_at.isoformat()}, "
                    f"на {days_late} дн. позже потребности ({needed_by.isoformat()})."
                )
        inc_rows.append(
            {
                "quantity": s.quantity,
                "expected_at": s.expected_at.isoformat() if s.expected_at else None,
                "reference": s.reference,
                "supplier": s.supplier,
                "in_time": arrives_in_time,
            }
        )
    shortage_after = max(0.0, shortage - in_time)
    if shortage == 0:
        status = "OK"
    elif shortage_after == 0:
        status = "COVERED_BY_INCOMING"
    else:
        status = "SHORTAGE"
    return AvailabilityResult(
        material=material,
        required=required,
        on_hand=on_hand,
        reserved_by_others=reserved_by_others,
        available=available,
        shortage=round(shortage, 3),
        needed_by=needed_by,
        incoming_in_time=in_time,
        incoming_late=late,
        shortage_after_incoming=round(shortage_after, 3),
        status=status,
        incoming=inc_rows,
        notes=notes,
    )


def days_of_cover(on_hand: float, daily_consumption: float) -> float | None:
    if daily_consumption <= 0:
        return None
    return round(on_hand / daily_consumption, 1)


def is_slow_moving(last_movement_days: int | None, threshold_days: int = 90, quantity: float = 0) -> bool:
    return quantity > 0 and (last_movement_days is None or last_movement_days >= threshold_days)
