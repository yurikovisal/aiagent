"""Structured-output validation (§50 Agents: structured output validation)."""

from __future__ import annotations

import pytest

from meza.agents.registry import all_agents
from meza.agents.base import AgentResult
from meza.core.rbac import Role
from meza.tools.base import ToolContext

REQUIRED_KEYS = {"status", "summary", "facts", "findings", "risks", "recommendations",
                  "actions_proposed", "sources", "confidence", "data", "error"}


def test_every_agent_has_manifest_fields():
    for agent in all_agents():
        m = agent.manifest()
        assert m["id"]
        assert m["name"]
        assert m["risk_level"] in ("LOW", "MEDIUM", "HIGH")


def test_agent_result_contract_shape():
    result = AgentResult(status="success", summary="ok")
    d = result.as_dict()
    assert set(d.keys()) == REQUIRED_KEYS


@pytest.mark.asyncio
async def test_warehouse_agent_returns_contract_shape(db_session):
    from meza.agents.warehouse import WarehouseAgent

    ctx = ToolContext(db=db_session, user_id=1, role=Role.ADMIN.value, run_id="r1", agent_id="warehouse")
    result = await WarehouseAgent().handle(ctx, "склад", {})
    assert set(result.as_dict().keys()) == REQUIRED_KEYS
    assert result.status in ("success", "partial", "insufficient_data", "error")
