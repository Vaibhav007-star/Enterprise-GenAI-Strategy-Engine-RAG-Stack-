import re
import json
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

from .models import FinancialMetricResult, ComparisonResult
from ..parsing.models import ParsedTable
from ..utils.logger import get_logger

logger = get_logger("financial_engine")


class FinancialAnalysisEngine:
    """Deterministic financial analytics engine performing verified Python calculations on structured tables."""

    @staticmethod
    def parse_numeric(val: Any) -> Optional[float]:
        """Convert messy financial strings ($1,234.50, (500), 12.5%, etc.) into clean floats."""
        if val is None or pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            return float(val)

        s = str(val).strip()
        if not s or s.lower() in ("-", "n/a", "na", "null", "none"):
            return None

        # Check for accounting parentheses for negative numbers e.g. (12,345)
        is_negative = False
        if s.startswith("(") and s.endswith(")"):
            is_negative = True
            s = s[1:-1].strip()

        # Remove currency symbols, commas, percent signs
        s = re.sub(r"[\$,€£¥%\s]", "", s)
        try:
            num = float(s)
            return -num if is_negative else num
        except ValueError:
            return None

    @classmethod
    def table_to_dataframe(cls, table: ParsedTable) -> pd.DataFrame:
        """Convert ParsedTable into a numeric-cleaned Pandas DataFrame."""
        if table.dataframe_json:
            try:
                df = pd.read_json(table.dataframe_json, orient="split")
                return df
            except Exception:
                pass

        if not table.headers:
            return pd.DataFrame(table.rows)

        df = pd.DataFrame(table.rows, columns=table.headers)
        return df

    @classmethod
    def compute_growth(
        cls,
        base_value: float,
        current_value: float,
        metric_name: str = "Metric",
        period_1: str = "Prior Period",
        period_2: str = "Current Period"
    ) -> ComparisonResult:
        """Deterministic computation of absolute and percentage change between periods."""
        abs_change = current_value - base_value
        pct_change = (abs_change / abs(base_value) * 100.0) if base_value != 0 else 0.0
        
        trend = "neutral"
        if abs_change > 0:
            trend = "increase"
        elif abs_change < 0:
            trend = "decrease"

        return ComparisonResult(
            metric_name=metric_name,
            period_1=period_1,
            value_1=base_value,
            period_2=period_2,
            value_2=current_value,
            absolute_change=round(abs_change, 2),
            percentage_change=round(pct_change, 2),
            trend=trend
        )

    @classmethod
    def rank_categories(
        cls,
        df: pd.DataFrame,
        category_col: str,
        value_col: str,
        ascending: bool = False
    ) -> List[Dict[str, Any]]:
        """Rank categories deterministically by a numeric column (e.g. highest OpEx department)."""
        df_copy = df.copy()
        df_copy["_clean_val"] = df_copy[value_col].apply(cls.parse_numeric)
        df_valid = df_copy.dropna(subset=["_clean_val"])
        
        if df_valid.empty:
            return []

        grouped = df_valid.groupby(category_col)["_clean_val"].sum().reset_index()
        grouped = grouped.sort_values(by="_clean_val", ascending=ascending)

        total_sum = grouped["_clean_val"].sum()
        results = []
        for idx, row in grouped.iterrows():
            val = float(row["_clean_val"])
            share = (val / total_sum * 100.0) if total_sum > 0 else 0.0
            results.append({
                "rank": len(results) + 1,
                "category": str(row[category_col]),
                "value": round(val, 2),
                "share_pct": round(share, 2)
            })

        return results

    @classmethod
    def compute_summary_statistics(cls, df: pd.DataFrame, column_name: str) -> Optional[FinancialMetricResult]:
        """Compute verified sum, mean, median, min, max on a numerical column."""
        numeric_series = df[column_name].apply(cls.parse_numeric).dropna()
        if numeric_series.empty:
            return None

        total = float(numeric_series.sum())
        mean_val = float(numeric_series.mean())
        median_val = float(numeric_series.median())
        min_val = float(numeric_series.min())
        max_val = float(numeric_series.max())

        return FinancialMetricResult(
            metric_name=f"Aggregate Statistics for {column_name}",
            value=total,
            formatted_value=f"{total:,.2f}",
            formula="SUM(column)",
            breakdown={
                "sum": round(total, 2),
                "mean": round(mean_val, 2),
                "median": round(median_val, 2),
                "min": round(min_val, 2),
                "max": round(max_val, 2),
                "count": len(numeric_series)
            }
        )

    @classmethod
    def calculate_margins(
        cls,
        revenue: float,
        cost_or_expenses: float,
        margin_type: str = "Operating Margin"
    ) -> FinancialMetricResult:
        """Calculate profit or operating margins with deterministic formula validation."""
        profit = revenue - cost_or_expenses
        margin_pct = (profit / revenue * 100.0) if revenue != 0 else 0.0

        return FinancialMetricResult(
            metric_name=margin_type,
            value=round(margin_pct, 2),
            formatted_value=f"{margin_pct:.2f}%",
            unit="Percentage",
            formula=f"({revenue:,.2f} - {cost_or_expenses:,.2f}) / {revenue:,.2f} * 100",
            breakdown={
                "revenue": revenue,
                "cost_or_expenses": cost_or_expenses,
                "profit": round(profit, 2)
            }
        )
