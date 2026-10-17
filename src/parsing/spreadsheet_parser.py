from pathlib import Path
from typing import Union, List
import uuid
import pandas as pd

from .base_parser import BaseParser
from .models import ParsedDocument, DocumentSection, ParsedTable
from ..utils.logger import get_logger

logger = get_logger("spreadsheet_parser")


class SpreadsheetParser(BaseParser):
    """Parser for Excel (.xlsx, .xls) and CSV spreadsheets with financial intelligence extraction."""

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Spreadsheet file not found: {path}")

        file_hash = self.compute_sha256(path)
        file_size = path.stat().st_size
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        suffix = path.suffix.lower()

        sections: List[DocumentSection] = []
        tables: List[ParsedTable] = []
        full_text_chunks: List[str] = []

        if suffix == ".csv":
            df = pd.read_csv(str(path))
            table_obj = self._dataframe_to_table(df, sheet_name="Data", table_id=f"{doc_id}_tbl_1", doc_name=path.name)
            tables.append(table_obj)
            sec_text = self._generate_sheet_summary(df, "Data")
            sections.append(DocumentSection(
                section_title="Data Sheet",
                content=sec_text,
                level=1,
                tables=[table_obj]
            ))
            full_text_chunks.append(sec_text)
            total_sheets = 1
        else:
            # Excel workbook
            excel_file = pd.ExcelFile(str(path))
            sheet_names = excel_file.sheet_names
            total_sheets = len(sheet_names)

            for idx, sheet_name in enumerate(sheet_names, start=1):
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    table_obj = self._dataframe_to_table(
                        df, sheet_name=sheet_name, table_id=f"{doc_id}_tbl_{idx}", doc_name=path.name
                    )
                    tables.append(table_obj)
                    sec_text = self._generate_sheet_summary(df, sheet_name)
                    sections.append(DocumentSection(
                        section_title=f"Sheet: {sheet_name}",
                        content=sec_text,
                        level=1,
                        tables=[table_obj]
                    ))
                    full_text_chunks.append(sec_text)
                except Exception as e:
                    logger.warning(f"Failed to parse sheet '{sheet_name}' in '{path.name}': {e}")

        full_text = "\n\n".join(full_text_chunks)
        logger.info(f"Parsed Spreadsheet '{path.name}' ({total_sheets} sheets, {len(tables)} structured tables)")

        return ParsedDocument(
            document_id=doc_id,
            file_name=path.name,
            file_type="csv" if suffix == ".csv" else "xlsx",
            file_size_bytes=file_size,
            content_hash=file_hash,
            total_pages_or_sheets=total_sheets,
            sections=sections,
            tables=tables,
            full_text=full_text,
            metadata={"sheet_count": total_sheets}
        )

    def _dataframe_to_table(self, df: pd.DataFrame, sheet_name: str, table_id: str, doc_name: str) -> ParsedTable:
        """Convert a Pandas DataFrame into a structured ParsedTable."""
        # Clean null values and format column names
        df_clean = df.fillna("")
        headers = [str(col) for col in df_clean.columns]
        rows = df_clean.values.tolist()

        return ParsedTable(
            table_id=table_id,
            sheet_or_page=sheet_name,
            headers=headers,
            rows=rows,
            dataframe_json=df_clean.to_json(orient="split"),
            title_or_caption=f"{doc_name} - {sheet_name}",
            metadata={"num_rows": len(df_clean), "num_cols": len(df_clean.columns)}
        )

    def _generate_sheet_summary(self, df: pd.DataFrame, sheet_name: str) -> str:
        """Generate structured text summary suitable for vector & keyword indexing."""
        headers = list(df.columns)
        num_rows, num_cols = df.shape
        summary_lines = [
            f"### Financial / Operational Sheet: {sheet_name}",
            f"Dimensions: {num_rows} rows x {num_cols} columns",
            f"Columns: {', '.join([str(c) for c in headers])}",
            "",
            "#### Table Data Preview:",
        ]
        
        # Convert first 50 rows to markdown for retrieval context
        preview_df = df.head(50).fillna("")
        markdown_table = preview_df.to_markdown(index=False)
        summary_lines.append(markdown_table)

        # Include numerical column statistics if available
        num_cols_list = df.select_dtypes(include=["number"]).columns.tolist()
        if num_cols_list:
            summary_lines.append("\n#### Numerical Summary:")
            for col in num_cols_list[:10]:
                col_series = df[col].dropna()
                if not col_series.empty:
                    summary_lines.append(
                        f"- **{col}**: Total={col_series.sum():,.2f}, Mean={col_series.mean():,.2f}, "
                        f"Min={col_series.min():,.2f}, Max={col_series.max():,.2f}"
                    )

        return "\n".join(summary_lines)
