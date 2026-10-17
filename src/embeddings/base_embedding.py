from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute embeddings for a list of document texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Compute embedding for a single search query."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension of the embedding model."""
        pass
