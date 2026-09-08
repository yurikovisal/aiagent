"""Intent / Agent Router (§28). Deterministic keyword routing first (fast, explainable,
no LLM cost for the common cases); falls back to the LLM classifier only for ambiguous text.
"""

from __future__ import annotations

import re

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "sales": ["сделк", "клиент", "продаж", "deal", "customer", "follow-up", "конверси"],
    "production": ["производств", "цех", "станок", "чпу", "сварк", "покрас", "этап", "production", "cnc", "welding"],
    "warehouse": ["склад", "остат", "материал", "запас", "warehouse", "stock", "инвентар"],
    "procurement": ["закуп", "поставщик", "заявк", "purchase", "supplier", "procurement"],
    "finance": ["маржа", "прибыл", "затрат", "себестоимост", "финанс", "оплат", "деньги", "margin", "cost", "profit", "выручк"],
    "projects": ["проект", "задач", "просроч", "дедлайн", "task", "project", "deadline"],
    "documents": ["документ", "договор", "спецификаци", "регламент", "инструкц", "document", "contract"],
    "tenders": ["тендер", "tender", "конкурс"],
    "marketing": ["маркетинг", "кампани", "лид", "campaign", "lead", "публик", "контент", "рассылк", "выложи", "разместить"],
    "hr": ["сотрудник", "отдел", "kpi", "employee", "department", "загруж"],
    "overview": ["что происходит", "внимани", "риск", "что горит", "brief", "сводк", "изменилось", "что нового"],
}

INTENT_PATTERNS = [
    ("what_changed", re.compile(r"(что\s+изменил|what\s+changed|изменения\s+за)", re.I)),
    ("daily_brief", re.compile(r"(утренн(ий|юю)\s+отчёт|daily\s+brief|доброе\s+утро|подготовь\s+отчёт)", re.I)),
    ("needs_attention", re.compile(r"(что\s+горит|требует\s+внимани|needs\s+attention)", re.I)),
    ("why_delayed", re.compile(r"(почему\s+задержива|why\s+.*delay)", re.I)),
    ("simulate", re.compile(r"(что\s+произойдёт|что\s+будет,\s+если|what\s+if)", re.I)),
]


def classify_intent(text: str) -> str | None:
    for intent, pattern in INTENT_PATTERNS:
        if pattern.search(text):
            return intent
    return None


def route_domains(text: str) -> list[str]:
    """Return the ordered list of domains relevant to free text. Falls back to ['overview']
    (broad fan-out) when nothing matches, so a vague question still gets *something* useful."""
    lowered = text.lower()
    hits = []
    for domain, kws in DOMAIN_KEYWORDS.items():
        if any(kw in lowered for kw in kws):
            hits.append(domain)
    if not hits:
        hits = ["overview"]
    # "overview" style broad questions ("что требует внимания", "что горит") fan out across the
    # core operational domains AND consult the centralized Risk Engine (via 'overview' ->
    # AnalyticsAgent) so already-detected risks are never dropped just because a narrower domain
    # agent didn't independently re-derive them.
    if "overview" in hits:
        hits = ["production", "warehouse", "procurement", "sales", "finance", "projects", "overview"]
    return hits
