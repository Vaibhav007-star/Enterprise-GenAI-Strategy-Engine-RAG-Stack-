from typing import List, Dict, Any, Optional
from ..retrieval.hybrid_retriever import HybridRetriever
from ..generation.generator import AnswerGenerator
from ..citations.models import GroundedResponse
from ..utils.logger import get_logger

logger = get_logger("document_comparator")


class DocumentComparator:
    """Compares policies, annual reports, financial statements, or operational reports."""

    def __init__(self, retriever: HybridRetriever, generator: AnswerGenerator):
        self.retriever = retriever
        self.generator = generator

    def compare_documents(
        self,
        doc_id_1: str,
        doc_name_1: str,
        doc_id_2: str,
        doc_name_2: str,
        focus_aspect: str = "Key policies, performance metrics, and compliance requirements"
    ) -> GroundedResponse:
        """Perform comparative analysis between two documents across a specific focus area."""
        logger.info(f"Comparing '{doc_name_1}' vs '{doc_name_2}' on focus: '{focus_aspect}'")

        # Retrieve relevant passages from doc 1
        res_1 = self.retriever.retrieve(
            query=focus_aspect,
            top_k=4,
            use_hybrid=True,
            filter_document_ids=[doc_id_1],
            expand_parent_context=True
        )

        # Retrieve relevant passages from doc 2
        res_2 = self.retriever.retrieve(
            query=focus_aspect,
            top_k=4,
            use_hybrid=True,
            filter_document_ids=[doc_id_2],
            expand_parent_context=True
        )

        combined_chunks = res_1["results"] + res_2["results"]

        custom_prompt = (
            f"You are conducting a strict comparative analysis between two documents:\n"
            f"Document A: {doc_name_1}\n"
            f"Document B: {doc_name_2}\n"
            f"Focus Area: {focus_aspect}\n\n"
            "Structure your comparative report as follows:\n"
            "1. COMPARATIVE OVERVIEW: High-level comparison summary\n"
            "2. COMMONALITIES & ALIGNED AREAS: Areas where both documents agree\n"
            "3. KEY DIFFERENCES & DIVERGENCES: Concrete variances, opposing metrics, or policy updates\n"
            "4. CONFLICTING OR INCONSISTENT CLAIMS: Any contradictions found between the documents\n"
            "5. COMPARATIVE SUMMARY TABLE: Markdown table contrasting Document A vs Document B\n"
            "Cite every claim with [SOURCE X]."
        )

        return self.generator.generate_answer(
            query=f"Compare {doc_name_1} and {doc_name_2} regarding {focus_aspect}",
            retrieved_chunks=combined_chunks,
            custom_instructions=custom_prompt
        )
