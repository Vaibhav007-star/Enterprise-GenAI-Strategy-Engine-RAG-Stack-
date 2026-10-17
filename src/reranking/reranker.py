from typing import List, Dict, Any, Optional
from ..utils.logger import get_logger

logger = get_logger("reranker")


class CrossEncoderReranker:
    """Configurable Cross-Encoder reranker for deep semantic relevance scoring."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", enabled: bool = False):
        self.model_name = model_name
        self.enabled = enabled
        self._model = None

    def _load_model(self):
        if not self.enabled:
            return
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading CrossEncoder model '{self.model_name}'...")
                self._model = CrossEncoder(self.model_name)
                logger.info("CrossEncoder loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder '{self.model_name}': {e}. Reranking will be disabled.")
                self.enabled = False
                self._model = None

    def rerank(self, query: str, candidate_chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank candidate chunks using cross-encoder query-passage interaction."""
        if not candidate_chunks:
            return []

        if not self.enabled:
            return candidate_chunks[:top_k]

        self._load_model()
        if not self._model:
            return candidate_chunks[:top_k]

        pairs = [[query, c.get("content", "")] for c in candidate_chunks]
        try:
            scores = self._model.predict(pairs)
            for idx, score in enumerate(scores):
                candidate_chunks[idx]["rerank_score"] = float(score)
                # Store original score for diagnostic panel
                candidate_chunks[idx]["original_score"] = candidate_chunks[idx].get("score", 0.0)
                candidate_chunks[idx]["score"] = float(score)

            candidate_chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            logger.info(f"Reranked {len(candidate_chunks)} candidates. Best score: {candidate_chunks[0]['rerank_score']:.4f}")
        except Exception as e:
            logger.error(f"Error during reranking: {e}")

        return candidate_chunks[:top_k]
