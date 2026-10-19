import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config.settings import AppSettings, get_settings
from .embeddings.embedding_service import EmbeddingFactory
from .storage.vector_store import ChromaVectorStore
from .storage.document_store import DocumentStore
from .chunking.chunker import ChunkingEngine
from .ingestion.pipeline import IngestionPipeline
from .retrieval.bm25_index import BM25SearchIndex
from .reranking.reranker import CrossEncoderReranker
from .retrieval.hybrid_retriever import HybridRetriever
from .generation.llm_client import LLMFactory
from .generation.generator import AnswerGenerator
from .generation.agentic_critic import AgenticCriticAuditor, CriticAuditResult
from .citations.grounding_auditor import GroundingAuditor, DocumentGroundingReport
from .financial_analysis.financial_engine import FinancialAnalysisEngine
from .financial_analysis.tco_calculator import EnterpriseTCOEngine, TCOInputParameters, TCOSimulationResult
from .financial_analysis.scenario_simulator import ScenarioStressSimulator, SensitivityGridResult
from .intelligence.executive_briefing import ExecutiveBriefingGenerator
from .intelligence.document_comparator import DocumentComparator
from .intelligence.compliance_risk import ComplianceRiskScanner
from .intelligence.graph_rag import EnterpriseKnowledgeGraph
from .intelligence.deck_generator import ExecutiveDeckGenerator
from .security.access_control import VirtualDataRoomRBAC, UserRole, AccessAuditLog
from .retrieval.semantic_cache import SemanticQueryCache
from .utils.telemetry import TelemetryTracker, LatencyBreakdown
from .evaluation.evaluator import RAGEvaluator
from .utils.logger import get_logger

logger = get_logger("engine")


