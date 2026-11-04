import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_owner, get_embedding_provider
from app.core.db import get_session
from app.core.errors import EmbeddingUnavailableError, NotFoundError
from app.models.document import Document
from app.models.evaluation import (
    EvaluationDataset,
    EvaluationDatasetCase,
    EvaluationRun,
    EvaluationRunResult,
)
from app.models.user import User
from app.repositories.search import search_chunks
from app.schemas.evaluation import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationDatasetCreate,
    EvaluationDatasetDetail,
    EvaluationDatasetSummary,
    EvaluationDatasetUpdate,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationRunSummary,
    EvaluationTrendResponse,
    RetrievedSource,
)
from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.services.evaluation import evaluate_case

router = APIRouter()


def _get_dataset(session: Session, owner_id: uuid.UUID, dataset_id: uuid.UUID) -> EvaluationDataset:
    dataset = session.scalar(
        select(EvaluationDataset)
        .where(EvaluationDataset.id == dataset_id, EvaluationDataset.owner_id == owner_id)
        .options(selectinload(EvaluationDataset.cases), selectinload(EvaluationDataset.runs))
    )
    if dataset is None:
        raise NotFoundError("Evaluation dataset was not found.")
    return dataset


def _run_summary(run: EvaluationRun) -> EvaluationRunSummary:
    return EvaluationRunSummary(
        id=run.id,
        top_k=run.top_k,
        min_similarity=run.min_similarity,
        case_count=run.case_count,
        recall_at_k=run.recall_at_k,
        mean_reciprocal_rank=run.mean_reciprocal_rank,
        page_match_rate=run.page_match_rate,
        label=run.label,
        embedding_model=run.embedding_model,
        created_at=run.created_at.isoformat(),
    )


def _dataset_summary(dataset: EvaluationDataset) -> EvaluationDatasetSummary:
    latest = dataset.runs[0] if dataset.runs else None
    return EvaluationDatasetSummary(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        case_count=len(dataset.cases),
        run_count=len(dataset.runs),
        latest_run=_run_summary(latest) if latest else None,
        created_at=dataset.created_at.isoformat(),
        updated_at=dataset.updated_at.isoformat(),
    )


def _case_schema(case: EvaluationDatasetCase) -> EvaluationCase:
    return EvaluationCase(question=case.question, expected_sources=case.expected_sources)


def _validate_document_ownership(
    session: Session, owner: User, cases: list[EvaluationCase]
) -> None:
    document_ids = {source.document_id for case in cases for source in case.expected_sources}
    owned_ids = set(
        session.scalars(
            select(Document.id).where(Document.owner_id == owner.id, Document.id.in_(document_ids))
        )
    )
    if owned_ids != document_ids:
        raise NotFoundError("Every expected source must reference one of your documents.")


