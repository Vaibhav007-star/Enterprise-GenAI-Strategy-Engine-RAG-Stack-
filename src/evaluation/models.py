from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TestCase:
    """Evaluation test case with query, ground truth reference, expected doc, and category."""
    case_id: str
    query: str
    expected_doc_name: Optional[str] = None
    expected_keywords: List[str] = field(default_factory=list)
    ground_truth_answer: Optional[str] = None
    test_category: str = "general"  # 'general', 'financial', 'missing_evidence', 'injection', 'citation'


@dataclass
class TestEvaluationResult:
    """Results for an individual evaluation test case."""
    case_id: str
    query: str
    test_category: str
    passed: bool
    context_precision: float
    context_recall: float
    citation_correctness: float
    faithfulness_score: float
    retrieval_latency_ms: float
    total_latency_ms: float
    answer_preview: str
    citations_count: int
    notes: str = ""


@dataclass
class EvaluationSuiteReport:
    """Summary report across the test suite."""
    total_cases: int
    passed_cases: int
    pass_rate_pct: float
    avg_context_precision: float
    avg_context_recall: float
    avg_faithfulness: float
    avg_latency_ms: float
    category_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    case_results: List[TestEvaluationResult] = field(default_factory=list)
