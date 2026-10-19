import time
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from pydantic import BaseModel, Field

from ..embeddings.base_embedding import BaseEmbeddingProvider
from ..utils.logger import get_logger

logger = get_logger("semantic_cache")


class CachedQueryEntry(BaseModel):
    query_text: str
    embedding: List[float]
    response_text: str
    citations: List[Dict[str, Any]]
    critic_audit: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)
    hit_count: int = 0


class CacheStats(BaseModel):
    total_entries: int
    hits: int
    misses: int
    hit_rate_pct: float
    estimated_tokens_saved: int
    estimated_cost_saved_usd: float


class SemanticQueryCache:
    """BCG X High-Performance Semantic Vector Cache.
    Matches queries by embedding cosine similarity (> 0.92) to eliminate redundant LLM calls
    and deliver sub-20ms executive responses."""

    def __init__(
        self,
        similarity_threshold: float = 0.92,
        max_entries: int = 500
    ):
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.entries: List[CachedQueryEntry] = []
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def lookup(
        self,
        query: str,
        query_embedding: List[float]
    ) -> Optional[Tuple[CachedQueryEntry, float]]:
        """Look up query in semantic cache; returns (entry, similarity) if >= threshold."""
        best_entry = None
        best_sim = -1.0

        for entry in self.entries:
            sim = self._cosine_similarity(query_embedding, entry.embedding)
            if sim > best_sim:
                best_sim = sim
                best_entry = entry

        if best_entry and best_sim >= self.similarity_threshold:
            self.hits += 1
            best_entry.hit_count += 1
            logger.info(f"Semantic Cache HIT: '{query[:40]}' matched '{best_entry.query_text[:40]}' (sim={best_sim:.3f})")
            return best_entry, best_sim

        self.misses += 1
        return None

    def store(
        self,
        query: str,
        embedding: List[float],
        response_text: str,
        citations: List[Dict[str, Any]],
        critic_audit: Optional[Dict[str, Any]] = None
    ):
        """Store newly generated result into cache."""
        if len(self.entries) >= self.max_entries:
            # Simple LRU-style eviction: remove entry with lowest hit count or oldest
            self.entries.sort(key=lambda e: (e.hit_count, e.timestamp))
            self.entries.pop(0)

        entry = CachedQueryEntry(
            query_text=query,
            embedding=embedding,
            response_text=response_text,
            citations=citations,
            critic_audit=critic_audit
        )
        self.entries.append(entry)

    def get_stats(self) -> CacheStats:
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100.0) if total_requests > 0 else 0.0
        # Estimate: each hit saves ~3,000 tokens ($0.006 at blended rate)
        tokens_saved = self.hits * 3000
        cost_saved = round((tokens_saved / 1_000_000.0) * 2.0, 4)

        return CacheStats(
            total_entries=len(self.entries),
            hits=self.hits,
            misses=self.misses,
            hit_rate_pct=round(hit_rate, 1),
            estimated_tokens_saved=tokens_saved,
            estimated_cost_saved_usd=cost_saved
        )

    def clear(self):
        self.entries.clear()
        self.hits = 0
        self.misses = 0
