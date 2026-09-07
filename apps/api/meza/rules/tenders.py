"""Tender fit analysis (§12): does ATON+ have the production capability and time to bid?
Deterministic — the LLM only decides *when* to run this, never computes the score itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class TenderFitResult:
    required_work_centers: list[str]
    available_work_centers: list[str]
    missing_work_centers: list[str]
    capability_coverage: float  # 0..1 — fraction of required work centers ATON+ has
    days_to_deadline: int | None
    lead_time_ok: bool
    fit_score: float  # 0..1 composite
    verdict: str  # GO_CANDIDATE / MARGINAL / NO_GO_CANDIDATE
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "required_work_centers": self.required_work_centers,
            "available_work_centers": self.available_work_centers,
            "missing_work_centers": self.missing_work_centers,
            "capability_coverage": round(self.capability_coverage, 3),
            "days_to_deadline": self.days_to_deadline,
            "lead_time_ok": self.lead_time_ok,
            "fit_score": round(self.fit_score, 3),
            "verdict": self.verdict,
            "reasons": self.reasons,
        }


def analyze_fit(
    *,
    required_work_centers: list[str],
    available_work_centers: list[str],
    submission_deadline: date | None,
    today: date,
    min_lead_days: int = 3,
) -> TenderFitResult:
    required = set(required_work_centers or [])
    available = set(available_work_centers or [])
    missing = sorted(required - available)
    coverage = 1.0 if not required else round(len(required & available) / len(required), 3)

    days_left = (submission_deadline - today).days if submission_deadline else None
    lead_time_ok = days_left is None or days_left >= min_lead_days

    reasons = []
    if missing:
        reasons.append(f"Нет своих мощностей для: {', '.join(missing)}.")
    if days_left is not None and days_left < 0:
        reasons.append("Срок подачи уже прошёл.")
    elif days_left is not None and not lead_time_ok:
        reasons.append(f"До дедлайна подачи всего {days_left} дн. — может не хватить времени на подготовку.")

    fit_score = round(coverage * (1.0 if lead_time_ok else 0.5) * (0.0 if (days_left is not None and days_left < 0) else 1.0), 3)

    if fit_score >= 0.75:
        verdict = "GO_CANDIDATE"
    elif fit_score >= 0.4:
        verdict = "MARGINAL"
    else:
        verdict = "NO_GO_CANDIDATE"

    return TenderFitResult(
        required_work_centers=sorted(required), available_work_centers=sorted(available),
        missing_work_centers=missing, capability_coverage=coverage, days_to_deadline=days_left,
        lead_time_ok=lead_time_ok, fit_score=fit_score, verdict=verdict, reasons=reasons,
    )
