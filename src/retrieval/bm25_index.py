import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from ..utils.logger import get_logger

logger = get_logger("bm25_index")


class BM25SearchIndex:
    """In-memory BM25 keyword search index for fast lexical retrieval."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None

    def build_index(self, chunks: List[Dict[str, Any]]) -> None:
        """Build or refresh BM25 index from a list of chunks (each containing 'chunk_id', 'content', 'metadata')."""
        self.corpus_chunks = chunks
        self.tokenized_corpus = [self._tokenize(c.get("content", "")) for c in chunks]
        
        if self.tokenized_corpus and any(len(doc) > 0 for doc in self.tokenized_corpus):
            self.bm25 = BM25Okapi(self.tokenized_corpus, k1=self.k1, b=self.b)
            logger.info(f"Built BM25 index with {len(self.corpus_chunks)} documents.")
        else:
            self.bm25 = None
            logger.info("BM25 index initialized with empty corpus.")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_doc_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Query the BM25 index and return ranked chunks with relevance scores."""
        if not self.bm25 or not self.corpus_chunks:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        doc_scores = self.bm25.get_scores(tokens)
        max_score = max(doc_scores) if len(doc_scores) > 0 and max(doc_scores) > 0 else 1.0

        results = []
        for idx, score in enumerate(doc_scores):
            if score <= 0.0:
                continue

            chunk = self.corpus_chunks[idx]
            
            # Apply document filter if requested
            if filter_doc_ids:
                doc_id = chunk.get("metadata", {}).get("document_id")
                if doc_id and doc_id not in filter_doc_ids:
                    continue

            normalized_score = float(score / max_score)
            results.append({
                "chunk_id": chunk.get("chunk_id"),
                "content": chunk.get("content"),
                "metadata": chunk.get("metadata", {}),
                "score": round(normalized_score, 4),
                "raw_bm25_score": round(float(score), 4),
                "retrieval_source": "bm25"
            })

        # Sort descending by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple, fast lowercase alphanumeric tokenizer."""
        return re.findall(r"\b\w+\b", text.lower())
