from pathlib import Path

import pytest

from app.services.extraction import ExtractionError, ScannedPdfError, extract_pages


def test_extracts_text_page_by_page(pdf_factory, tmp_path: Path) -> None:
    path = pdf_factory(
        tmp_path / "two-pages.pdf",
        ["Alpha content on the first page.", "Beta content on the second page."],
    )

    pages = extract_pages(path)

    assert [page.page_number for page in pages] == [1, 2]
    assert "Alpha content" in pages[0].text
    assert "Beta content" in pages[1].text


def test_scanned_pdf_without_text_is_rejected(pdf_factory, tmp_path: Path) -> None:
    path = pdf_factory(tmp_path / "blank.pdf", ["", ""])

    with pytest.raises(ScannedPdfError, match="Scanned PDFs are not supported"):
        extract_pages(path)


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ExtractionError, match="Stored file is missing"):
        extract_pages(tmp_path / "missing.pdf")
