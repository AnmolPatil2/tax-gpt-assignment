from __future__ import annotations

from openai import OpenAI
from typing import Generator

from app.config import settings


_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def get_embedding(text: str) -> list[float]:
    client = get_openai_client()
    response = client.embeddings.create(
        input=text,
        model=settings.openai_embedding_model,
    )
    return response.data[0].embedding


def get_embeddings_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    client = get_openai_client()
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model=settings.openai_embedding_model,
        )
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


def chat_completion(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    client = get_openai_client()
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def chat_completion_stream(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> Generator[str, None, None]:
    client = get_openai_client()
    stream = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


def chat_completion_with_tools(
    messages: list[dict],
    tools: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 2048,
):
    """Non-streaming completion that supports function calling / tools."""
    client = get_openai_client()
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0]
