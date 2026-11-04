"""Page-aware PDF text extraction.

Extraction returns one entry per page and never joins pages together.
Chunking and citations both depend on that boundary: a passage must be
attributable to exactly one page.
"""

from dataclasses import dataclass
from pathlib import Path

import pymupdf


class ExtractionError(Exception):
    """Raised when a PDF cannot provide usable text."""


class ScannedPdfError(ExtractionError):
    """Raised when a PDF contains pages but no extractable text."""


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


def extract_pages(path: Path) -> list[ExtractedPage]:
    """Return the text of every page in a PDF.

    Page numbers are 1-based because they are shown to users and stored
    in citations. A page with no text still appears, so reported page
    counts match the document.
    """
    if not path.is_file():
        raise ExtractionError(f"Stored file is missing: {path.name}")

    try:
        document = pymupdf.open(path)
    except Exception as exc:  # noqa: BLE001 - pymupdf raises several types
        raise ExtractionError("The file is not a readable PDF.") from exc

    try:
        if document.page_count == 0:
            raise ExtractionError("The PDF has no pages.")

        pages = [
            ExtractedPage(
                page_number=index + 1,
                text=page.get_text("text").strip(),
            )
            for index, page in enumerate(document)
        ]
    finally:
        document.close()

    if not any(page.text for page in pages):
        raise ScannedPdfError("This PDF has no extractable text. Scanned PDFs are not supported.")

    return pages