@router.post(
    "/evaluation/datasets",
    response_model=EvaluationDatasetDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset(
    request: EvaluationDatasetCreate,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> EvaluationDatasetDetail:
    _validate_document_ownership(session, owner, request.cases)
    dataset = EvaluationDataset(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name=request.name,
        description=request.description,
    )
    dataset.cases = [
        EvaluationDatasetCase(
            id=uuid.uuid4(),
            position=position,
            question=case.question,
            expected_sources=[source.model_dump(mode="json") for source in case.expected_sources],
        )
        for position, case in enumerate(request.cases)
    ]
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return EvaluationDatasetDetail(
        **_dataset_summary(dataset).model_dump(),
        cases=[_case_schema(case) for case in dataset.cases],
        runs=[],
    )


@router.get("/evaluation/datasets", response_model=list[EvaluationDatasetSummary])
def list_datasets(
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> list[EvaluationDatasetSummary]:
    datasets = list(
        session.scalars(
            select(EvaluationDataset)
            .where(EvaluationDataset.owner_id == owner.id)
            .options(selectinload(EvaluationDataset.cases), selectinload(EvaluationDataset.runs))
            .order_by(EvaluationDataset.updated_at.desc(), EvaluationDataset.id)
        )
    )
    return [_dataset_summary(dataset) for dataset in datasets]


@router.get("/evaluation/datasets/{dataset_id}", response_model=EvaluationDatasetDetail)
def read_dataset(
    dataset_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> EvaluationDatasetDetail:
    dataset = _get_dataset(session, owner.id, dataset_id)
    return EvaluationDatasetDetail(
        **_dataset_summary(dataset).model_dump(),
        cases=[_case_schema(case) for case in dataset.cases],
        runs=[_run_summary(run) for run in dataset.runs],
    )


@router.patch("/evaluation/datasets/{dataset_id}", response_model=EvaluationDatasetDetail)
def update_dataset(
    dataset_id: uuid.UUID,
    request: EvaluationDatasetUpdate,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> EvaluationDatasetDetail:
    dataset = _get_dataset(session, owner.id, dataset_id)
    if request.name is not None:
        dataset.name = request.name
    if request.description is not None:
        dataset.description = request.description
    if request.cases is not None:
        _validate_document_ownership(session, owner, request.cases)
        dataset.cases = [
            EvaluationDatasetCase(
                id=uuid.uuid4(),
                position=position,
                question=case.question,
                expected_sources=[
                    source.model_dump(mode="json") for source in case.expected_sources
                ],
            )
            for position, case in enumerate(request.cases)
        ]
    session.commit()
    session.refresh(dataset)
    return read_dataset(dataset.id, session, owner)


@router.get(
    "/evaluation/datasets/{dataset_id}/trend",
    response_model=EvaluationTrendResponse,
)
def dataset_trend(
    dataset_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> EvaluationTrendResponse:
    dataset = _get_dataset(session, owner.id, dataset_id)
    return EvaluationTrendResponse(
        dataset_id=dataset.id,
        runs=[_run_summary(run) for run in reversed(dataset.runs)],
    )


@router.post(
    "/evaluation/datasets/{dataset_id}/runs",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_dataset(
    dataset_id: uuid.UUID,
    request: EvaluationRunRequest,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> EvaluationRunResponse:
    dataset = _get_dataset(session, owner.id, dataset_id)
    try:
        vectors = embedding_provider.embed_texts([case.question for case in dataset.cases])
    except (EmbeddingConfigurationError, EmbeddingProviderError) as exc:
        raise EmbeddingUnavailableError(str(exc)) from exc
    if len(vectors) != len(dataset.cases):
        raise EmbeddingUnavailableError(
            "The embedding provider returned the wrong number of vectors."
        )

    results: list[EvaluationCaseResult] = []
    for case, vector in zip(dataset.cases, vectors, strict=True):
        expected = {
            (source["document_id"], source["page_number"]) for source in case.expected_sources
        }
        hits = search_chunks(
            session,
            owner_id=owner.id,
            query_embedding=vector,
            limit=request.top_k,
            min_similarity=request.min_similarity,
        )
        recall, rank, page_match = evaluate_case(hits, expected)
        results.append(
            EvaluationCaseResult(
                question=case.question,
                recall_at_k=recall,
                reciprocal_rank=rank,
                page_match=page_match,
                retrieved_sources=[
                    RetrievedSource(
                        chunk_id=hit.chunk_id,
                        document_id=hit.document_id,
                        document_name=hit.document_name,
                        page_number=hit.page_number,
                        chunk_index=hit.chunk_index,
                        similarity=hit.similarity,
                    )
                    for hit in hits
                ],
            )
        )
    count = len(results)
    run = EvaluationRun(
        id=uuid.uuid4(),
        dataset_id=dataset.id,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        label=request.label,
        embedding_model=request.embedding_model,
        case_count=count,
        recall_at_k=round(sum(item.recall_at_k for item in results) / count, 6),
        mean_reciprocal_rank=round(sum(item.reciprocal_rank for item in results) / count, 6),
        page_match_rate=round(sum(item.page_match for item in results) / count, 6),
    )
    run.results = [
        EvaluationRunResult(
            id=uuid.uuid4(),
            case_id=case.id,
            position=position,
            question=result.question,
            recall_at_k=result.recall_at_k,
            reciprocal_rank=result.reciprocal_rank,
            page_match=result.page_match,
            retrieved_sources=[
                source.model_dump(mode="json") for source in result.retrieved_sources
            ],
        )
        for position, (case, result) in enumerate(zip(dataset.cases, results, strict=True))
    ]
    session.add(run)
    session.commit()
    session.refresh(run)
    return EvaluationRunResponse(
        **_run_summary(run).model_dump(), dataset_id=dataset.id, results=results
    )
