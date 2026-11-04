import uuid

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    document_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Query cannot be empty.")
        return normalized


class SearchResult(BaseModel):
    document_id: uuid.UUID
    document_name: str
    page_number: int
    chunk_index: int
    content: str
    similarity: float = Field(ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
