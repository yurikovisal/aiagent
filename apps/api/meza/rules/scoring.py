"""Alert scoring / de-duplication to avoid alert fatigue."""

from __future__ import annotations

SEVERITY_WEIGHT = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.5, "LOW": 0.25, "INFO": 0.1}
SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


def risk_score(severity: str, impact: float, urgency: float, confidence: float = 1.0) -> float:
    """0..100 composite score = weighted severity/impact/urgency scaled by confidence."""
    sev = SEVERITY_WEIGHT.get(severity.upper(), 0.3)
    raw = 0.4 * sev + 0.35 * min(max(impact, 0), 1) + 0.25 * min(max(urgency, 0), 1)
    return round(raw * min(max(confidence, 0), 1) * 100, 1)


def severity_from_score(score: float) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 55:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def urgency_from_days(days_left: float | None, horizon_days: float = 14) -> float:
    """1.0 when overdue/now, decays linearly to 0 at horizon."""
    if days_left is None:
        return 0.3
    if days_left <= 0:
        return 1.0
    return round(max(0.0, 1 - days_left / horizon_days), 3)


def impact_from_amount(amount: float, reference: float = 10_000_000) -> float:
    """Money impact normalised against a reference order size."""
    if reference <= 0:
        return 0.5
    return round(min(1.0, max(0.0, amount / reference)), 3)


def dedupe(items: list[dict], key_fields: tuple[str, ...] = ("entity_type", "entity_id", "rule_key")) -> list[dict]:
    """Keep the highest-scored item per key."""
    best: dict[tuple, dict] = {}
    for it in items:
        key = tuple(str(it.get(f)) for f in key_fields)
        if key not in best or it.get("score", 0) > best[key].get("score", 0):
            best[key] = it
    return sorted(best.values(), key=lambda x: -x.get("score", 0))


def merge_related(items: list[dict]) -> list[dict]:
    """Collapse several risks on the same entity into one card with sub-causes (keeps top score)."""
    groups: dict[tuple, list[dict]] = {}
    for it in items:
        groups.setdefault((it.get("entity_type"), str(it.get("entity_id"))), []).append(it)
    merged = []
    for _key, grp in groups.items():
        grp.sort(key=lambda x: -x.get("score", 0))
        head = dict(grp[0])
        if len(grp) > 1:
            head["related"] = [
                {"rule_key": g.get("rule_key"), "title": g.get("title"), "severity": g.get("severity"), "score": g.get("score")}
                for g in grp[1:]
            ]
        merged.append(head)
    return sorted(merged, key=lambda x: -x.get("score", 0))
