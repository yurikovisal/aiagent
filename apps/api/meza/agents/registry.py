"""Agent Registry — every specialized agent MEZA can route to."""

from __future__ import annotations

from meza.agents.analytics import AnalyticsAgent
from meza.agents.base import Agent
from meza.agents.documents import DocumentAgent
from meza.agents.executive import ExecutiveAgent
from meza.agents.finance import FinanceControllerAgent
from meza.agents.hr import HRAgent
from meza.agents.marketing import MarketingAgent
from meza.agents.procurement import ProcurementAgent
from meza.agents.production import ProductionAgent
from meza.agents.projects import ProjectManagerAgent
from meza.agents.sales import SalesAgent
from meza.agents.tender import TenderAgent
from meza.agents.warehouse import WarehouseAgent

_AGENTS: dict[str, Agent] = {}


def _register(agent: Agent) -> None:
    _AGENTS[agent.agent_id] = agent


def _bootstrap() -> None:
    if _AGENTS:
        return
    for cls in (
        ExecutiveAgent, SalesAgent, ProductionAgent, WarehouseAgent, ProcurementAgent,
        FinanceControllerAgent, ProjectManagerAgent, DocumentAgent, TenderAgent, MarketingAgent,
        HRAgent, AnalyticsAgent,
    ):
        _register(cls())


_bootstrap()

DOMAIN_TO_AGENT = {
    "sales": "sales", "production": "production", "warehouse": "warehouse",
    "procurement": "procurement", "finance": "finance", "projects": "projects",
    "documents": "documents", "tenders": "tenders", "marketing": "marketing", "hr": "hr",
    "overview": "analytics",
}


def get_agent(agent_id: str) -> Agent | None:
    return _AGENTS.get(agent_id)


def all_agents() -> list[Agent]:
    return list(_AGENTS.values())


def manifest() -> list[dict]:
    return [a.manifest() for a in all_agents()]
