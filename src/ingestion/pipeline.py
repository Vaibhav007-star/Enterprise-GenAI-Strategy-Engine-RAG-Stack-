import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..parsing.parser_factory import ParserFactory
from ..chunking.chunker import ChunkingEngine
from ..storage.vector_store import ChromaVectorStore
from ..storage.document_store import DocumentStore
from ..utils.logger import get_logger

logger = get_logger("ingestion_pipeline")


@dataclass
class IngestionResult:
    """Result of an ingestion operation for a single file."""
    file_name: str
    success: bool
    document_id: Optional[str] = None
    chunks_indexed: int = 0
    tables_indexed: int = 0
    warning: Optional[str] = None
    error: Optional[str] = None
    is_duplicate: bool = False


class IngestionPipeline:
    """Unified ingestion pipeline for enterprise documents."""

    def __init__(
        self,
        upload_dir: Path,
        vector_store: ChromaVectorStore,
        document_store: DocumentStore,
        chunking_engine: Optional[ChunkingEngine] = None
    ):
        self.upload_dir = Path(upload_dir)
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.vector_store = vector_store
        self.document_store = document_store
        self.chunking_engine = chunking_engine or ChunkingEngine()

    def ingest_file(
        self,
        source_path: Path,
        chunking_strategy: str = "parent_child",
        force_reindex: bool = False
    ) -> IngestionResult:
        """Ingest a single document through validation, parsing, chunking, and indexing."""
        file_path = Path(source_path)
        if not file_path.exists():
            return IngestionResult(file_name=file_path.name, success=False, error="File does not exist")

        # 1. Validation
        if not ParserFactory.is_supported(file_path):
            return IngestionResult(
                file_name=file_path.name,
                success=False,
                error=f"Unsupported file format '{file_path.suffix}'"
            )

        try:
            # 2. Check for duplicate hash
            parser = ParserFactory.get_parser(file_path)
            content_hash = parser.compute_sha256(file_path)
            existing_doc = self.document_store.is_duplicate_hash(content_hash)
            
            if existing_doc and not force_reindex:
                logger.info(f"Duplicate document detected for '{file_path.name}' (hash: {content_hash[:8]}...)")
                return IngestionResult(
                    file_name=file_path.name,
                    success=True,
                    document_id=existing_doc["document_id"],
                    chunks_indexed=0,
                    is_duplicate=True,
                    warning="Document already indexed with identical content hash."
                )

            # Copy to persistent upload directory if not already there
            dest_path = self.upload_dir / file_path.name
            if file_path.resolve() != dest_path.resolve():
                shutil.copy2(file_path, dest_path)
                file_path = dest_path

            # 3. Parse Document
            parsed_doc = parser.parse(file_path)

            if not parsed_doc.full_text.strip() and not parsed_doc.tables:
                return IngestionResult(
                    file_name=file_path.name,
                    success=False,
                    error="Document contains no extractable text or tables."
                )

            # 4. Chunk Document
            chunks = self.chunking_engine.chunk_document(parsed_doc, strategy=chunking_strategy)

            # 5. Index into ChromaDB
            indexed_count = self.vector_store.add_chunks(chunks)

            # 6. Register Document and Parent Chunks in Document Store
            self.document_store.register_document(parsed_doc)
            self.document_store.register_parent_chunks(chunks)

            logger.info(f"Successfully ingested '{file_path.name}': {indexed_count} chunks indexed.")
            return IngestionResult(
                file_name=file_path.name,
                success=True,
                document_id=parsed_doc.document_id,
                chunks_indexed=indexed_count,
                tables_indexed=len(parsed_doc.tables)
            )

        except Exception as e:
            logger.error(f"Failed to ingest '{file_path.name}': {e}", exc_info=True)
            return IngestionResult(
                file_name=file_path.name,
                success=False,
                error=str(e)
            )

    def ingest_multiple(
        self,
        file_paths: List[Path],
        chunking_strategy: str = "parent_child",
        force_reindex: bool = False
    ) -> List[IngestionResult]:
        """Ingest a batch of documents."""
        results = []
        for fp in file_paths:
            res = self.ingest_file(fp, chunking_strategy=chunking_strategy, force_reindex=force_reindex)
            results.append(res)
        return results

    def delete_document(self, document_id: str) -> bool:
        """Completely purge a document from vector store and metadata registry."""
        # 1. Delete from vector store
        self.vector_store.delete_document(document_id)
        # 2. Delete from document store
        return self.document_store.delete_document(document_id)
