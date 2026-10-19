from typing import List, Dict, Any
from pydantic import BaseModel


class SensitivityGridResult(BaseModel):
    base_ebitda: float
    cost_reduction_steps_pct: List[float]
    exit_multiples: List[float]
    matrix: List[List[float]]  # Rows: cost_reduction_steps, Cols: exit_multiples (Enterprise Value in $ Billions)
    delta_value_matrix: List[List[float]]  # Incremental EV created


class ScenarioStressSimulator:
    """BCG X Scenario & Stress Testing Engine: Produces 2D sensitivity matrices
    evaluating Enterprise Value impact under varying operating margin efficiencies and exit multiples."""

    @classmethod
    def run_sensitivity_matrix(
        cls,
        base_ebitda_billions: float = 109.4,  # e.g. Microsoft FY24 EBIT
        cost_savings_pcts: List[float] = None,
        multiples: List[float] = None
    ) -> SensitivityGridResult:
        if cost_savings_pcts is None:
            cost_savings_pcts = [2.0, 4.0, 6.0, 8.0, 10.0]  # Efficiency improvements
        if multiples is None:
            multiples = [15.0, 18.0, 22.0, 26.0, 30.0]      # EV / EBITDA multiples

        base_value_matrix = []
        delta_matrix = []

        for eff in cost_savings_pcts:
            row_ev = []
            row_delta = []
            # Improved EBITDA = base * (1 + eff / 100)
            adjusted_ebitda = base_ebitda_billions * (1.0 + (eff / 100.0))
            for m in multiples:
                base_ev = base_ebitda_billions * m
                new_ev = adjusted_ebitda * m
                delta_ev = new_ev - base_ev
                row_ev.append(round(new_ev, 2))
                row_delta.append(round(delta_ev, 2))
            base_value_matrix.append(row_ev)
            delta_matrix.append(row_delta)

        return SensitivityGridResult(
            base_ebitda=base_ebitda_billions,
            cost_reduction_steps_pct=cost_savings_pcts,
            exit_multiples=multiples,
            matrix=base_value_matrix,
            delta_value_matrix=delta_matrix
        )
