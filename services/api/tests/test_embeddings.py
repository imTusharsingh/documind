from types import SimpleNamespace
from typing import Any

import pytest
from openai import OpenAIError

from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    OpenAIEmbeddingProvider,
)


class FakeEmbeddingsResource:
    def __init__(
        self,
        *,
        vector: list[float] | None = None,
        reverse: bool = False,
        error: Exception | None = None,
        drop_last: bool = False,
    ) -> None:
        self.vector = vector
        self.reverse = reverse
        self.error = error
        self.drop_last = drop_last
        self.calls: list[dict[str, Any]] = []

    def create(self, *, model: str, input: list[str], dimensions: int) -> Any:
        self.calls.append({"model": model, "input": list(input), "dimensions": dimensions})
        if self.error is not None:
            raise self.error

        vectors = [
            self.vector if self.vector is not None else [float(index), float(len(text)), 1.0]
            for index, text in enumerate(input)
        ]
        if self.drop_last:
            vectors = vectors[:-1]

        items = [
            SimpleNamespace(index=index, embedding=vector) for index, vector in enumerate(vectors)
        ]
        if self.reverse:
            items.reverse()
        return SimpleNamespace(data=items)


def _provider(
    resource: FakeEmbeddingsResource,
    *,
    api_key: str = "test-key",
    dimensions: int = 3,
    batch_size: int = 2,
) -> OpenAIEmbeddingProvider:
    client = SimpleNamespace(embeddings=resource)
    return OpenAIEmbeddingProvider(
        api_key=api_key,
        model="test-model",
        dimensions=dimensions,
        batch_size=batch_size,
        timeout_seconds=5,
        max_retries=0,
        client=client,  # type: ignore[arg-type]
    )


def test_embeds_empty_input_without_calling_the_provider() -> None:
    resource = FakeEmbeddingsResource()

    assert _provider(resource, api_key="").embed_texts([]) == []
    assert resource.calls == []


def test_missing_api_key_fails_before_any_request() -> None:
    resource = FakeEmbeddingsResource()

    with pytest.raises(EmbeddingConfigurationError, match="OPENAI_API_KEY"):
        _provider(resource, api_key="").embed_texts(["hello"])

    assert resource.calls == []


def test_batches_inputs_and_preserves_provider_order() -> None:
    resource = FakeEmbeddingsResource(reverse=True)
    provider = _provider(resource, batch_size=2)

    vectors = provider.embed_texts(["first", "second", "third"])

    assert [call["input"] for call in resource.calls] == [["first", "second"], ["third"]]
    assert len(vectors) == 3
    # Fake client derives the first component from the provider index, so
    # sorted output must be 0, 1, 2 rather than reversed.
    assert [vector[0] for vector in vectors] == [0.0, 1.0, 0.0]


def test_rejects_a_response_with_the_wrong_number_of_vectors() -> None:
    resource = FakeEmbeddingsResource(drop_last=True)
    provider = _provider(resource, batch_size=2)

    with pytest.raises(EmbeddingProviderError, match="wrong number"):
        provider.embed_texts(["one", "two"])


def test_rejects_a_vector_with_the_wrong_dimension() -> None:
    resource = FakeEmbeddingsResource(vector=[1.0, 2.0])
    provider = _provider(resource, dimensions=3)

    with pytest.raises(EmbeddingProviderError, match="wrong dimension"):
        provider.embed_texts(["one"])


def test_provider_errors_are_wrapped_without_leaking_details() -> None:
    resource = FakeEmbeddingsResource(error=OpenAIError("secret upstream detail"))
    provider = _provider(resource)

    with pytest.raises(EmbeddingProviderError) as excinfo:
        provider.embed_texts(["one"])

    assert "secret upstream detail" not in str(excinfo.value)
    assert "Check worker logs" in str(excinfo.value)
