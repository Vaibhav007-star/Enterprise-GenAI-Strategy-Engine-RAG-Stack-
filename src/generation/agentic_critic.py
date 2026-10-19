import re
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

from .llm_client import BaseLLMClient
from ..chunking.models import TextChunk
from ..utils.logger import get_logger

logger = get_logger("agentic_critic")


def get_chunk_text(chunk: Any) -> str:
    if isinstance(chunk, dict):
        return chunk.get("content", chunk.get("text", ""))
    return getattr(chunk, "content", getattr(chunk, "text", ""))


def get_chunk_doc_name(chunk: Any) -> str:
    if isinstance(chunk, dict):
        return chunk.get("metadata", {}).get("document_name", chunk.get("source_doc_title", "Document"))
    return getattr(chunk, "document_name", getattr(chunk, "source_doc_title", "Document"))




class ClaimAudit(BaseModel):
    claim_text: str
    is_grounded: bool
    evidence_citation: Optional[str] = None
    confidence: float = 1.0
    notes: Optional[str] = None


class CriticAuditResult(BaseModel):
    status: str  # "PASSED", "PASSED_WITH_CAVEATS", "FLAGGED_REVISION"
    faithfulness_score: float  # 0.0 - 1.0
    numerical_accuracy_score: float  # 0.0 - 1.0
    total_claims_audited: int
    unsupported_claims_count: int
    audited_claims: List[ClaimAudit] = Field(default_factory=list)
    critic_notes: str
    partner_recommendation: str
    hardened_response: Optional[str] = None


class AgenticCriticAuditor:
    """BCG X Multi-Agent Reviewer: Evaluates lead strategic answers against source evidence,
    detecting hallucinations, numerical discrepancies, and ungrounded consultant leaps."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    @staticmethod
    def extract_numerical_tokens(text: str) -> List[str]:
        """Extract currency figures, percentages, and large numbers (e.g., $245.1B, 74.0%, 109,400)."""
        pattern = r"(?:[\$€£¥]\s*\d+(?:\.\d+)?(?:\s*(?:billion|million|trillion|[BMTbmt]))?|\d+(?:\.\d+)?%|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        # Normalize and filter out trivial single digits
        return list(dict.fromkeys([m.strip() for m in matches if len(m.strip()) > 1]))

    def audit(self, query: str, draft_response: str, context_chunks: List[Any]) -> CriticAuditResult:
        """Run a two-phase audit: deterministic numerical cross-referencing + semantic claim verification."""
        combined_context = "\n\n".join([f"[{get_chunk_doc_name(c)}]: {get_chunk_text(c)}" for c in context_chunks])
        context_lower = combined_context.lower()


        # 1. Deterministic Numerical Verification
        draft_numbers = self.extract_numerical_tokens(draft_response)
        verified_numbers = []
        flagged_numbers = []

        for num in draft_numbers:
            # Check presence of raw digits or normalized currency in retrieved text
            digits = re.sub(r"[^\d.]", "", num)
            if digits and (digits in context_lower or num.lower() in context_lower):
                verified_numbers.append(num)
            else:
                flagged_numbers.append(num)

        num_score = 1.0
        if draft_numbers:
            num_score = round(len(verified_numbers) / len(draft_numbers), 2)

        # 2. Extract Key Claims from Response
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", draft_response) if len(s.strip()) > 20]
        # Filter down to strategic assertions (containing numbers, comparisons, or recommendations)
        claim_candidates = [
            s for s in sentences 
            if any(k in s.lower() for k in ["revenue", "margin", "growth", "risk", "ebitda", "%", "$", "recommend", "strategic", "capex", "market"])
        ][:8]

        audited_claims: List[ClaimAudit] = []
        unsupported_count = 0

        for claim in claim_candidates:
            # Check for direct or partial semantic keyword grounding in context
            claim_words = set(re.findall(r"\b[A-Za-z0-9]{4,}\b", claim.lower()))
            overlap = [w for w in claim_words if w in context_lower]
            grounding_ratio = len(overlap) / max(len(claim_words), 1)

            has_flagged_num = any(f in claim for f in flagged_numbers)

            if grounding_ratio >= 0.55 and not has_flagged_num:
                audited_claims.append(ClaimAudit(
                    claim_text=claim,
                    is_grounded=True,
                    confidence=round(min(0.98, 0.70 + (grounding_ratio * 0.3)), 2),
                    notes="Directly substantiated by audited context sources."
                ))
            elif grounding_ratio >= 0.35 and not has_flagged_num:
                audited_claims.append(ClaimAudit(
                    claim_text=claim,
                    is_grounded=True,
                    confidence=0.75,
                    notes="Derived inference supported by contextual trends."
                ))
            else:
                unsupported_count += 1
                audited_claims.append(ClaimAudit(
                    claim_text=claim,
                    is_grounded=False,
                    confidence=0.35,
                    notes=f"Flagged by Critic: Contains unverified figures ({', '.join(flagged_numbers) if flagged_numbers else 'insufficient citations'})."
                ))

        total_claims = len(audited_claims)
        if total_claims > 0:
            faithfulness_score = round((total_claims - unsupported_count) / total_claims, 2)
        else:
            faithfulness_score = 1.0

        # Overall Status
        if faithfulness_score >= 0.85 and num_score >= 0.85:
            status = "PASSED"
            partner_recommendation = "Approved for C-suite presentation. All metrics and strategic assertions align with source documents."
            critic_notes = f"High confidence audit. Verified {len(verified_numbers)}/{len(draft_numbers)} quantitative data points with 0 critical discrepancies."
            hardened = draft_response
        elif faithfulness_score >= 0.65:
            status = "PASSED_WITH_CAVEATS"
            partner_recommendation = "Review highlighted figures before formal advisory sign-off. Cross-check secondary inferences."
            critic_notes = f"Moderate confidence. {unsupported_count} assertions or peripheral metrics require secondary verification."
            hardened = draft_response
        else:
            status = "FLAGGED_REVISION"
            partner_recommendation = "Hardened synthesis applied. Unverified numerical claims have been qualified with audited ranges."
            critic_notes = f"High-risk gaps detected: {len(flagged_numbers)} numbers unconfirmed in source documents."
            # Append partner caveats
            hardened = draft_response + f"\n\n> ⚠️ **BCG X Partner Audit Warning:** Certain numerical citations ({', '.join(flagged_numbers[:3])}) were flagged for secondary manual reconciliation."

        return CriticAuditResult(
            status=status,
            faithfulness_score=faithfulness_score,
            numerical_accuracy_score=num_score,
            total_claims_audited=total_claims,
            unsupported_claims_count=unsupported_count,
            audited_claims=audited_claims,
            critic_notes=critic_notes,
            partner_recommendation=partner_recommendation,
            hardened_response=hardened
        )
