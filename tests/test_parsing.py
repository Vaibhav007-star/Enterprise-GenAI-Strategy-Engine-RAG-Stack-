import pytest
from pathlib import Path
from src.parsing.parser_factory import ParserFactory
from src.parsing.text_parser import TextParser
from src.parsing.spreadsheet_parser import SpreadsheetParser


def test_parser_factory_resolution():
    assert ParserFactory.is_supported("test.pdf")
    assert ParserFactory.is_supported("report.docx")
    assert ParserFactory.is_supported("data.csv")
    assert ParserFactory.is_supported("sheet.xlsx")
    assert ParserFactory.is_supported("policy.md")
    assert ParserFactory.is_supported("notes.txt")
    assert not ParserFactory.is_supported("image.png")


def test_text_parser(tmp_path):
    md_file = tmp_path / "test_doc.md"
    md_file.write_text("# Section 1\nThis is paragraph one.\n\n## Section 2\nThis is paragraph two.", encoding="utf-8")

    parser = TextParser()
    parsed = parser.parse(md_file)

    assert parsed.file_name == "test_doc.md"
    assert parsed.file_type == "markdown"
    assert len(parsed.sections) == 2
    assert parsed.sections[0].section_title == "Section 1"
    assert "paragraph one" in parsed.sections[0].content


def test_csv_parser(tmp_path):
    csv_file = tmp_path / "financial.csv"
    csv_file.write_text("Department,Q1,Q2\nEngineering,100,120\nSales,80,95", encoding="utf-8")

    parser = SpreadsheetParser()
    parsed = parser.parse(csv_file)

    assert parsed.file_name == "financial.csv"
    assert parsed.file_type == "csv"
    assert len(parsed.tables) == 1
    table = parsed.tables[0]
    assert table.headers == ["Department", "Q1", "Q2"]
    assert len(table.rows) == 2
