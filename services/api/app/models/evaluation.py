import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cases: Mapped[list["EvaluationDatasetCase"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="EvaluationDatasetCase.position",
    )
    runs: Mapped[list["EvaluationRun"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="EvaluationRun.created_at.desc()",
    )


class EvaluationDatasetCase(Base):
    __tablename__ = "evaluation_dataset_cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(String(2000))
    expected_sources: Mapped[list[dict[str, object]]] = mapped_column(JSON)

    dataset: Mapped[EvaluationDataset] = relationship(back_populates="cases")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), index=True
    )
    top_k: Mapped[int] = mapped_column(Integer)
    min_similarity: Mapped[float] = mapped_column()
    case_count: Mapped[int] = mapped_column(Integer)
    recall_at_k: Mapped[float] = mapped_column()
    mean_reciprocal_rank: Mapped[float] = mapped_column()
    page_match_rate: Mapped[float] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped[EvaluationDataset] = relationship(back_populates="runs")
    results: Mapped[list["EvaluationRunResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="EvaluationRunResult.position"
    )


class EvaluationRunResult(Base):
    __tablename__ = "evaluation_run_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True))
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(String(2000))
    recall_at_k: Mapped[float] = mapped_column()
    reciprocal_rank: Mapped[float] = mapped_column()
    page_match: Mapped[bool] = mapped_column()
    retrieved_sources: Mapped[list[dict[str, object]]] = mapped_column(JSON)

    run: Mapped[EvaluationRun] = relationship(back_populates="results")
