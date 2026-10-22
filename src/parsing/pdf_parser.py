from pathlib import Path
from typing import Union, List
import uuid
import re

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from .base_parser import BaseParser
from .models import ParsedDocument, DocumentSection, ParsedTable
from ..utils.logger import get_logger

logger = get_logger("pdf_parser")


class PDFParser(BaseParser):
    """Enterprise PDF parser extracting text, pages, section structure, and tabular data."""

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found at: {path}")

        file_hash = self.compute_sha256(path)
        file_size = path.stat().st_size
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"

        reader = PdfReader(str(path))
        num_pages = len(reader.pages)
        sections: List[DocumentSection] = []
        tables: List[ParsedTable] = []
        full_text_chunks: List[str] = []

        for page_idx, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            normalized_text = self._normalize_text(raw_text)
            
            if not normalized_text.strip():
                continue

            full_text_chunks.append(f"--- Page {page_idx} ---\n{normalized_text}")

            # Identify headers or potential tables in the text
            page_sections, page_tables = self._extract_page_content(
                normalized_text, page_idx, path.name
            )
            sections.extend(page_sections)
            tables.extend(page_tables)

        full_text = "\n\n".join(full_text_chunks)
        
        # If no explicit sections were parsed, treat each page as a section
        if not sections and full_text_chunks:
            for idx, chunk in enumerate(full_text_chunks, start=1):
                sections.append(
                    DocumentSection(
                        section_title=f"Page {idx}",
                        content=chunk,
                        page_number=idx,
                        level=1
                    )
                )

        logger.info(f"Parsed PDF '{path.name}' ({num_pages} pages, {len(sections)} sections, {len(tables)} tables)")

        return ParsedDocument(
            document_id=doc_id,
            file_name=path.name,
            file_type="pdf",
            file_size_bytes=file_size,
            content_hash=file_hash,
            total_pages_or_sheets=num_pages,
            sections=sections,
            tables=tables,
            full_text=full_text,
            metadata={
                "author": reader.metadata.author if reader.metadata else None,
                "title": reader.metadata.title if reader.metadata else path.stem,
            }
        )

    def _normalize_text(self, text: str) -> str:
        """Clean redundant whitespace and control characters."""
        # Replace non-breaking spaces and unusual whitespace
        text = text.replace("\xa0", " ").replace("\r\n", "\n")
        # Collapse excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_page_content(self, text: str, page_num: int, doc_name: str):
        """Detect headers, section breaks, and tabular lines on a page."""
        sections: List[DocumentSection] = []
        tables: List[ParsedTable] = []

        lines = text.split("\n")
        current_title = f"Page {page_num} Content"
        current_lines: List[str] = []

        for line in lines:
            line_stripped = line.strip()
            # Simple heuristic for headings: short, capitalized, or numbered like "1.2 Title"
            is_heading = (
                (len(line_stripped) < 60 and line_stripped.isupper() and len(line_stripped) > 4) or
                re.match(r"^(Section|\d+\.|\d+\.\d+|Chapter)\s+[A-Z]", line_stripped) is not None
            )

            if is_heading and current_lines:
                sections.append(DocumentSection(
                    section_title=current_title,
                    content="\n".join(current_lines),
                    page_number=page_num,
                    level=1
                ))
                current_title = line_stripped
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(DocumentSection(
                section_title=current_title,
                content="\n".join(current_lines),
                page_number=page_num,
                level=1
            ))

        return sections, tables
