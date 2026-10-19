import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class LatencyBreakdown(BaseModel):
    query_text: str
    is_cache_hit: bool = False
    embedding_ms: float = 0.0
    dense_vector_ms: float = 0.0
    bm25_lexical_ms: float = 0.0
    rrf_fusion_ms: float = 0.0
    reranker_ms: float = 0.0
    llm_generation_ms: float = 0.0
    agentic_critic_ms: float = 0.0
    total_latency_ms: float = 0.0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    estimated_query_cost_usd: float = 0.0


class TelemetryTracker:
    """BCG X Production Observability & Latency Waterfall Profiler.
    Measures microsecond latency for every pipeline stage and estimates token expenditure."""

    def __init__(self, query: str):
        self.query = query
        self.start_times: Dict[str, float] = {}
        self.durations_ms: Dict[str, float] = {}
        self.total_start = time.perf_counter()
        self.is_cache_hit = False
        self.input_tokens = 0
        self.output_tokens = 0

    def start_span(self, span_name: str):
        self.start_times[span_name] = time.perf_counter()

    def end_span(self, span_name: str) -> float:
        if span_name in self.start_times:
            elapsed = (time.perf_counter() - self.start_times[span_name]) * 1000.0
            self.durations_ms[span_name] = round(elapsed, 2)
            return self.durations_ms[span_name]
        return 0.0

    def record_tokens(self, prompt_tokens: int, completion_tokens: int):
        self.input_tokens = prompt_tokens
        self.output_tokens = completion_tokens

    def finalize(self) -> LatencyBreakdown:
        total_ms = round((time.perf_counter() - self.total_start) * 1000.0, 2)
        # Cost estimate: $1.50 per 1M input tokens, $3.00 per 1M output tokens
        cost = round(((self.input_tokens * 1.50) + (self.output_tokens * 3.00)) / 1_000_000.0, 5)

        return LatencyBreakdown(
            query_text=self.query,
            is_cache_hit=self.is_cache_hit,
            embedding_ms=self.durations_ms.get("embedding", 0.0),
            dense_vector_ms=self.durations_ms.get("dense_vector", 0.0),
            bm25_lexical_ms=self.durations_ms.get("bm25_lexical", 0.0),
            rrf_fusion_ms=self.durations_ms.get("rrf_fusion", 0.0),
            reranker_ms=self.durations_ms.get("reranker", 0.0),
            llm_generation_ms=self.durations_ms.get("llm_generation", 0.0),
            agentic_critic_ms=self.durations_ms.get("agentic_critic", 0.0),
            total_latency_ms=total_ms,
            estimated_input_tokens=self.input_tokens,
            estimated_output_tokens=self.output_tokens,
            estimated_query_cost_usd=cost
        )