class StrategyEngine:
    """Unified Facade for Enterprise GenAI Strategy Engine — BCG X Edition."""

    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or get_settings()
        self.settings.ensure_directories()

        # 1. Embeddings
        self.embedding_provider = EmbeddingFactory.get_provider(
            provider_type=self.settings.embedding_provider,
            model_name=self.settings.embedding_model_name,
            device=self.settings.embedding_device
        )

        # 2. Storage
        self.vector_store = ChromaVectorStore(
            persist_dir=self.settings.chroma_persist_directory,
            collection_name=self.settings.chroma_collection_name,
            embedding_provider=self.embedding_provider
        )
        self.document_store = DocumentStore(metadata_dir=self.settings.metadata_dir)

        # 3. Ingestion & Chunking
        self.chunking_engine = ChunkingEngine(
            chunk_size=self.settings.default_chunk_size,
            chunk_overlap=self.settings.default_chunk_overlap,
            parent_chunk_size=self.settings.parent_chunk_size,
            parent_chunk_overlap=self.settings.parent_chunk_overlap
        )
        self.ingestion_pipeline = IngestionPipeline(
            upload_dir=self.settings.upload_dir,
            vector_store=self.vector_store,
            document_store=self.document_store,
            chunking_engine=self.chunking_engine
        )

        # 4. Retrieval, Reranking & Semantic Cache
        self.bm25_index = BM25SearchIndex(k1=self.settings.bm25_k1, b=self.settings.bm25_b)
        self.reranker = CrossEncoderReranker(
            model_name=self.settings.reranker_model_name,
            enabled=self.settings.reranker_enabled
        )
        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            document_store=self.document_store,
            bm25_index=self.bm25_index,
            reranker=self.reranker,
            rrf_k=self.settings.rrf_k
        )
        self.semantic_cache = SemanticQueryCache(similarity_threshold=0.92)

        # 5. LLM, Generation & Verification
        self.llm_client = LLMFactory.create_client(self.settings)
        self.generator = AnswerGenerator(llm_client=self.llm_client)
        self.critic_auditor = AgenticCriticAuditor(llm_client=self.llm_client)
        self.grounding_auditor = GroundingAuditor()

        # 6. Specialized Consulting & Financial Intelligence
        self.financial_engine = FinancialAnalysisEngine()
        self.tco_engine = EnterpriseTCOEngine()
        self.scenario_simulator = ScenarioStressSimulator()
        self.briefing_generator = ExecutiveBriefingGenerator(self.retriever, self.generator)
        self.comparator = DocumentComparator(self.retriever, self.generator)
        self.compliance_scanner = ComplianceRiskScanner(self.retriever, self.generator)
        self.knowledge_graph = EnterpriseKnowledgeGraph()
        self.deck_generator = ExecutiveDeckGenerator()
        self.vdr_rbac = VirtualDataRoomRBAC()
        self.evaluator = RAGEvaluator(self.retriever, self.generator)

        # Auto-ingest sample documents if collection is completely fresh
        self._bootstrap_sample_data_if_empty()
        logger.info("Enterprise GenAI Strategy Engine (BCG X Edition) initialized successfully.")

    def _bootstrap_sample_data_if_empty(self):
        """Pre-populate sample business documents on first launch if empty."""
        try:
            doc_count = len(self.document_store.get_all_documents())
            if doc_count == 0 and self.settings.sample_data_dir.exists():
                sample_files = list(self.settings.sample_data_dir.glob("*.*"))
                if sample_files:
                    logger.info(f"Bootstrapping {len(sample_files)} sample enterprise documents...")
                    self.ingestion_pipeline.ingest_multiple(sample_files, chunking_strategy="parent_child")
                    self.retriever.refresh_bm25_index()
        except Exception as e:
            logger.warning(f"Could not bootstrap sample documents: {e}")

    def query_enterprise(
        self,
        query: str,
        persona: str = "bcg_partner",
        top_k: int = 6,
        use_hybrid: bool = True,
        use_reranker: bool = False,
        document_ids: Optional[List[str]] = None,
        user_role: UserRole = UserRole.STRATEGY_CONSULTANT,
        bypass_cache: bool = False
    ) -> Dict[str, Any]:
        """BCG X End-to-End Orchestrated Query:
        1. Telemetry waterfall profiling
        2. Semantic vector caching
        3. Virtual Data Room RBAC filtration
        4. Hybrid RRF retrieval & reranking
        5. GraphRAG context injection
        6. Strategic synthesis
        7. Agentic Critic audit
        8. Sentence-level grounding report"""
        telemetry = TelemetryTracker(query=query)

        # Step A: Semantic Cache Check
        telemetry.start_span("embedding")
        query_emb = self.embedding_provider.embed_query(query)
        telemetry.end_span("embedding")

        if not bypass_cache:
            cache_hit = self.semantic_cache.lookup(query, query_emb)
            if cache_hit:
                entry, sim = cache_hit
                telemetry.is_cache_hit = True
                telemetry_data = telemetry.finalize()
                return {
                    "answer": entry.response_text,
                    "citations": entry.citations,
                    "critic_audit": entry.critic_audit,
                    "grounding_report": None,
                    "rbac_audit": None,
                    "is_cache_hit": True,
                    "cache_similarity": round(sim, 3),
                    "telemetry": telemetry_data.model_dump(),
                    "persona": persona
                }

        # Step B: Retrieval
        telemetry.start_span("retrieval")
        if use_hybrid:
            telemetry.start_span("dense_vector")
            retrieval_output = self.retriever.retrieve(
                query=query,
                top_k=top_k,
                use_hybrid=True,
                use_reranker=use_reranker,
                filter_document_ids=document_ids,
                expand_parent_context=True
            )
            chunks = retrieval_output.get("results", [])
            telemetry.end_span("dense_vector")
        else:
            chunks = self.retriever.vector_store.similarity_search(
                query=query,
                top_k=top_k
            )
        telemetry.end_span("retrieval")

        # Step C: RBAC Access Control Filtration
        allowed_chunks, rbac_audit = self.vdr_rbac.filter_chunks_by_role(chunks, user_role=user_role)

        # Step D: GraphRAG Context Augmentation
        graph_context = self.knowledge_graph.query_subgraph_for_context(query)

        # Step E: Answer Generation
        telemetry.start_span("llm_generation")
        if persona == "bcg_partner":
            persona_directive = (
                "Adopt the persona of a senior Boston Consulting Group (BCG) Strategy Partner. "
                "Structure the response using the Pyramidal Principle:\n"
                "1. EXECUTIVE STRATEGY RECOMMENDATION (Top-down direct answer)\n"
                "2. QUANTITATIVE PILLARS & FINANCIAL EVIDENCE (Audited SEC Form 10-K numbers with [SOURCE X] citations)\n"
                "3. VALUE CREATION LEVERS (Identified commercial upside)\n"
                "4. DOWNSIDE RISK & MITIGATION FRAMEWORK (Regulatory, supply chain, geopolitical)\n"
                "Ensure the analysis is Mutually Exclusive and Collectively Exhaustive (MECE)."
            )
        elif persona == "private_equity":
            persona_directive = (
                "Adopt the persona of a Private Equity / M&A Due Diligence Principal:\n"
                "1. INVESTMENT THESIS & CORE VERDICT\n"
                "2. RECURRING REVENUE QUALITY & SEGMENT MARGINS (Audited 10-K data with [SOURCE X])\n"
                "3. CAPEX INTENSITY & FREE CASH FLOW CONVERSION\n"
                "4. DOWNSIDE VULNERABILITIES & REGULATORY EXPOSURES\n"
            )
        else:
            persona_directive = "Focus strictly on technical accuracy, token economy, and specific page/item references."

        generated_resp = self.generator.generate_answer(
            query=query,
            retrieved_chunks=allowed_chunks,
            custom_instructions=persona_directive
        )
        telemetry.end_span("llm_generation")

        # Record tokens
        chunk_chars = sum(len(c.get("content", c.get("text", ""))) if isinstance(c, dict) else len(getattr(c, "content", getattr(c, "text", ""))) for c in allowed_chunks)
        prompt_est = (len(query) + chunk_chars) // 4
        comp_est = len(generated_resp.answer) // 4
        telemetry.record_tokens(prompt_est, comp_est)

        # Step F: Agentic Critic Verification
        telemetry.start_span("agentic_critic")
        critic_audit = self.critic_auditor.audit(
            query=query,
            draft_response=generated_resp.answer,
            context_chunks=allowed_chunks
        )
        telemetry.end_span("agentic_critic")

        # Step G: Fine-Grained Sentence Grounding
        grounding_report = self.grounding_auditor.audit_spans(

            text=generated_resp.answer,
            context_chunks=allowed_chunks
        )

        telemetry_data = telemetry.finalize()

        citations_data = [
            {
                "id": c.citation_id,
                "document_name": c.document_name,
                "document_id": c.document_id,
                "page_number": c.page_number,
                "section_title": c.section_title,
                "sheet_name": c.sheet_name,
                "snippet": c.snippet,
                "relevance_score": c.relevance_score
            }
            for c in generated_resp.citations
        ]
        critic_data = critic_audit.model_dump()

        # Step H: Store in Semantic Cache
        self.semantic_cache.store(
            query=query,
            embedding=query_emb,
            response_text=generated_resp.answer,
            citations=citations_data,
            critic_audit=critic_data
        )

        return {
            "answer": generated_resp.answer,
            "hardened_answer": critic_audit.hardened_response,
            "citations": citations_data,
            "critic_audit": critic_data,
            "grounding_report": grounding_report.model_dump(),
            "rbac_audit": rbac_audit.model_dump(),
            "is_cache_hit": False,
            "cache_similarity": 0.0,
            "telemetry": telemetry_data.model_dump(),
            "graph_context": graph_context,
            "persona": persona
        }


_engine_instance: Optional[StrategyEngine] = None


def get_engine() -> StrategyEngine:
    """Retrieve global singleton StrategyEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = StrategyEngine()
    return _engine_instance
