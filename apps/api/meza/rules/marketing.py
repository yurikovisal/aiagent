"""Campaign performance — cost-per-lead and conversion, computed in code, never by the LLM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CampaignPerformance:
    campaign_id: int
    name: str
    budget: float
    spent: float
    leads_generated: int
    leads_converted: int
    cost_per_lead: float | None
    conversion_rate: float | None
    budget_utilization: float | None

    def as_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id, "name": self.name, "budget": self.budget, "spent": self.spent,
            "leads_generated": self.leads_generated, "leads_converted": self.leads_converted,
            "cost_per_lead": round(self.cost_per_lead, 2) if self.cost_per_lead is not None else None,
            "conversion_rate": round(self.conversion_rate, 4) if self.conversion_rate is not None else None,
            "budget_utilization": round(self.budget_utilization, 4) if self.budget_utilization is not None else None,
        }


def compute_campaign_performance(
    *, campaign_id: int, name: str, budget: float, spent: float, leads_generated: int, leads_converted: int
) -> CampaignPerformance:
    cpl = (spent / leads_generated) if leads_generated > 0 else None
    conv = (leads_converted / leads_generated) if leads_generated > 0 else None
    util = (spent / budget) if budget > 0 else None
    return CampaignPerformance(
        campaign_id=campaign_id, name=name, budget=budget, spent=spent,
        leads_generated=leads_generated, leads_converted=leads_converted,
        cost_per_lead=cpl, conversion_rate=conv, budget_utilization=util,
    )
