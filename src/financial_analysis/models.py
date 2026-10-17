from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd


@dataclass
class FinancialMetricResult:
    """Represents a computed financial indicator with formula and verified numbers."""
    metric_name: str
    value: float
    formatted_value: str
    unit: str = "USD"
    formula: str = ""
    period: Optional[str] = None
    source_table: Optional[str] = None
    breakdown: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """Represents side-by-side comparative analysis between periods or documents."""
    metric_name: str
    period_1: str
    value_1: float
    period_2: str
    value_2: float
    absolute_change: float
    percentage_change: float
    trend: str  # 'increase', 'decrease', 'neutral'
