from typing import List, Dict, Any, Optional
from ..retrieval.hybrid_retriever import HybridRetriever
from ..generation.generator import AnswerGenerator
from ..citations.models import GroundedResponse
from ..utils.logger import get_logger

logger = get_logger("compliance_risk")


class ComplianceRiskScanner:
    """Scans enterprise documents for regulatory requirements, compliance deadlines, and risk vulnerabilities."""

    def __init__(self, retriever: HybridRetriever, generator: AnswerGenerator):
        self.retriever = retriever
        self.generator = generator

    def audit_risk_and_compliance(
        self,
        compliance_topic: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 6
    ) -> GroundedResponse:
        """Execute risk and regulatory compliance scan on indexed documentation."""
        logger.info(f"Scanning for compliance & risk on topic: '{compliance_topic}'")

        # Query using hybrid retrieval
        search_query = f"{compliance_topic} risk regulatory requirement policy compliance audit exception deadline"
        retrieval_output = self.retriever.retrieve(
            query=search_query,
            top_k=top_k,
            use_hybrid=True,
            filter_document_ids=document_ids,
            expand_parent_context=True
        )

        custom_prompt = (
            "You are an Enterprise Risk and Compliance Auditor.\n"
            "Analyze the provided document evidence for compliance requirements, deadlines, risk factors, and policy gaps.\n\n"
            "Structure your report as follows:\n"
            "1. EXECUTIVE AUDIT SUMMARY: Current compliance posture\n"
            "2. REGULATORY & POLICY MANDATES: Key requirements identified, with [SOURCE X] citations\n"
            "3. DEADLINES & OBLIGATIONS: Explicit dates, filing requirements, review periods\n"
            "4. POTENTIAL COMPLIANCE GAPS & RISKS: Note: Describe potential gaps as 'findings requiring verification', NOT definitive legal conclusions\n"
            "5. RECOMMENDED AUDIT ACTIONS: Recommended remediation steps\n"
        )

        return self.generator.generate_answer(
            query=f"Conduct Compliance and Risk Audit regarding: {compliance_topic}",
            retrieved_chunks=retrieval_output["results"],
            custom_instructions=custom_prompt
        )
