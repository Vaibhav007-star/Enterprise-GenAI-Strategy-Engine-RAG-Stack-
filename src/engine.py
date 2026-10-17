import os
from pathlib import Path
from typing import Optional

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
from .financial_analysis.financial_engine import FinancialAnalysisEngine
from .intelligence.executive_briefing import ExecutiveBriefingGenerator
from .intelligence.document_comparator import DocumentComparator
from .intelligence.compliance_risk import ComplianceRiskScanner
from .evaluation.evaluator import RAGEvaluator
from .utils.logger import get_logger

logger = get_logger("engine")


class StrategyEngine:
    """Unified Facade for Enterprise GenAI Strategy Engine."""

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

        # 4. Retrieval & Reranking
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

        # 5. LLM & Generation
        self.llm_client = LLMFactory.create_client(self.settings)
        self.generator = AnswerGenerator(llm_client=self.llm_client)

        # 6. Specialized Enterprise Intelligence
        self.financial_engine = FinancialAnalysisEngine()
        self.briefing_generator = ExecutiveBriefingGenerator(self.retriever, self.generator)
        self.comparator = DocumentComparator(self.retriever, self.generator)
        self.compliance_scanner = ComplianceRiskScanner(self.retriever, self.generator)
        self.evaluator = RAGEvaluator(self.retriever, self.generator)

        # Auto-ingest sample documents if collection is completely fresh
        self._bootstrap_sample_data_if_empty()
        logger.info("Enterprise GenAI Strategy Engine initialized successfully.")

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


_engine_instance: Optional[StrategyEngine] = None


def get_engine() -> StrategyEngine:
    """Retrieve global singleton StrategyEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = StrategyEngine()
    return _engine_instance
