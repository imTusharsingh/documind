"""Embedding provider integration.

The application talks to one hosted provider through a small protocol. Tests
inject a deterministic implementation; production constructs the OpenAI
client from settings. No provider SDK leaks into routes or repositories.
"""

import logging
from collections.abc import Sequence
from typing import Protocol

from openai import OpenAI, OpenAIError

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Base class for expected embedding failures."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when the provider cannot be used because it is unconfigured."""


class EmbeddingProviderError(EmbeddingError):
    """Raised when the provider rejects or corrupts a request."""


class EmbeddingProvider(Protocol):
    """Minimal interface required by ingestion and search."""

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...


class OpenAIEmbeddingProvider:
    """Embedding provider backed by the OpenAI embeddings API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
        batch_size: int,
        timeout_seconds: float,
        max_retries: int,
        client: OpenAI | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._client = client

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self._api_key,
                timeout=self._timeout_seconds,
                max_retries=self._max_retries,
            )
        return self._client

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_key:
            raise EmbeddingConfigurationError(
                "Embeddings are not configured. Set OPENAI_API_KEY on the API and worker."
            )

        client = self._get_client()
        vectors: list[list[float]] = []

        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])

            try:
                response = client.embeddings.create(
                    model=self._model,
                    input=batch,
                    dimensions=self._dimensions,
                )
            except OpenAIError as exc:
                logger.warning("Embedding request failed: %s", exc)
                raise EmbeddingProviderError(
                    "The embedding provider request failed. Check worker logs."
                ) from exc

            items = sorted(response.data, key=lambda item: item.index)
            if len(items) != len(batch):
                raise EmbeddingProviderError(
                    "The embedding provider returned the wrong number of vectors."
                )
            if [item.index for item in items] != list(range(len(batch))):
                raise EmbeddingProviderError(
                    "The embedding provider returned invalid vector indexes."
                )

            for item in items:
                vector = list(item.embedding)
                if len(vector) != self._dimensions:
                    raise EmbeddingProviderError(
                        "The embedding provider returned a vector with the wrong dimension."
                    )
                vectors.append(vector)

        return vectors


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the configured provider for the API process or worker."""
    return OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.embedding_model,
        dimensions=settings.embedding_dim,
        batch_size=settings.embedding_batch_size,
        timeout_seconds=settings.embedding_timeout_seconds,
        max_retries=settings.embedding_max_retries,
    )
