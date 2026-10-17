import hashlib
import numpy as np
from typing import List, Optional
from .base_embedding import BaseEmbeddingProvider
from ..utils.logger import get_logger

logger = get_logger("embedding_service")


class SentenceTransformerEmbedding(BaseEmbeddingProvider):
    """Sentence Transformers local embedding model provider."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._dim = 384

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer model '{self.model_name}' on device '{self.device}'...")
                self._model = SentenceTransformer(self.model_name, device=self.device)
                if hasattr(self._model, "get_embedding_dimension"):
                    self._dim = self._model.get_embedding_dimension()
                else:
                    self._dim = self._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded '{self.model_name}' successfully. Embedding dimension: {self._dim}")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer '{self.model_name}': {e}. Falling back to deterministic embeddings.")
                self._model = "fallback"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        if self._model == "fallback" or self._model is None:
            return [self._fallback_embed(t) for t in texts]
        embeddings = self._model.encode(texts, convert_to_numpy=True, batch_size=32, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        self._load_model()
        if self._model == "fallback" or self._model is None:
            return self._fallback_embed(text)
        embedding = self._model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding.tolist()

    @property
    def dimension(self) -> int:
        return self._dim

    def _fallback_embed(self, text: str) -> List[float]:
        """Deterministic pseudo-embedding for testing or fallback when offline."""
        rng = np.random.RandomState(int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16))
        vec = rng.randn(self._dim)
        norm = np.linalg.norm(vec)
        return (vec / (norm if norm > 0 else 1.0)).tolist()


class EmbeddingFactory:
    """Factory to retrieve configured embedding provider."""

    _instance: Optional[BaseEmbeddingProvider] = None

    @classmethod
    def get_provider(cls, provider_type: str = "sentence-transformers", model_name: str = "all-MiniLM-L6-v2", device: str = "cpu") -> BaseEmbeddingProvider:
        if cls._instance is None:
            cls._instance = SentenceTransformerEmbedding(model_name=model_name, device=device)
        return cls._instance
