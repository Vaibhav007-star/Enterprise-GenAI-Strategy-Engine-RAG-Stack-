from pathlib import Path
from typing import Union, Dict, Type
from .base_parser import BaseParser
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .spreadsheet_parser import SpreadsheetParser
from .text_parser import TextParser


class ParserFactory:
    """Factory to retrieve appropriate document parser based on file extension."""

    _parsers: Dict[str, Type[BaseParser]] = {
        ".pdf": PDFParser,
        ".docx": DocxParser,
        ".csv": SpreadsheetParser,
        ".xlsx": SpreadsheetParser,
        ".xls": SpreadsheetParser,
        ".txt": TextParser,
        ".md": TextParser,
    }

    @classmethod
    def get_parser(cls, file_path: Union[str, Path]) -> BaseParser:
        """Resolve and instantiate parser based on file extension."""
        path = Path(file_path)
        ext = path.suffix.lower()
        parser_cls = cls._parsers.get(ext)
        if not parser_cls:
            supported = ", ".join(cls._parsers.keys())
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: {supported}")
        return parser_cls()

    @classmethod
    def is_supported(cls, file_path: Union[str, Path]) -> bool:
        """Check if file format is supported."""
        return Path(file_path).suffix.lower() in cls._parsers
