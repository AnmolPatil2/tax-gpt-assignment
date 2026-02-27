import os
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock


def get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data"


class TestCSVLoader:
    def test_csv_file_exists(self):
        csv_path = get_data_dir() / "tax_data.csv"
        assert csv_path.exists(), f"CSV file not found at {csv_path}"

    def test_csv_readable(self):
        csv_path = get_data_dir() / "tax_data.csv"
        df = pd.read_csv(csv_path)
        assert len(df) > 0, "CSV is empty"
        assert len(df) == 5000, f"Expected 5000 rows, got {len(df)}"

    def test_csv_columns(self):
        csv_path = get_data_dir() / "tax_data.csv"
        df = pd.read_csv(csv_path)
        expected_cols = [
            "Taxpayer Type", "Tax Year", "Transaction Date",
            "Income Source", "Deduction Type", "State",
            "Income", "Deductions", "Taxable Income",
            "Tax Rate", "Tax Owed",
        ]
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_csv_data_types(self):
        csv_path = get_data_dir() / "tax_data.csv"
        df = pd.read_csv(csv_path)
        assert df["Income"].dtype in ("float64", "float32")
        assert df["Tax Year"].dtype in ("int64", "int32")

    def test_csv_value_ranges(self):
        csv_path = get_data_dir() / "tax_data.csv"
        df = pd.read_csv(csv_path)
        assert df["Income"].min() > 0
        assert 0 <= df["Tax Rate"].min()
        assert df["Tax Rate"].max() <= 1.0

    def test_row_to_text(self):
        from app.ingestion.csv_loader import _row_to_text

        row = pd.Series({
            "Taxpayer Type": "Individual",
            "State": "CA",
            "Tax Year": 2023,
            "Income Source": "Salary",
            "Deduction Type": "Mortgage Interest",
            "Income": 100000.0,
            "Deductions": 20000.0,
            "Taxable Income": 80000.0,
            "Tax Rate": 0.22,
            "Tax Owed": 17600.0,
        })
        text = _row_to_text(row)
        assert "Individual" in text
        assert "CA" in text
        assert "100,000.00" in text

    def test_row_to_graph_dict(self):
        from app.ingestion.csv_loader import _row_to_graph_dict

        row = pd.Series({
            "Taxpayer Type": "Corporation",
            "State": "TX",
            "Tax Year": 2022,
            "Income Source": "Business Income",
            "Deduction Type": "Business Expenses",
            "Income": 500000.0,
            "Deductions": 100000.0,
            "Taxable Income": 400000.0,
            "Tax Rate": 0.21,
            "Tax Owed": 84000.0,
            "Transaction Date": "2022-06-15",
        })
        d = _row_to_graph_dict(row)
        assert d["taxpayer_type"] == "Corporation"
        assert d["tax_year"] == 2022
        assert isinstance(d["income"], float)


class TestPDFLoader:
    def test_pdf_files_exist(self):
        data_dir = get_data_dir()
        pdfs = list(data_dir.glob("*.pdf"))
        assert len(pdfs) >= 2, f"Expected at least 2 PDFs, found {len(pdfs)}"

    def test_pdf_readable(self):
        import pdfplumber

        pdf_path = get_data_dir() / "i1040gi.pdf"
        with pdfplumber.open(pdf_path) as pdf:
            assert len(pdf.pages) > 0
            text = pdf.pages[0].extract_text()
            assert text is not None
            assert len(text) > 0

    def test_chunk_text(self):
        from app.ingestion.pdf_loader import _chunk_text

        text = "word " * 2000  # ~2000 tokens
        chunks = _chunk_text(text, chunk_size=500, chunk_overlap=100)
        assert len(chunks) > 1
        assert all(len(c) > 0 for c in chunks)


class TestPPTLoader:
    def test_ppt_file_exists(self):
        ppt_path = get_data_dir() / "MIC_3e_Ch11.ppt"
        assert ppt_path.exists(), f"PPT file not found at {ppt_path}"

    def test_ole_extraction(self):
        from app.ingestion.ppt_loader import _extract_text_ole

        ppt_path = get_data_dir() / "MIC_3e_Ch11.ppt"
        slides = _extract_text_ole(ppt_path)
        assert len(slides) > 0, "Could not extract any text from PPT"
        total_text = " ".join(text for _, text in slides)
        assert len(total_text) > 50, "Extracted text is too short"
