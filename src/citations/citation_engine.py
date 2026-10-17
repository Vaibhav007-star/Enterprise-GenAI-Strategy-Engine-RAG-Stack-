from typing import List, Dict, Any
from .models import Citation, GroundedResponse
from ..utils.logger import get_logger

logger = get_logger("citation_engine")


class CitationEngine:
    """Builds and validates citations from retrieved document chunks."""

    @staticmethod
    def build_citations(retrieved_chunks: List[Dict[str, Any]]) -> List[Citation]:
        """Convert retrieved chunks into numbered citations."""
        citations = []
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            meta = chunk.get("metadata", {})
            content = chunk.get("content", "").strip()
            # Truncate snippet for citation display
            snippet = content[:280] + "..." if len(content) > 280 else content

            citations.append(Citation(
                citation_id=idx,
                document_name=meta.get("document_name", "Unknown Document"),
                document_id=meta.get("document_id", ""),
                page_number=meta.get("page_number"),
                section_title=meta.get("section_title"),
                sheet_name=meta.get("sheet_name"),
                snippet=snippet,
                relevance_score=chunk.get("score", 0.0)
            ))
        return citations

    @staticmethod
    def format_context_for_prompt(citations: List[Citation], full_chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved context with explicit numbered source markers for the LLM."""
        formatted_blocks = []
        for cite, chunk in zip(citations, full_chunks):
            header = f"[SOURCE {cite.citation_id}] Document: {cite.document_name}"
            locs = []
            if cite.page_number:
                locs.append(f"Page: {cite.page_number}")
            if cite.sheet_name:
                locs.append(f"Sheet: {cite.sheet_name}")
            if cite.section_title:
                locs.append(f"Section: {cite.section_title}")
            if locs:
                header += f" | {', '.join(locs)}"

            formatted_blocks.append(f"{header}\n{chunk.get('content', '').strip()}\n[/SOURCE {cite.citation_id}]")

        return "\n\n".join(formatted_blocks)
