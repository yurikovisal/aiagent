"""Tool contract. Every tool declares its schema, permission and risk explicitly (§27)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.rbac import Permission


class ToolRisk(StrEnum):
    READ = "READ"
    CALCULATE = "CALCULATE"
    PROPOSE = "PROPOSE"
    WRITE_LOW_RISK = "WRITE_LOW_RISK"
    WRITE_HIGH_RISK = "WRITE_HIGH_RISK"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"


AUTO_EXECUTE_RISKS = {ToolRisk.READ, ToolRisk.CALCULATE, ToolRisk.PROPOSE}
APPROVAL_REQUIRED_RISKS = {ToolRisk.WRITE_LOW_RISK, ToolRisk.WRITE_HIGH_RISK, ToolRisk.EXTERNAL_ACTION}


@dataclass
class ToolContext:
    db: AsyncSession
    user_id: int | None
    role: str
    run_id: str
    agent_id: str


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    summary: str = ""
    sources: list[dict] = field(default_factory=list)
    error: str | None = None
    pending_approval_id: int | None = None


class Tool(ABC):
    name: str
    description: str
    risk: ToolRisk
    required_permission: Permission | None = None
    input_schema: dict = {}
    output_schema: dict = {}

    @abstractmethod
    async def run(self, ctx: ToolContext, **kwargs) -> ToolResult: ...

    def to_manifest(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "risk": self.risk.value,
            "permission": self.required_permission.value if self.required_permission else None,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }
