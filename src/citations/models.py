from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Citation:
    """Explicit traceable citation linking answer text to specific source evidence."""
    citation_id: int
    document_name: str
    document_id: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    sheet_name: Optional[str] = None
    snippet: str = ""
    relevance_score: float = 0.0

    def format_badge(self) -> str:
        """User-friendly reference badge e.g. [1: Annual_Report_2024.pdf (p. 14)]."""
        loc = []
        if self.page_number is not None:
            loc.append(f"p. {self.page_number}")
        if self.sheet_name:
            loc.append(f"Sheet: {self.sheet_name}")
        if self.section_title:
            loc.append(f"Section: {self.section_title}")
        loc_str = f" ({', '.join(loc)})" if loc else ""
        return f"[{self.citation_id}: {self.document_name}{loc_str}]"


@dataclass
class GroundedResponse:
    """Structured response container adhering to enterprise grounding standards."""
    answer: str
    citations: List[Citation] = field(default_factory=list)
    has_sufficient_evidence: bool = True
    contradictions_noted: Optional[str] = None
    assumptions_or_calculations: Optional[str] = None
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[str] = None
