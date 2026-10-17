from pathlib import Path
from typing import Union, List
import uuid
import re

from .base_parser import BaseParser
from .models import ParsedDocument, DocumentSection
from ..utils.logger import get_logger

logger = get_logger("text_parser")


class TextParser(BaseParser):
    """Parser for raw text (.txt) and Markdown (.md) documents."""

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {path}")

        file_hash = self.compute_sha256(path)
        file_size = path.stat().st_size
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        sections: List[DocumentSection] = []
        lines = raw_text.splitlines()
        
        current_title = path.stem.replace("_", " ").title()
        current_lines: List[str] = []
        current_level = 1

        for line in lines:
            header_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if header_match:
                if current_lines:
                    sections.append(DocumentSection(
                        section_title=current_title,
                        content="\n".join(current_lines).strip(),
                        level=current_level
                    ))
                    current_lines = []
                current_level = len(header_match.group(1))
                current_title = header_match.group(2).strip()
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(DocumentSection(
                section_title=current_title,
                content="\n".join(current_lines).strip(),
                level=current_level
            ))

        logger.info(f"Parsed Text/MD '{path.name}' ({len(sections)} sections)")

        return ParsedDocument(
            document_id=doc_id,
            file_name=path.name,
            file_type="markdown" if path.suffix.lower() == ".md" else "text",
            file_size_bytes=file_size,
            content_hash=file_hash,
            total_pages_or_sheets=len(sections) or 1,
            sections=sections,
            tables=[],
            full_text=raw_text,
            metadata={"format": path.suffix.lower()}
        )
