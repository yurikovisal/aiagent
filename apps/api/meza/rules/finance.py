"""PLAN vs ACTUAL management accounting per order. All formulas run in code, never in the LLM."""

from __future__ import annotations

from dataclasses import dataclass, field

COST_CATEGORIES = ("MATERIAL", "LABOR", "SUBCONTRACTOR", "LOGISTICS", "INSTALLATION", "OTHER")

CATEGORY_LABELS_RU = {
    "MATERIAL": "Материалы",
    "LABOR": "Работа",
    "SUBCONTRACTOR": "Субподряд",
    "LOGISTICS": "Логистика",
    "INSTALLATION": "Монтаж",
    "OTHER": "Прочее",
}


@dataclass
class CategoryVariance:
    category: str
    planned: float
    actual: float

    @property
    def variance(self) -> float:
        return round(self.actual - self.planned, 2)

    @property
    def variance_pct(self) -> float | None:
        if self.planned == 0:
            return None
        return round((self.actual - self.planned) / self.planned * 100, 2)

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "label": CATEGORY_LABELS_RU.get(self.category, self.category),
            "planned": round(self.planned, 2),
            "actual": round(self.actual, 2),
            "variance": self.variance,
            "variance_pct": self.variance_pct,
        }


@dataclass
class MarginResult:
    revenue: float
    planned_by_category: dict[str, float]
    actual_by_category: dict[str, float]
    categories: list[CategoryVariance] = field(default_factory=list)

    @property
    def planned_total(self) -> float:
        return round(sum(self.planned_by_category.values()), 2)

    @property
    def actual_total(self) -> float:
        return round(sum(self.actual_by_category.values()), 2)

    @property
    def planned_gross_profit(self) -> float:
        return round(self.revenue - self.planned_total, 2)

    @property
    def actual_gross_profit(self) -> float:
        return round(self.revenue - self.actual_total, 2)

    @property
    def planned_margin(self) -> float | None:
        return round(self.planned_gross_profit / self.revenue, 4) if self.revenue else None

    @property
    def actual_margin(self) -> float | None:
        return round(self.actual_gross_profit / self.revenue, 4) if self.revenue else None

    @property
    def cost_variance(self) -> float:
        return round(self.actual_total - self.planned_total, 2)

    @property
    def cost_variance_pct(self) -> float | None:
        return round(self.cost_variance / self.planned_total * 100, 2) if self.planned_total else None

    @property
    def margin_delta_points(self) -> float | None:
        if self.planned_margin is None or self.actual_margin is None:
            return None
        return round((self.actual_margin - self.planned_margin) * 100, 2)

    def top_overruns(self, limit: int = 3) -> list[CategoryVariance]:
        return sorted([c for c in self.categories if c.variance > 0], key=lambda c: -c.variance)[:limit]

    def as_dict(self) -> dict:
        return {
            "revenue": round(self.revenue, 2),
            "planned_cost": self.planned_total,
            "actual_cost": self.actual_total,
            "cost_variance": self.cost_variance,
            "cost_variance_pct": self.cost_variance_pct,
            "planned_gross_profit": self.planned_gross_profit,
            "actual_gross_profit": self.actual_gross_profit,
            "planned_margin": self.planned_margin,
            "actual_margin": self.actual_margin,
            "margin_delta_points": self.margin_delta_points,
            "categories": [c.as_dict() for c in self.categories],
            "top_overruns": [c.as_dict() for c in self.top_overruns()],
        }


def compute_margin(revenue: float, planned: dict[str, float], actual: dict[str, float]) -> MarginResult:
    """Compute plan-vs-actual margin. Unknown categories are folded into OTHER."""
    p = dict.fromkeys(COST_CATEGORIES, 0.0)
    a = dict.fromkeys(COST_CATEGORIES, 0.0)
    for src, dst in ((planned, p), (actual, a)):
        for cat, amount in (src or {}).items():
            key = cat if cat in COST_CATEGORIES else "OTHER"
            dst[key] += float(amount or 0)
    cats = [CategoryVariance(c, p[c], a[c]) for c in COST_CATEGORIES if p[c] or a[c]]
    return MarginResult(revenue=float(revenue or 0), planned_by_category=p, actual_by_category=a, categories=cats)


def explain_variance(result: MarginResult) -> str:
    """Deterministic, human-readable explanation of the cost deviation by category (RU)."""
    if result.cost_variance == 0:
        return "Фактические затраты соответствуют плану."
    direction = "перерасход" if result.cost_variance > 0 else "экономия"
    parts = [
        f"Общий {direction}: {abs(result.cost_variance):,.0f} "
        f"({result.cost_variance_pct:+.1f}% к плану)." if result.cost_variance_pct is not None else f"Общий {direction}: {abs(result.cost_variance):,.0f}."
    ]
    for c in result.top_overruns():
        pct = f" ({c.variance_pct:+.1f}%)" if c.variance_pct is not None else ""
        parts.append(f"{c.as_dict()['label']}: план {c.planned:,.0f}, факт {c.actual:,.0f}, отклонение {c.variance:+,.0f}{pct}.")
    if result.margin_delta_points is not None:
        parts.append(
            f"Валовая маржа: план {result.planned_margin * 100:.1f}% → факт {result.actual_margin * 100:.1f}% "
            f"({result.margin_delta_points:+.1f} п.п.)."
        )
    return " ".join(parts)
