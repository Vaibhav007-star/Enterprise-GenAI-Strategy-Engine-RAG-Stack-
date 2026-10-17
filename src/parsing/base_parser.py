from abc import ABC, abstractmethod
from pathlib import Path
import hashlib
from typing import Union
from .models import ParsedDocument


class BaseParser(ABC):
    """Abstract base class for all enterprise document parsers."""

    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        """Parse file into standardized ParsedDocument representation."""
        pass

    @staticmethod
    def compute_sha256(file_path: Union[str, Path]) -> str:
        """Compute SHA256 checksum of document for deduplication."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
