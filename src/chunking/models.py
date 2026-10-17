from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class TextChunk:
    """Represents a text chunk with complete metadata and parent-child linkage."""
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    chunk_type: str  # 'child', 'parent', 'standalone', 'table'
    parent_id: Optional[str] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    chunk_index: int = 0
    token_count_approx: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
