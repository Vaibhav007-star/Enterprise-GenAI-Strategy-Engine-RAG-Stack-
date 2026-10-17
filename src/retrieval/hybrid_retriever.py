import time
from typing import List, Dict, Any, Optional
from collections import defaultdict

from ..storage.vector_store import ChromaVectorStore
from ..storage.document_store import DocumentStore
from .bm25_index import BM25SearchIndex
from ..reranking.reranker import CrossEncoderReranker
from ..utils.logger import get_logger

logger = get_logger("hybrid_retriever")


class HybridRetriever:
    """Enterprise hybrid retrieval engine uniting Vector Search, BM25, RRF, and Parent Expansion."""

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        document_store: DocumentStore,
        bm25_index: Optional[BM25SearchIndex] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        rrf_k: int = 60
    ):
        self.vector_store = vector_store
        self.document_store = document_store
        self.bm25_index = bm25_index or BM25SearchIndex()
        self.reranker = reranker or CrossEncoderReranker()
        self.rrf_k = rrf_k
        self._ensure_bm25_synced()

    def _ensure_bm25_synced(self):
        """Populate BM25 index from active vector collection chunks."""
        try:
            # Query all items from collection
            results = self.vector_store.collection.get(
                include=["documents", "metadatas"]
            )
            chunks = []
            if results and results.get("ids"):
                for idx, cid in enumerate(results["ids"]):
                    chunks.append({
                        "chunk_id": cid,
                        "content": results["documents"][idx] if results.get("documents") else "",
                        "metadata": results["metadatas"][idx] if results.get("metadatas") else {}
                    })
            self.bm25_index.build_index(chunks)
        except Exception as e:
            logger.warning(f"Could not sync BM25 index on init: {e}")

    def refresh_bm25_index(self):
        """Public method to rebuild BM25 index after new document ingestion."""
        self._ensure_bm25_synced()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_hybrid: bool = True,
        use_reranker: bool = False,
        filter_document_ids: Optional[List[str]] = None,
        expand_parent_context: bool = True
    ) -> Dict[str, Any]:
        """Execute hybrid search pipeline and return ranked chunks along with diagnostic trace."""
        start_time = time.perf_counter()
        diagnostics = {
            "query": query,
            "vector_candidates_count": 0,
            "bm25_candidates_count": 0,
            "hybrid_fused_count": 0,
            "reranked": False,
            "execution_time_ms": 0.0,
            "vector_results": [],
            "bm25_results": [],
        }

        # 1. Vector Search
        # Filter dict for Chroma
        where_filter = None
        if filter_document_ids and len(filter_document_ids) == 1:
            where_filter = {"document_id": filter_document_ids[0]}
        elif filter_document_ids and len(filter_document_ids) > 1:
            where_filter = {"document_id": {"$in": filter_document_ids}}

        vector_results = self.vector_store.similarity_search(
            query=query,
            top_k=top_k * 2 if use_hybrid else top_k,
            filter_dict=where_filter
        )
        diagnostics["vector_candidates_count"] = len(vector_results)
        diagnostics["vector_results"] = [
            {"id": r["chunk_id"], "score": r["score"], "doc": r["metadata"].get("document_name")}
            for r in vector_results[:5]
        ]

        if not use_hybrid:
            final_chunks = vector_results[:top_k]
        else:
            # 2. BM25 Search
            bm25_results = self.bm25_index.search(
                query=query,
                top_k=top_k * 2,
                filter_doc_ids=filter_document_ids
            )
            diagnostics["bm25_candidates_count"] = len(bm25_results)
            diagnostics["bm25_results"] = [
                {"id": r["chunk_id"], "score": r["score"], "doc": r["metadata"].get("document_name")}
                for r in bm25_results[:5]
            ]

            # 3. Reciprocal Rank Fusion (RRF)
            final_chunks = self._reciprocal_rank_fusion(
                vector_results=vector_results,
                bm25_results=bm25_results,
                top_k=top_k * 2
            )
            diagnostics["hybrid_fused_count"] = len(final_chunks)

        # 4. Optional Reranking
        if use_reranker and self.reranker:
            self.reranker.enabled = True
            final_chunks = self.reranker.rerank(query, final_chunks, top_k=top_k)
            diagnostics["reranked"] = True
        else:
            final_chunks = final_chunks[:top_k]

        # 5. Parent-Child Context Expansion
        if expand_parent_context:
            for chunk in final_chunks:
                parent_id = chunk.get("metadata", {}).get("parent_id")
                if parent_id:
                    parent_data = self.document_store.get_parent_chunk(parent_id)
                    if parent_data and parent_data.get("content"):
                        chunk["child_content"] = chunk["content"]
                        chunk["content"] = parent_data["content"]
                        chunk["parent_expanded"] = True
                        chunk["parent_section"] = parent_data.get("section_title")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        diagnostics["execution_time_ms"] = round(elapsed_ms, 2)
        logger.info(f"Retrieved {len(final_chunks)} chunks for '{query[:30]}...' in {elapsed_ms:.1f}ms")

        return {
            "results": final_chunks,
            "diagnostics": diagnostics
        }

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Compute Reciprocal Rank Fusion scores across Vector and BM25 candidate lists."""
        rrf_scores = defaultdict(float)
        chunk_map: Dict[str, Dict[str, Any]] = {}

        # Vector rankings (1-indexed rank)
        for rank, item in enumerate(vector_results, start=1):
            cid = item["chunk_id"]
            rrf_scores[cid] += 1.0 / (self.rrf_k + rank)
            if cid not in chunk_map:
                chunk_map[cid] = dict(item)
                chunk_map[cid]["vector_rank"] = rank

        # BM25 rankings (1-indexed rank)
        for rank, item in enumerate(bm25_results, start=1):
            cid = item["chunk_id"]
            rrf_scores[cid] += 1.0 / (self.rrf_k + rank)
            if cid not in chunk_map:
                chunk_map[cid] = dict(item)
            chunk_map[cid]["bm25_rank"] = rank

        # Form unified list sorted by RRF score
        fused_list = []
        for cid, score in rrf_scores.items():
            entry = chunk_map[cid]
            entry["rrf_score"] = round(score, 6)
            entry["score"] = round(score, 6)
            entry["retrieval_source"] = "hybrid_rrf"
            fused_list.append(entry)

        fused_list.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_list[:top_k]
