import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..parsing.models import ParsedDocument
from ..chunking.models import TextChunk
from ..utils.logger import get_logger

logger = get_logger("document_store")


class DocumentStore:
    """Manages document registry, parent chunk mappings, and query history persistence."""

    def __init__(self, metadata_dir: Path):
        self.metadata_dir = Path(metadata_dir)
        try:
            self.metadata_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        
        self.docs_file = self.metadata_dir / "documents.json"
        self.parents_file = self.metadata_dir / "parent_chunks.json"
        self.history_file = self.metadata_dir / "query_history.json"
        
        self.documents: Dict[str, Dict[str, Any]] = self._load_json(self.docs_file)
        self.parent_chunks: Dict[str, Dict[str, Any]] = self._load_json(self.parents_file)
        self.query_history: List[Dict[str, Any]] = self._load_json(self.history_file, default=[])

    def register_document(self, doc: ParsedDocument) -> None:
        """Register parsed document metadata."""
        self.documents[doc.document_id] = {
            "document_id": doc.document_id,
            "file_name": doc.file_name,
            "file_type": doc.file_type,
            "file_size_bytes": doc.file_size_bytes,
            "content_hash": doc.content_hash,
            "total_pages_or_sheets": doc.total_pages_or_sheets,
            "sections_count": len(doc.sections),
            "tables_count": len(doc.tables),
            "ingested_at": doc.ingested_at,
            "metadata": doc.metadata
        }
        self._save_json(self.docs_file, self.documents)
        logger.info(f"Registered document metadata: {doc.file_name} ({doc.document_id})")

    def register_parent_chunks(self, chunks: List[TextChunk]) -> None:
        """Store parent chunks for broader contextual expansion."""
        count = 0
        for c in chunks:
            if c.chunk_type == "parent":
                self.parent_chunks[c.chunk_id] = {
                    "parent_id": c.chunk_id,
                    "document_id": c.document_id,
                    "document_name": c.document_name,
                    "content": c.content,
                    "section_title": c.section_title,
                    "page_number": c.page_number,
                    "metadata": c.metadata
                }
                count += 1
        if count > 0:
            self._save_json(self.parents_file, self.parent_chunks)
            logger.info(f"Persisted {count} parent chunks.")

    def get_parent_chunk(self, parent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full parent text for a given parent_id."""
        return self.parent_chunks.get(parent_id)

    def is_duplicate_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Check if a document with identical SHA-256 hash was already ingested."""
        for doc in self.documents.values():
            if doc.get("content_hash") == content_hash:
                return doc
        return None

    def delete_document(self, document_id: str) -> bool:
        """Delete document from registry and purge its parent chunks."""
        if document_id in self.documents:
            del self.documents[document_id]
            self._save_json(self.docs_file, self.documents)
            
            # Remove related parent chunks
            parents_to_remove = [
                pid for pid, pdata in self.parent_chunks.items()
                if pdata.get("document_id") == document_id
            ]
            for pid in parents_to_remove:
                del self.parent_chunks[pid]
            if parents_to_remove:
                self._save_json(self.parents_file, self.parent_chunks)
                
            logger.info(f"Purged document '{document_id}' and {len(parents_to_remove)} parents.")
            return True
        return False

    def log_query(self, query_record: Dict[str, Any]) -> None:
        """Log a question, answer, citations, and latency metrics."""
        self.query_history.insert(0, query_record)
        # Retain last 200 records
        if len(self.query_history) > 200:
            self.query_history = self.query_history[:200]
        self._save_json(self.history_file, self.query_history)

    def get_query_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent query records."""
        return self.query_history[:limit]

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Return list of all registered documents."""
        return list(self.documents.values())

    def _load_json(self, path: Path, default: Any = None) -> Any:
        if default is None:
            default = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read {path}: {e}")
        return default

    def _save_json(self, path: Path, data: Any) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save {path}: {e}")
