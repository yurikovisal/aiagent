"""FileConnector: reads local files (used by the Document Agent / Import Center). This one is
fully implemented — it's the backbone of Import Center + Inbox until live system connectors
exist."""

from __future__ import annotations

from pathlib import Path

from meza.connectors.base import BaseConnector, ConnectorHealth


class FileConnector(BaseConnector):
    name = "file"

    def __init__(self, root: Path):
        self.root = root

    async def health(self) -> ConnectorHealth:
        ok = self.root.exists() and self.root.is_dir()
        return ConnectorHealth(connected=ok, detail=str(self.root))

    def list_files(self, pattern: str = "*") -> list[Path]:
        if not self.root.exists():
            return []
        return sorted(self.root.glob(pattern))

    def read_bytes(self, relative_path: str) -> bytes:
        return (self.root / relative_path).read_bytes()
