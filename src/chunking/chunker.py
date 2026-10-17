import re
import uuid
from typing import List, Optional
from ..parsing.models import ParsedDocument, DocumentSection, ParsedTable
from .models import TextChunk
from ..utils.logger import get_logger

logger = get_logger("chunker")


class ChunkingEngine:
    """Enterprise chunking engine supporting recursive, structural, and parent-child chunking."""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        parent_chunk_size: int = 2000,
        parent_chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parent_chunk_size = parent_chunk_size
        self.parent_chunk_overlap = parent_chunk_overlap

    def chunk_document(
        self,
        doc: ParsedDocument,
        strategy: str = "parent_child"
    ) -> List[TextChunk]:
        """Split a parsed document into chunks using selected strategy.
        
        Strategies:
        - 'parent_child': Generates broader parent context and precise child search chunks
        - 'structure_aware': Preserves headings and sections
        - 'recursive': Standard recursive character sliding window
        """
        all_chunks: List[TextChunk] = []

        # 1. Process structured tables first (retaining high fidelity)
        for tbl in doc.tables:
            table_chunk = self._create_table_chunk(doc, tbl)
            if table_chunk:
                all_chunks.append(table_chunk)

        # 2. Process text sections
        if strategy == "parent_child":
            text_chunks = self._chunk_parent_child(doc)
        elif strategy == "structure_aware":
            text_chunks = self._chunk_structure_aware(doc)
        else:
            text_chunks = self._chunk_recursive(doc)

        all_chunks.extend(text_chunks)
        logger.info(f"Generated {len(all_chunks)} chunks for document '{doc.file_name}' using strategy '{strategy}'")
        return all_chunks

    def _split_text_recursively(self, text: str, size: int, overlap: int) -> List[str]:
        """Split text recursively using paragraph, sentence, and word boundaries."""
        if not text:
            return []
        
        if len(text) <= size:
            return [text.strip()]

        separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]
        return self._recursive_split(text, separators, size, overlap)

    def _recursive_split(self, text: str, separators: List[str], size: int, overlap: int) -> List[str]:
        final_chunks: List[str] = []
        separator = separators[-1]
        
        for sep in separators:
            if sep == "" or sep in text:
                separator = sep
                break

        splits = text.split(separator) if separator != "" else list(text)
        current_chunk: List[str] = []
        current_len = 0

        for piece in splits:
            piece_len = len(piece) + len(separator)
            if current_len + piece_len > size and current_chunk:
                joined = separator.join(current_chunk).strip()
                if joined:
                    final_chunks.append(joined)
                
                # Apply overlap by keeping tail elements
                overlap_tokens: List[str] = []
                accum_len = 0
                for item in reversed(current_chunk):
                    if accum_len + len(item) + len(separator) <= overlap:
                        overlap_tokens.insert(0, item)
                        accum_len += len(item) + len(separator)
                    else:
                        break
                current_chunk = overlap_tokens
                current_len = accum_len

            current_chunk.append(piece)
            current_len += piece_len

        if current_chunk:
            joined = separator.join(current_chunk).strip()
            if joined:
                final_chunks.append(joined)

        return final_chunks

    def _chunk_parent_child(self, doc: ParsedDocument) -> List[TextChunk]:
        """Parent-child chunking: broad parent chunks with precise child chunks."""
        chunks: List[TextChunk] = []
        chunk_idx = 0

        for section in doc.sections:
            sec_content = section.content.strip()
            if not sec_content:
                continue

            # Generate parent chunks for this section
            parent_texts = self._split_text_recursively(
                sec_content, self.parent_chunk_size, self.parent_chunk_overlap
            )

            for p_num, p_text in enumerate(parent_texts):
                parent_id = f"parent_{doc.document_id}_{chunk_idx}"
                parent_chunk = TextChunk(
                    chunk_id=parent_id,
                    document_id=doc.document_id,
                    document_name=doc.file_name,
                    content=p_text,
                    chunk_type="parent",
                    section_title=section.section_title,
                    page_number=section.page_number,
                    chunk_index=chunk_idx,
                    token_count_approx=len(p_text) // 4,
                    metadata={"level": section.level}
                )
                chunks.append(parent_chunk)
                chunk_idx += 1

                # Generate smaller child chunks linked to this parent
                child_texts = self._split_text_recursively(
                    p_text, self.chunk_size, self.chunk_overlap
                )

                for c_num, c_text in enumerate(child_texts):
                    child_id = f"child_{parent_id}_{c_num}"
                    child_chunk = TextChunk(
                        chunk_id=child_id,
                        document_id=doc.document_id,
                        document_name=doc.file_name,
                        content=c_text,
                        chunk_type="child",
                        parent_id=parent_id,
                        section_title=section.section_title,
                        page_number=section.page_number,
                        chunk_index=chunk_idx,
                        token_count_approx=len(c_text) // 4,
                        metadata={"parent_id": parent_id, "level": section.level}
                    )
                    chunks.append(child_chunk)
                    chunk_idx += 1

        return chunks

    def _chunk_structure_aware(self, doc: ParsedDocument) -> List[TextChunk]:
        """Chunks respect section boundaries, only splitting if a section exceeds chunk_size."""
        chunks: List[TextChunk] = []
        chunk_idx = 0

        for section in doc.sections:
            sec_text = section.content.strip()
            if not sec_text:
                continue

            splits = self._split_text_recursively(sec_text, self.chunk_size, self.chunk_overlap)
            for split in splits:
                chunk = TextChunk(
                    chunk_id=f"chunk_{doc.document_id}_{chunk_idx}",
                    document_id=doc.document_id,
                    document_name=doc.file_name,
                    content=f"### {section.section_title}\n{split}",
                    chunk_type="standalone",
                    section_title=section.section_title,
                    page_number=section.page_number,
                    chunk_index=chunk_idx,
                    token_count_approx=len(split) // 4,
                    metadata={"level": section.level}
                )
                chunks.append(chunk)
                chunk_idx += 1

        return chunks

    def _chunk_recursive(self, doc: ParsedDocument) -> List[TextChunk]:
        """Standard recursive chunking over full document text."""
        chunks: List[TextChunk] = []
        text = doc.full_text.strip()
        if not text:
            return chunks

        splits = self._split_text_recursively(text, self.chunk_size, self.chunk_overlap)
        for idx, split in enumerate(splits):
            chunk = TextChunk(
                chunk_id=f"chunk_{doc.document_id}_{idx}",
                document_id=doc.document_id,
                document_name=doc.file_name,
                content=split,
                chunk_type="standalone",
                chunk_index=idx,
                token_count_approx=len(split) // 4
            )
            chunks.append(chunk)

        return chunks

    def _create_table_chunk(self, doc: ParsedDocument, table: ParsedTable) -> Optional[TextChunk]:
        """Format a structured table into an indexed chunk."""
        table_md = table.to_markdown()
        if not table_md:
            return None

        content = f"### Structured Data Table: {table.title_or_caption or table.sheet_or_page}\n"
        content += f"Source: {doc.file_name} | Location: {table.sheet_or_page}\n\n"
        content += table_md

        return TextChunk(
            chunk_id=f"table_{table.table_id}",
            document_id=doc.document_id,
            document_name=doc.file_name,
            content=content,
            chunk_type="table",
            sheet_name=table.sheet_or_page,
            chunk_index=0,
            token_count_approx=len(content) // 4,
            metadata={
                "is_table": True,
                "table_id": table.table_id,
                "sheet": table.sheet_or_page,
                "rows_count": len(table.rows),
                "cols_count": len(table.headers)
            }
        )
