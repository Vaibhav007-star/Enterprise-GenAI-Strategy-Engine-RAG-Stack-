import pytest
from src.chunking.chunker import ChunkingEngine
from src.parsing.models import ParsedDocument, DocumentSection


def test_chunking_engine_strategies():
    doc = ParsedDocument(
        document_id="doc_test_123",
        file_name="policy.txt",
        file_type="text",
        file_size_bytes=1000,
        content_hash="abc123hash",
        total_pages_or_sheets=1,
        sections=[
            DocumentSection(
                section_title="Security Controls",
                content="This is the security controls text. " * 30,
                level=1
            )
        ],
        full_text="This is the security controls text. " * 30
    )

    chunker = ChunkingEngine(chunk_size=200, chunk_overlap=40, parent_chunk_size=500, parent_chunk_overlap=50)

    # 1. Parent-Child Chunking
    chunks_pc = chunker.chunk_document(doc, strategy="parent_child")
    assert len(chunks_pc) > 1
    parent_chunks = [c for c in chunks_pc if c.chunk_type == "parent"]
    child_chunks = [c for c in chunks_pc if c.chunk_type == "child"]
    assert len(parent_chunks) > 0
    assert len(child_chunks) > 0
    # Every child has a parent_id
    assert all(c.parent_id is not None for c in child_chunks)

    # 2. Structure-Aware Chunking
    chunks_sa = chunker.chunk_document(doc, strategy="structure_aware")
    assert len(chunks_sa) > 0
    assert all("Security Controls" in c.content for c in chunks_sa)
