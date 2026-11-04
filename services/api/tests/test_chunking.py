import pytest

from app.services.chunking import ChunkingConfig, chunk_pages
from app.services.extraction import ExtractedPage

LONG_PAGE = " ".join(f"token{i}" for i in range(1000))


def test_chunks_never_cross_page_boundaries() -> None:
    pages = [
        ExtractedPage(page_number=1, text=LONG_PAGE),
        ExtractedPage(page_number=2, text=LONG_PAGE),
    ]

    chunks = chunk_pages(pages, ChunkingConfig(chunk_tokens=350, overlap_tokens=50))

    first_page = [chunk for chunk in chunks if chunk.page_number == 1]
    second_page = [chunk for chunk in chunks if chunk.page_number == 2]

    assert len(first_page) > 1
    assert len(second_page) > 1
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.token_count <= 350 for chunk in chunks)


def test_adjacent_chunks_overlap_by_the_configured_window() -> None:
    page = ExtractedPage(page_number=1, text=LONG_PAGE)

    chunks = chunk_pages([page], ChunkingConfig(chunk_tokens=350, overlap_tokens=50))
    contiguous = chunk_pages([page], ChunkingConfig(chunk_tokens=350, overlap_tokens=0))

    # With a 50-token overlap the first chunk's tail reappears at the
    # start of the second, while a non-overlapping split shares nothing.
    assert chunks[0].content[-100:] in chunks[1].content
    assert chunks[1].content[:100] in chunks[0].content
    assert contiguous[0].content[-100:] not in contiguous[1].content


def test_empty_pages_are_skipped() -> None:
    chunks = chunk_pages(
        [
            ExtractedPage(page_number=1, text=""),
            ExtractedPage(page_number=2, text="Only this page has text."),
        ],
        ChunkingConfig(),
    )

    assert len(chunks) == 1
    assert chunks[0].page_number == 2


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="overlap_tokens must be smaller"):
        ChunkingConfig(chunk_tokens=100, overlap_tokens=100)

    with pytest.raises(ValueError, match="chunk_tokens must be positive"):
        ChunkingConfig(chunk_tokens=0, overlap_tokens=0)
