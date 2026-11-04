import uuid

from pydantic import BaseModel, Field, field_validator


class ExpectedSource(BaseModel):
    document_id: uuid.UUID
    page_number: int = Field(ge=1)


class EvaluationCase(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    expected_sources: list[ExpectedSource] = Field(min_length=1, max_length=50)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Question cannot be empty.")
        return normalized


class EvaluationRequest(BaseModel):
    cases: list[EvaluationCase] = Field(min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class RetrievedSource(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    chunk_index: int
    similarity: float


class EvaluationCaseResult(BaseModel):
    question: str
    recall_at_k: float
    reciprocal_rank: float
    page_match: bool
    retrieved_sources: list[RetrievedSource]


class EvaluationResponse(BaseModel):
    case_count: int
    recall_at_k: float
    mean_reciprocal_rank: float
    page_match_rate: float
    results: list[EvaluationCaseResult]
