from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import numpy as np

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except Exception:
    chromadb = None

from ..chunking.models import TextChunk
from ..embeddings.base_embedding import BaseEmbeddingProvider
from ..utils.logger import get_logger

logger = get_logger("vector_store")


class ChromaVectorStore:
    """Enterprise ChromaDB vector store wrapper with seamless in-memory fallback for serverless deployments."""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        embedding_provider: BaseEmbeddingProvider
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider

        self.client = None
        self.collection = None
        self._in_memory_chunks: Dict[str, Dict[str, Any]] = {}

        # 1. Attempt persistent ChromaDB initialization
        if chromadb is not None:
            try:
                Path(persist_dir).mkdir(parents=True, exist_ok=True)
                self.client = chromadb.PersistentClient(
                    path=str(persist_dir),
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
                self.collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": "Enterprise Document Chunks & Tables"}
                )
                logger.info(f"Initialized ChromaDB at '{persist_dir}' with collection '{collection_name}'. Current count: {self.collection.count()}")
            except Exception as e:
                logger.warning(f"ChromaDB initialization failed: {e}. Falling back to lightweight vector store.")
                self.client = None
                self.collection = None

        # 2. If ChromaDB unavailable or empty, bootstrap in-memory fallback from persisted vector_chunks.json
        if self.collection is None or self.collection.count() == 0:
            self._load_fallback_chunks()

    def _load_fallback_chunks(self):
        """Loads pre-indexed vector chunks from JSON fallback locations."""
        candidates = [
            Path(self.persist_dir) / "vector_chunks.json",
            Path("data/metadata/vector_chunks.json"),
            Path(__file__).resolve().parent.parent.parent / "data" / "metadata" / "vector_chunks.json"
        ]
        for p in candidates:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    for item in raw:
                        cid = item.get("chunk_id")
                        if cid:
                            self._in_memory_chunks[cid] = item
                    logger.info(f"Loaded {len(self._in_memory_chunks)} fallback vector chunks from '{p}'.")
                    break
                except Exception as e:
                    logger.warning(f"Error loading fallback chunks from {p}: {e}")

    def add_chunks(self, chunks: List[TextChunk]) -> int:
        """Embed and upsert text chunks into ChromaDB or in-memory vector store."""
        if not chunks:
            return 0

        # Only index child chunks, tables, and standalone chunks (parents are retrieved via metadata)
        indexable_chunks = [c for c in chunks if c.chunk_type in ("child", "standalone", "table")]
        if not indexable_chunks:
            return 0

        ids = [c.chunk_id for c in indexable_chunks]
        documents = [c.content for c in indexable_chunks]
        
        # Prepare metadata (flat dict without nested objects for ChromaDB compatibility)
        metadatas = []
        for c in indexable_chunks:
            meta: Dict[str, Any] = {
                "document_id": str(c.document_id),
                "document_name": str(c.document_name),
                "chunk_type": str(c.chunk_type),
                "chunk_index": int(c.chunk_index),
                "token_count": int(c.token_count_approx),
            }
            if c.parent_id:
                meta["parent_id"] = str(c.parent_id)
            if c.section_title:
                meta["section_title"] = str(c.section_title)
            if c.page_number is not None:
                meta["page_number"] = int(c.page_number)
            if c.sheet_name:
                meta["sheet_name"] = str(c.sheet_name)
            
            # Additional metadata
            for k, v in c.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[f"meta_{k}"] = v
            metadatas.append(meta)

        # Batch embed documents
        logger.info(f"Generating embeddings for {len(documents)} chunks...")
        embeddings = self.embedding_provider.embed_documents(documents)

        # Store in ChromaDB if active
        if self.collection is not None:
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                end_idx = i + batch_size
                self.collection.upsert(
                    ids=ids[i:end_idx],
                    documents=documents[i:end_idx],
                    embeddings=embeddings[i:end_idx],
                    metadatas=metadatas[i:end_idx]
                )

        # Mirror in in-memory fallback
        for i, cid in enumerate(ids):
            self._in_memory_chunks[cid] = {
                "chunk_id": cid,
                "content": documents[i],
                "metadata": metadatas[i],
                "embedding": embeddings[i]
            }

        logger.info(f"Successfully indexed {len(ids)} chunks.")
        return len(ids)

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic vector similarity search with optional metadata filtering."""
        query_embedding = np.array(self.embedding_provider.embed_query(query), dtype=np.float32)

        # If ChromaDB is active and has chunks, use it
        if self.collection is not None and self.collection.count() > 0:
            where_clause = filter_dict if (filter_dict and len(filter_dict) > 0) else None
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding.tolist()],
                    n_results=top_k,
                    where=where_clause,
                    include=["documents", "metadatas", "distances"]
                )

                formatted_results = []
                if results and results.get("ids") and len(results["ids"]) > 0:
                    ids = results["ids"][0]
                    docs = results["documents"][0] if results.get("documents") else []
                    metas = results["metadatas"][0] if results.get("metadatas") else []
                    distances = results["distances"][0] if results.get("distances") else []

                    for i in range(len(ids)):
                        dist = distances[i] if i < len(distances) else 1.0
                        score = max(0.0, 1.0 - (dist / 2.0))
                        formatted_results.append({
                            "chunk_id": ids[i],
                            "content": docs[i] if i < len(docs) else "",
                            "metadata": metas[i] if i < len(metas) else {},
                            "score": score,
                            "retrieval_source": "vector"
                        })
                return formatted_results
            except Exception as e:
                logger.warning(f"ChromaDB query encountered an issue: {e}. Falling back to in-memory cosine search.")

        # In-Memory Cosine Similarity Search Fallback
        if not self._in_memory_chunks:
            return []

        q_norm = np.linalg.norm(query_embedding)
        if q_norm > 0:
            query_embedding = query_embedding / q_norm

        scored_chunks = []
        for cid, item in self._in_memory_chunks.items():
            meta = item.get("metadata", {})
            if filter_dict:
                match = True
                for fk, fv in filter_dict.items():
                    if meta.get(fk) != fv:
                        match = False
                        break
                if not match:
                    continue

            emb = item.get("embedding")
            if emb is not None:
                vec = np.array(emb, dtype=np.float32)
                v_norm = np.linalg.norm(vec)
                if v_norm > 0:
                    vec = vec / v_norm
                sim = float(np.dot(query_embedding, vec))
                score = max(0.0, min(1.0, (sim + 1.0) / 2.0))
            else:
                score = 0.5

            scored_chunks.append({
                "chunk_id": cid,
                "content": item.get("content", ""),
                "metadata": meta,
                "score": round(score, 4),
                "retrieval_source": "vector"
            })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]

    def delete_document(self, document_id: str) -> int:
        """Remove all chunks associated with a specific document ID."""
        deleted = 0
        if self.collection is not None:
            try:
                existing = self.collection.get(where={"document_id": document_id}, include=["metadatas"])
                ids_to_del = existing.get("ids", [])
                if ids_to_del:
                    self.collection.delete(ids=ids_to_del)
                    deleted = len(ids_to_del)
            except Exception as e:
                logger.error(f"Error deleting chunks from ChromaDB for doc '{document_id}': {e}")

        # Remove from in-memory fallback
        to_del = [cid for cid, it in self._in_memory_chunks.items() if it.get("metadata", {}).get("document_id") == document_id]
        for cid in to_del:
            self._in_memory_chunks.pop(cid, None)
            deleted = max(deleted, len(to_del))

        return deleted

    def get_collection_stats(self) -> Dict[str, Any]:
        """Return diagnostic metrics for Chroma or in-memory vector collection."""
        count = self.collection.count() if self.collection is not None else len(self._in_memory_chunks)
        return {
            "collection_name": self.collection_name,
            "total_chunks": count,
            "persist_directory": self.persist_dir,
            "engine_backend": "chromadb" if self.collection is not None else "in_memory_vector_store"
        }
