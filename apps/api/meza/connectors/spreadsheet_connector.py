"""SpreadsheetConnector: thin wrapper over the Import Center's CSV/XLSX readers, exposed as a
connector so it fits the same interface agents expect (`list_rows`)."""

from __future__ import annotations

from pathlib import Path

from meza.connectors.base import BaseConnector, ConnectorHealth
from meza.services.import_center import read_rows


class SpreadsheetConnector(BaseConnector):
    name = "spreadsheet"

    def __init__(self, path: Path):
        self.path = path

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self.path.exists(), detail=str(self.path))

    def list_rows(self) -> list[dict]:
        ext = self.path.suffix.lower().lstrip(".")
        file_type = {"csv": "csv", "xlsx": "xlsx", "json": "json"}.get(ext)
        if not file_type:
            return []
        return read_rows(file_type, self.path.read_bytes())
