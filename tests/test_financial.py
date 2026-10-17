import pytest
import pandas as pd
from src.financial_analysis.financial_engine import FinancialAnalysisEngine


def test_parse_numeric():
    assert FinancialAnalysisEngine.parse_numeric("$1,234.50") == 1234.50
    assert FinancialAnalysisEngine.parse_numeric("(500.00)") == -500.00
    assert FinancialAnalysisEngine.parse_numeric("15.5%") == 15.5
    assert FinancialAnalysisEngine.parse_numeric("-") is None
    assert FinancialAnalysisEngine.parse_numeric(100) == 100.0


def test_compute_growth():
    growth = FinancialAnalysisEngine.compute_growth(
        base_value=100.0,
        current_value=125.0,
        metric_name="Revenue",
        period_1="2023",
        period_2="2024"
    )
    assert growth.absolute_change == 25.0
    assert growth.percentage_change == 25.0
    assert growth.trend == "increase"


def test_calculate_margins():
    margin = FinancialAnalysisEngine.calculate_margins(revenue=1000.0, cost_or_expenses=600.0)
    assert margin.value == 40.0
    assert margin.formatted_value == "40.00%"
    assert margin.breakdown["profit"] == 400.0


def test_rank_categories():
    data = {
        "Department": ["Sales", "Engineering", "Marketing"],
        "Expense": ["$50,000", "$120,000", "$30,000"]
    }
    df = pd.DataFrame(data)
    ranked = FinancialAnalysisEngine.rank_categories(df, "Department", "Expense")
    assert len(ranked) == 3
    assert ranked[0]["category"] == "Engineering"
    assert ranked[0]["value"] == 120000.0
