from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import datetime


@dataclass
class ParsedTable:
    """Represents a structured table extracted from a document or spreadsheet."""
    table_id: str
    sheet_or_page: str
    headers: List[str]
    rows: List[List[Any]]
    dataframe_json: Optional[str] = None
    title_or_caption: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert table into readable Markdown representation."""
        if not self.headers and not self.rows:
            return ""
        
        headers_str = [str(h) for h in self.headers]
        lines = []
        if self.title_or_caption:
            lines.append(f"**Table: {self.title_or_caption}** ({self.sheet_or_page})")
        
        lines.append("| " + " | ".join(headers_str) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers_str)) + " |")
        for row in self.rows:
            row_str = [str(val) if val is not None else "" for val in row]
            # Ensure row length matches headers
            if len(row_str) < len(headers_str):
                row_str.extend([""] * (len(headers_str) - len(row_str)))
            elif len(row_str) > len(headers_str):
                row_str = row_str[:len(headers_str)]
            lines.append("| " + " | ".join(row_str) + " |")
        return "\n".join(lines)


@dataclass
class DocumentSection:
    """Represents a section within a parsed document."""
    section_title: str
    content: str
    page_number: Optional[int] = None
    level: int = 1
    tables: List[ParsedTable] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Standardized representation of an ingested document."""
    document_id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    content_hash: str
    total_pages_or_sheets: int
    sections: List[DocumentSection] = field(default_factory=list)
    tables: List[ParsedTable] = field(default_factory=list)
    full_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
