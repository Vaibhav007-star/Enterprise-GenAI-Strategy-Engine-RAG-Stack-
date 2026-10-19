from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from ..chunking.models import TextChunk
from ..utils.logger import get_logger

logger = get_logger("access_control")


def get_chunk_doc_title(chunk: Any) -> str:
    if isinstance(chunk, dict):
        return chunk.get("metadata", {}).get("document_name", chunk.get("source_doc_title", "Document"))
    return getattr(chunk, "document_name", getattr(chunk, "source_doc_title", "Document"))


class SecurityClearance(str, Enum):
    PUBLIC_10K = "PUBLIC_10K"                      # Public SEC filings, annual reports
    RESTRICTED_STRATEGY = "RESTRICTED_STRATEGY"    # Internal strategic playbooks, benchmarking
    CONFIDENTIAL_DEALROOM = "CONFIDENTIAL_DEALROOM" # M&A clean rooms, unannounced transactions, P&L models
    AUDIT_GOVERNANCE = "AUDIT_GOVERNANCE"          # Regulatory audit logs and compliance notes


class UserRole(str, Enum):
    PUBLIC_ANALYST = "PUBLIC_ANALYST"
    STRATEGY_CONSULTANT = "STRATEGY_CONSULTANT"
    MA_PARTNER_CLEANROOM = "MA_PARTNER_CLEANROOM"
    COMPLIANCE_AUDITOR = "COMPLIANCE_AUDITOR"


# Permissions Mapping
ROLE_PERMISSIONS: Dict[UserRole, List[SecurityClearance]] = {
    UserRole.PUBLIC_ANALYST: [
        SecurityClearance.PUBLIC_10K
    ],
    UserRole.STRATEGY_CONSULTANT: [
        SecurityClearance.PUBLIC_10K,
        SecurityClearance.RESTRICTED_STRATEGY
    ],
    UserRole.MA_PARTNER_CLEANROOM: [
        SecurityClearance.PUBLIC_10K,
        SecurityClearance.RESTRICTED_STRATEGY,
        SecurityClearance.CONFIDENTIAL_DEALROOM
    ],
    UserRole.COMPLIANCE_AUDITOR: [
        SecurityClearance.PUBLIC_10K,
        SecurityClearance.RESTRICTED_STRATEGY,
        SecurityClearance.AUDIT_GOVERNANCE
    ]
}


class AccessAuditLog(BaseModel):
    user_role: UserRole
    total_chunks_inspected: int
    allowed_chunks_count: int
    redacted_chunks_count: int
    access_granted: bool
    policy_notes: str


class VirtualDataRoomRBAC:
    """BCG X Enterprise Security & M&A Clean Room Access Controller.
    Enforces document-level and chunk-level clearance policies across corporate repositories."""

    @classmethod
    def get_document_clearance(cls, doc_title: str) -> SecurityClearance:
        """Infer security clearance from document title and metadata."""
        title_lower = doc_title.lower()
        if any(k in title_lower for k in ["deal", "m&a", "acquisition", "clean_room", "private"]):
            return SecurityClearance.CONFIDENTIAL_DEALROOM
        elif any(k in title_lower for k in ["framework", "playbook", "strategy", "benchmark"]):
            return SecurityClearance.RESTRICTED_STRATEGY
        elif any(k in title_lower for k in ["audit", "compliance", "regulatory"]):
            return SecurityClearance.AUDIT_GOVERNANCE
        else:
            return SecurityClearance.PUBLIC_10K

    @classmethod
    def filter_chunks_by_role(
        cls,
        chunks: List[Any],
        user_role: UserRole = UserRole.STRATEGY_CONSULTANT
    ) -> Tuple[List[Any], AccessAuditLog]:
        """Filter retrieved chunks based on user's security clearance level."""
        allowed_clearances = ROLE_PERMISSIONS.get(user_role, [SecurityClearance.PUBLIC_10K])
        allowed_chunks: List[Any] = []
        redacted_count = 0

        for chunk in chunks:
            chunk_clearance = cls.get_document_clearance(get_chunk_doc_title(chunk))
            if chunk_clearance in allowed_clearances:
                allowed_chunks.append(chunk)
            else:
                redacted_count += 1


        policy_notes = f"Role '{user_role.value}' permitted access to {len(allowed_chunks)}/{len(chunks)} chunks."
        if redacted_count > 0:
            policy_notes += f" {redacted_count} chunks redacted due to Clean Room / Confidentiality boundary."

        audit_log = AccessAuditLog(
            user_role=user_role,
            total_chunks_inspected=len(chunks),
            allowed_chunks_count=len(allowed_chunks),
            redacted_chunks_count=redacted_count,
            access_granted=(len(allowed_chunks) > 0),
            policy_notes=policy_notes
        )

        return allowed_chunks, audit_log
