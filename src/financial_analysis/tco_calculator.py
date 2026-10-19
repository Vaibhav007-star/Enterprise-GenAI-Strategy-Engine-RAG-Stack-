from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class TCOInputParameters(BaseModel):
    num_employees: int = Field(default=2500, description="Enterprise knowledge workers using the system")
    daily_queries_per_employee: float = Field(default=4.0, description="Average strategic queries per user daily")
    work_days_per_year: int = Field(default=250, description="Annual working days")
    avg_tokens_per_query: int = Field(default=3000, description="Tokens per RAG interaction (prompt + chunks + completion)")
    api_cost_per_million_tokens: float = Field(default=2.00, description="Blended API token price per 1M tokens ($)")
    self_hosted_gpu_cluster_annual_cost: float = Field(default=120000.0, description="Annual OpEx for dedicated GPU cluster (e.g. 2x 8xH100)")
    employee_hourly_cost: float = Field(default=85.0, description="Fully burdened hourly cost of corporate strategist ($)")
    minutes_saved_per_query: float = Field(default=12.0, description="Minutes saved vs manual 10-K search and cross-referencing")
    total_transformation_budget: float = Field(default=1500000.0, description="Total Enterprise GenAI budget ($)")


class TCOSimulationResult(BaseModel):
    # Volume Metrics
    annual_query_volume: int
    annual_tokens_consumed_billions: float

    # Run-Rate Cost Comparison
    annual_api_token_cost: float
    annual_self_hosted_cost: float
    recommended_infrastructure_mode: str
    infrastructure_annual_savings: float

    # BCG 10-20-70 Budget Allocation Breakdown
    bcg_10_algorithms_budget: float
    bcg_20_tech_data_budget: float
    bcg_70_people_workflows_budget: float

    # Business Value Realization & ROI
    annual_hours_saved: float
    annual_gross_productivity_value: float
    annual_net_ebitda_impact: float
    roi_percentage: float
    payback_period_months: float
    executive_verdict: str


class EnterpriseTCOEngine:
    """BCG X Enterprise GenAI Total Cost of Ownership (TCO) & Value Realization Engine.
    Implements the 10-20-70 transformation rule and deterministic financial payback modeling."""

    @classmethod
    def calculate_tco(cls, params: Optional[TCOInputParameters] = None) -> TCOSimulationResult:
        if params is None:
            params = TCOInputParameters()

        # 1. Volume Projections
        annual_queries = int(params.num_employees * params.daily_queries_per_employee * params.work_days_per_year)
        total_tokens = annual_queries * params.avg_tokens_per_query
        tokens_in_billions = round(total_tokens / 1_000_000_000.0, 3)

        # 2. Infra Costs (Cloud API vs Self-Hosted Dedicated)
        annual_api_cost = (total_tokens / 1_000_000.0) * params.api_cost_per_million_tokens
        annual_self_hosted = params.self_hosted_gpu_cluster_annual_cost

        if annual_api_cost < annual_self_hosted:
            rec_mode = "Cloud Managed API"
            infra_savings = round(annual_self_hosted - annual_api_cost, 2)
            active_infra_cost = annual_api_cost
        else:
            rec_mode = "Self-Hosted Private vLLM / Ollama"
            infra_savings = round(annual_api_cost - annual_self_hosted, 2)
            active_infra_cost = annual_self_hosted

        # 3. BCG 10-20-70 Rule Budget
        total_budget = params.total_transformation_budget
        bcg_10 = round(total_budget * 0.10, 2)
        bcg_20 = round(total_budget * 0.20, 2)
        bcg_70 = round(total_budget * 0.70, 2)

        # 4. Productivity & EBITDA Realization
        total_minutes_saved = annual_queries * params.minutes_saved_per_query
        annual_hours_saved = round(total_minutes_saved / 60.0, 1)
        gross_value = round(annual_hours_saved * params.employee_hourly_cost, 2)
        
        # Net annual EBITDA benefit (Gross productivity value minus ongoing infra run-rate)
        net_ebitda = round(gross_value - active_infra_cost, 2)

        # ROI & Payback period
        if total_budget > 0:
            roi_pct = round(((net_ebitda - (total_budget / 3.0)) / (total_budget / 3.0)) * 100.0, 1)
            monthly_net_benefit = net_ebitda / 12.0
            payback_months = round(total_budget / max(monthly_net_benefit, 1.0), 1)
        else:
            roi_pct = 0.0
            payback_months = 0.0

        if payback_months <= 12.0:
            verdict = "Exceptional Tier-1 Transformation. High EBITDA yield with payback in under 12 months."
        elif payback_months <= 24.0:
            verdict = "Strong Enterprise Business Case. Steady ROI with positive cash flow within 2 years."
        else:
            verdict = "Moderate Long-Term Strategy. Focus adoption on high-margin business units."

        return TCOSimulationResult(
            annual_query_volume=annual_queries,
            annual_tokens_consumed_billions=tokens_in_billions,
            annual_api_token_cost=round(annual_api_cost, 2),
            annual_self_hosted_cost=round(annual_self_hosted, 2),
            recommended_infrastructure_mode=rec_mode,
            infrastructure_annual_savings=infra_savings,
            bcg_10_algorithms_budget=bcg_10,
            bcg_20_tech_data_budget=bcg_20,
            bcg_70_people_workflows_budget=bcg_70,
            annual_hours_saved=annual_hours_saved,
            annual_gross_productivity_value=gross_value,
            annual_net_ebitda_impact=net_ebitda,
            roi_percentage=roi_pct,
            payback_period_months=payback_months,
            executive_verdict=verdict
        )
