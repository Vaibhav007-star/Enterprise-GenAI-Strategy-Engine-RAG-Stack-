import re
from pathlib import Path
from typing import Tuple, Optional
from ..utils.logger import get_logger

logger = get_logger("security_sanitizer")

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".csv", ".xlsx", ".xls", ".txt", ".md"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB max upload limit


class SecuritySanitizer:
    """Security and input sanitization guards for enterprise document pipelines."""

    @staticmethod
    def validate_file_upload(file_name: str, file_size_bytes: int) -> Tuple[bool, Optional[str]]:
        """Validate file name, extension, and upload size."""
        # Check path traversal
        if ".." in file_name or "/" in file_name or "\\" in file_name:
            return False, "Dangerous filename containing directory traversal sequences."

        ext = Path(file_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File extension '{ext}' is not authorized. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

        if file_size_bytes > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            return False, f"File size exceeds maximum allowable limit of {max_mb} MB."

        return True, None

    @staticmethod
    def sanitize_user_query(query: str) -> str:
        """Sanitize query against null bytes and control characters."""
        if not query:
            return ""
        # Remove null bytes and non-printable control characters (except newline and tab)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", query)
        return cleaned.strip()

    @staticmethod
    def detect_prompt_injection(text: str) -> bool:
        """Detect known prompt injection patterns attempting to hijack system instructions."""
        lower = text.lower()
        injection_patterns = [
            r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
            r"override\s+system\s+prompt",
            r"system:\s*you\s+are\s+now",
            r"disregard\s+the\s+above",
            r"output\s+the\s+entire\s+prompt",
            r"reveal\s+your\s+instructions"
        ]
        for pattern in injection_patterns:
            if re.search(pattern, lower):
                logger.warning(f"Suspected prompt injection pattern flagged: '{pattern}'")
                return True
        return False
