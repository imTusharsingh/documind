"""Grounded answer generation behind a small provider interface."""

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI, OpenAIError

from app.core.config import Settings
from app.repositories.search import SearchHit

logger = logging.getLogger(__name__)


class AnswerProviderError(Exception):
    """Raised when the answer provider cannot return a usable answer."""


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    citation_chunk_ids: list[str]
    input_tokens: int | None
    output_tokens: int | None


class AnswerProvider(Protocol):
    def answer(
        self,
        question: str,
        passages: Sequence[SearchHit],
        history: Sequence[tuple[str, str]],
    ) -> GeneratedAnswer:
        """Generate an answer whose citations refer to passage chunk ids."""


class OpenAIAnswerProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        client: OpenAI | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
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

    def answer(
        self,
        question: str,
        passages: Sequence[SearchHit],
        history: Sequence[tuple[str, str]],
    ) -> GeneratedAnswer:
        if not self._api_key:
            raise AnswerProviderError("Answers are not configured. Set OPENAI_API_KEY on the API.")

        source_text = "\n\n".join(
            f"SOURCE {hit.chunk_id}: {hit.document_name}, page {hit.page_number}\n{hit.content}"
            for hit in passages
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a document research assistant. Answer only from the supplied sources. "
                    "If the sources do not support an answer, say so clearly. Every factual claim "
                    "must be supported by one or more source chunk ids. Return JSON only."
                ),
            },
            *({"role": role, "content": content} for role, content in history),
            {
                "role": "user",
                "content": f"Question:\n{question}\n\nSources:\n{source_text}",
            },
        ]

        try:
            response = self._get_client().chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "grounded_answer",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "answer": {"type": "string"},
                                "citation_chunk_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["answer", "citation_chunk_ids"],
                            "additionalProperties": False,
                        },
                    },
                },
            )
        except OpenAIError as exc:
            logger.warning("Answer provider request failed: %s", exc)
            raise AnswerProviderError(
                "The answer provider request failed. Check API logs."
            ) from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise AnswerProviderError("The answer provider returned an empty response.")

        try:
            payload = json.loads(content)
            answer = str(payload["answer"]).strip()
            citations = [str(value) for value in payload["citation_chunk_ids"]]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AnswerProviderError("The answer provider returned invalid JSON.") from exc

        usage = response.usage
        return GeneratedAnswer(
            answer=answer,
            citation_chunk_ids=citations,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )


def create_answer_provider(settings: Settings) -> AnswerProvider:
    return OpenAIAnswerProvider(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.llm_model,
        timeout_seconds=settings.embedding_timeout_seconds,
        max_retries=settings.embedding_max_retries,
    )
