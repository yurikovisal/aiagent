"""Document ingestion: extraction + rule-based classification (§18)."""

from __future__ import annotations

import re
from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".csv", ".png", ".jpg", ".jpeg"}

CLASSIFICATION_RULES: list[tuple[str, list[str]]] = [
    ("CONTRACT", ["договор", "contract", "соглашение"]),
    ("INVOICE", ["счёт", "счет-фактура", "invoice", "накладная"]),
    ("COMMERCIAL_OFFER", ["коммерческое предложение", "commercial offer", "offer"]),
    ("SPECIFICATION", ["спецификац", "specification", "чертёж", "drawing"]),
    ("INSTRUCTION", ["инструкция", "instruction", "manual"]),
    ("REGULATION", ["регламент", "положение", "policy", "regulation"]),
    ("TECH_DOC", ["технич", "technical", "datasheet"]),
    ("REPORT", ["отчёт", "report"]),
]


def extract_text(path: Path, ext: str) -> str:
    try:
        if ext == ".txt" or ext == ".csv":
            return path.read_text(errors="ignore")
        if ext == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        if ext == ".docx":
            from docx import Document as DocxDocument

            d = DocxDocument(str(path))
            return "\n".join(p.text for p in d.paragraphs)
        if ext == ".xlsx":
            from openpyxl import load_workbook

            wb = load_workbook(str(path), read_only=True, data_only=True)
            lines = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    lines.append(" ".join(str(c) for c in row if c is not None))
            return "\n".join(lines)
    except Exception:  # noqa: BLE001
        return ""
    return ""


def classify_document(filename: str, text: str) -> tuple[str, float]:
    haystack = f"{filename}\n{text[:5000]}".lower()
    for doc_type, keywords in CLASSIFICATION_RULES:
        for kw in keywords:
            if kw in haystack:
                return doc_type, 0.75
    return "UNCLASSIFIED", 0.0


DATE_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b")
AMOUNT_RE = re.compile(r"\b(\d[\d\s]{3,})\s?(тенге|kzt|₸|руб|usd|\$)\b", re.I)


def extract_metadata(text: str) -> dict:
    dates = DATE_RE.findall(text[:20_000])
    amounts = AMOUNT_RE.findall(text[:20_000])
    return {
        "dates_found": [f"{d}.{m}.{y}" for d, m, y in dates[:10]],
        "amounts_found": [f"{a.strip()} {cur}" for a, cur in amounts[:10]],
    }
