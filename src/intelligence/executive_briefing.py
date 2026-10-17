from typing import List, Dict, Any, Optional
from ..retrieval.hybrid_retriever import HybridRetriever
from ..generation.generator import AnswerGenerator
from ..citations.models import GroundedResponse
from ..utils.logger import get_logger

logger = get_logger("executive_briefing")


class ExecutiveBriefingGenerator:
    """Produces structured C-level executive briefings from enterprise documents."""

    def __init__(self, retriever: HybridRetriever, generator: AnswerGenerator):
        self.retriever = retriever
        self.generator = generator

    def generate_briefing(
        self,
        topic_or_query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 8
    ) -> GroundedResponse:
        """Synthesize a complete strategic executive briefing."""
        logger.info(f"Generating Executive Briefing for topic: '{topic_or_query}'")

        # Retrieve comprehensive context
        retrieval_output = self.retriever.retrieve(
            query=topic_or_query,
            top_k=top_k,
            use_hybrid=True,
            filter_document_ids=document_ids,
            expand_parent_context=True
        )

        custom_prompt = (
            "Generate a formal, structured Executive Briefing with the following exact sections:\n"
            "1. EXECUTIVE OVERVIEW (High-level summary)\n"
            "2. KEY STRATEGIC FINDINGS (Numbered bullet points with [SOURCE X] citations)\n"
            "3. FINANCIAL & OPERATIONAL METRICS (Specific verified numbers)\n"
            "4. MAJOR RISKS & VULNERABILITIES (Identified risk factors)\n"
            "5. STRATEGIC OPPORTUNITIES (Actionable levers)\n"
            "6. RECOMMENDED NEXT STEPS (Near-term recommendations)\n"
            "Format cleanly with bold headers and markdown."
        )

        return self.generator.generate_answer(
            query=f"Generate Executive Briefing on: {topic_or_query}",
            retrieved_chunks=retrieval_output["results"],
            custom_instructions=custom_prompt
        )
