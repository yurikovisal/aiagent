"""Connector interfaces (§43). Real ATON+ systems can be wired in incrementally by implementing
one of these adapters — agents/tools never talk to an external system directly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ConnectorHealth:
    connected: bool
    detail: str = ""


class BaseConnector(ABC):
    name: str

    @abstractmethod
    async def health(self) -> ConnectorHealth: ...


class CRMConnector(BaseConnector):
    """Interface for an external CRM (Bitrix24, amoCRM, ...). Not yet wired to a real system —
    MEZA's own `deals`/`customers` tables are the source of truth until one is implemented."""

    @abstractmethod
    async def list_deals(self, *, stage: str | None = None) -> list[dict]: ...

    @abstractmethod
    async def get_deal(self, external_id: str) -> dict | None: ...


class WarehouseConnector(BaseConnector):
    """Interface for an external WMS. Until implemented, `meza/services/warehouse.py` reads
    directly from MEZA's own inventory tables."""

    @abstractmethod
    async def get_stock(self, sku: str) -> dict | None: ...

    @abstractmethod
    async def list_movements(self, sku: str, *, since=None) -> list[dict]: ...


class AccountingConnector(BaseConnector):
    """Interface for an external accounting system (1C, etc). MEZA's Finance Controller (§17) is
    explicitly a management-accounting layer and does not attempt to replace this system."""

    @abstractmethod
    async def get_invoice(self, external_id: str) -> dict | None: ...

    @abstractmethod
    async def list_payments(self, *, since=None) -> list[dict]: ...


class ProductionConnector(BaseConnector):
    """Interface for an external MES/production system. Until implemented, MEZA's own
    production_orders/production_stages tables are authoritative."""

    @abstractmethod
    async def get_work_order_status(self, external_id: str) -> dict | None: ...
