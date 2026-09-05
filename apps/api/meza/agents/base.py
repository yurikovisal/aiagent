"""Agent Protocol (§10). Every specialized agent implements this contract and returns the
common structured result — never free-form text that the rest of the system must re-parse."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from meza.tools.base import ToolContext


@dataclass
class Fact:
    fact: str
    source: str
    record_id: Any = None
    confidence: float = 1.0
    timestamp: str | None = None

    def as_dict(self) -> dict:
        return {"fact": self.fact, "source": self.source, "record_id": self.record_id,
                "confidence": self.confidence, "timestamp": self.timestamp}


@dataclass
class AgentResult:
    status: str  # success | partial | insufficient_data | error
    summary: str
    facts: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    actions_proposed: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    confidence: float = 1.0
    data: dict = field(default_factory=dict)
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "status": self.status, "summary": self.summary, "facts": self.facts,
            "findings": self.findings, "risks": self.risks, "recommendations": self.recommendations,
            "actions_proposed": self.actions_proposed, "sources": self.sources,
            "confidence": self.confidence, "data": self.data, "error": self.error,
        }


class Agent(ABC):
    agent_id: str
    name: str
    description: str
    capabilities: list[str] = []
    allowed_tools: list[str] = []
    allowed_data: list[str] = []
    risk_level: str = "LOW"
    requires_approval: bool = False
    timeout_seconds: int = 60

    @abstractmethod
    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult: ...

    def manifest(self) -> dict:
        return {
            "id": self.agent_id, "name": self.name, "description": self.description,
            "capabilities": self.capabilities, "allowed_tools": self.allowed_tools,
            "allowed_data": self.allowed_data, "risk_level": self.risk_level,
            "requires_approval": self.requires_approval, "timeout": self.timeout_seconds,
        }
