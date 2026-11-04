"""Token-based chunking that respects page boundaries."""

from dataclasses import dataclass

import tiktoken

from app.services.extraction import ExtractedPage

_ENCODING_NAME = "cl100k_base"


@dataclass(frozen=True)
class ChunkDraft:
    page_number: int
    chunk_index: int
    content: str
    token_count: int


@dataclass(frozen=True)
class ChunkingConfig:
    chunk_tokens: int = 350
    overlap_tokens: int = 50

    def __post_init__(self) -> None:
        if self.chunk_tokens <= 0:
            raise ValueError("chunk_tokens must be positive.")
        if self.overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative.")
        if self.overlap_tokens >= self.chunk_tokens:
            raise ValueError("overlap_tokens must be smaller than chunk_tokens.")


def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(_ENCODING_NAME)


def chunk_pages(pages: list[ExtractedPage], config: ChunkingConfig) -> list[ChunkDraft]:
    """Split every page into overlapping token windows.

    The same tokenizer family (``cl100k_base``) is used by the embedding
    model, so ``token_count`` reflects what will actually be embedded.
    The window step is ``chunk_tokens - overlap_tokens``; with the default
    350/50 that is 300 tokens of new text per chunk.
    """
    encoding = _encoding()
    step = config.chunk_tokens - config.overlap_tokens
    drafts: list[ChunkDraft] = []

    for page in pages:
        if not page.text:
            continue

        tokens = encoding.encode(page.text, disallowed_special=())
        if not tokens:
            continue

        start = 0
        while start < len(tokens):
            window = tokens[start : start + config.chunk_tokens]
            content = encoding.decode(window).strip()

            if content:
                drafts.append(
                    ChunkDraft(
                        page_number=page.page_number,
                        chunk_index=len(drafts),
                        content=content,
                        token_count=len(window),
                    )
                )

            if start + config.chunk_tokens >= len(tokens):
                break
            start += step

    if not drafts:
        raise ValueError("Chunking produced no chunks.")

    return drafts
