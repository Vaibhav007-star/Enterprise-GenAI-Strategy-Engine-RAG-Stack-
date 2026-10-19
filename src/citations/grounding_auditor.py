import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from ..chunking.models import TextChunk


def get_chunk_text(chunk: Any) -> str:
    if isinstance(chunk, dict):
        return chunk.get("content", chunk.get("text", ""))
    return getattr(chunk, "content", getattr(chunk, "text", ""))


def get_chunk_doc_name(chunk: Any) -> str:
    if isinstance(chunk, dict):
        return chunk.get("metadata", {}).get("document_name", chunk.get("source_doc_title", "Document"))
    return getattr(chunk, "document_name", getattr(chunk, "source_doc_title", "Document"))


class GroundedSpan(BaseModel):
    sentence: str
    status: str  # "GROUNDED_GREEN", "INFERRED_AMBER", "UNVERIFIED_RED"
    confidence: float
    matched_source: Optional[str] = None
    supporting_text_snippet: Optional[str] = None


class DocumentGroundingReport(BaseModel):
    overall_grounding_score: float  # 0.0 - 1.0
    spans: List[GroundedSpan]
    green_count: int
    amber_count: int
    red_count: int
    summary: str


class GroundingAuditor:
    """BCG X Fact-Checking & Sentence-Level Grounding Engine.
    Deconstructs generated answers into discrete assertions and matches against retrieved context chunks."""

    @classmethod
    def audit_spans(cls, text: str, context_chunks: List[Any]) -> DocumentGroundingReport:
        if not text:
            return DocumentGroundingReport(
                overall_grounding_score=1.0, spans=[], green_count=0, amber_count=0, red_count=0, summary="No text to audit."
            )

        # Split text into sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]
        if not sentences:
            sentences = [text.strip()]

        spans: List[GroundedSpan] = []
        green_cnt = 0
        amber_cnt = 0
        red_cnt = 0

        for sent in sentences:
            # Skip pure markdown headers or bullet indicators
            clean_s = re.sub(r"^[#\*\-\d\.\s]+", "", sent).strip()
            if len(clean_s) < 10:
                continue

            words = set(re.findall(r"\b[A-Za-z0-9]{4,}\b", clean_s.lower()))
            best_overlap = 0
            best_chunk: Optional[Any] = None
            best_snippet = None

            for chunk in context_chunks:
                ctext = get_chunk_text(chunk)
                chunk_words = set(re.findall(r"\b[A-Za-z0-9]{4,}\b", ctext.lower()))
                common = words.intersection(chunk_words)
                if len(common) > best_overlap:
                    best_overlap = len(common)
                    best_chunk = chunk
                    best_snippet = ctext[:180] + "..."

            ratio = best_overlap / max(len(words), 1)

            if ratio >= 0.45 or any(c.isdigit() for c in clean_s) and best_overlap >= 3:
                status = "GROUNDED_GREEN"
                conf = round(min(0.99, 0.70 + (ratio * 0.3)), 2)
                green_cnt += 1
            elif ratio >= 0.25:
                status = "INFERRED_AMBER"
                conf = 0.70
                amber_cnt += 1
            else:
                status = "UNVERIFIED_RED"
                conf = 0.35
                red_cnt += 1

            spans.append(GroundedSpan(
                sentence=clean_s,
                status=status,
                confidence=conf,
                matched_source=get_chunk_doc_name(best_chunk) if best_chunk else None,
                supporting_text_snippet=best_snippet
            ))


        total = len(spans)
        overall_score = round((green_cnt + (amber_cnt * 0.6)) / max(total, 1), 2)
        summary = f"{green_cnt} sentences verified directly ({round(green_cnt/max(total,1)*100)}%), {amber_cnt} inferred, {red_cnt} ungrounded."

        return DocumentGroundingReport(
            overall_grounding_score=overall_score,
            spans=spans,
            green_count=green_cnt,
            amber_count=amber_cnt,
            red_count=red_cnt,
            summary=summary
        )
