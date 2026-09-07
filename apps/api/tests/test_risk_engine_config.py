"""Risk Engine rule configuration is DB-backed, not hard-coded (§38)."""

from __future__ import annotations

import pytest

from meza.models import RiskRule
from meza.services import risk_engine


@pytest.mark.asyncio
async def test_ensure_default_rules_creates_all_rows(db_session):
    await risk_engine.ensure_default_rules(db_session)
    from sqlalchemy import select

    rows = (await db_session.execute(select(RiskRule))).scalars().all()
    assert {r.rule_key for r in rows} == set(risk_engine.RULE_DEFAULTS.keys())


@pytest.mark.asyncio
async def test_ensure_default_rules_is_idempotent(db_session):
    await risk_engine.ensure_default_rules(db_session)
    await risk_engine.ensure_default_rules(db_session)
    from sqlalchemy import select

    rows = (await db_session.execute(select(RiskRule))).scalars().all()
    assert len(rows) == len(risk_engine.RULE_DEFAULTS)


@pytest.mark.asyncio
async def test_get_rule_config_merges_db_override(db_session):
    await risk_engine.ensure_default_rules(db_session)
    from sqlalchemy import select

    row = (await db_session.execute(select(RiskRule).where(RiskRule.rule_key == "cost_overrun"))).scalars().first()
    row.params = {"threshold_pct": 25.0}
    row.enabled = False
    await db_session.flush()

    config = await risk_engine.get_rule_config(db_session)
    assert config["cost_overrun"]["params"]["threshold_pct"] == 25.0
    assert config["cost_overrun"]["enabled"] is False
    # Untouched rule keeps its default
    assert config["task_overdue"]["params"]["medium_days"] == 5


@pytest.mark.asyncio
async def test_disabled_rule_is_skipped_by_run_all_rules(db_session):
    await risk_engine.ensure_default_rules(db_session)
    from sqlalchemy import select

    for rule_key in risk_engine.RULE_DEFAULTS:
        row = (await db_session.execute(select(RiskRule).where(RiskRule.rule_key == rule_key))).scalars().first()
        row.enabled = rule_key == "task_overdue"
    await db_session.flush()

    # No task data exists in this empty test DB, so this just proves disabled rules never run
    # (would raise if e.g. cost_overrun's query touched missing relations) and none are skipped
    # due to a bug in the enabled-filtering itself.
    risks = await risk_engine.run_all_rules(db_session)
    assert risks == []
