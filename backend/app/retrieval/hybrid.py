from __future__ import annotations

import json
import logging
from typing import Generator

from app.retrieval.query_router import classify_query
from app.retrieval import vector_store, graph_store
from app.llm.client import chat_completion_stream
from app.llm.prompts import SYSTEM_PROMPT, ANSWER_WITH_CONTEXT_PROMPT

logger = logging.getLogger(__name__)


def _format_graph_results(graph_data: dict) -> str:
    """Format Neo4j query results into readable context."""
    if graph_data.get("error"):
        return f"[Graph query error: {graph_data['error']}]"

    results = graph_data.get("results", [])
    if not results:
        return "[No results found in graph database]"

    cypher = graph_data.get("cypher", "")
    lines = [f"Graph Query: {cypher}", "Results:"]

    for row in results[:25]:
        formatted_values = []
        for k, v in row.items():
            if isinstance(v, float):
                formatted_values.append(f"{k}: {v:,.2f}")
            else:
                formatted_values.append(f"{k}: {v}")
        lines.append("  " + ", ".join(formatted_values))

    return "\n".join(lines)


def _format_vector_results(docs: list[dict]) -> str:
    """Format ChromaDB search results into readable context."""
    if not docs:
        return "[No relevant documents found]"

    lines = ["Retrieved Documents:"]
    for i, doc in enumerate(docs, 1):
        meta = doc.get("metadata", {})
        source = meta.get("document", "unknown")
        source_type = meta.get("source_type", "unknown")
        score = doc.get("relevance_score", 0)

        lines.append(f"\n[Source {i}: {source} ({source_type}, relevance: {score:.2f})]")
        lines.append(doc.get("content", "")[:800])

    return "\n".join(lines)


def _build_sources(
    vector_docs: list[dict] | None,
    graph_data: dict | None,
) -> list[dict]:
    """Build source references for the response."""
    sources = []

    if vector_docs:
        for doc in vector_docs[:5]:
            meta = doc.get("metadata", {})
            sources.append({
                "source_type": meta.get("source_type", "unknown"),
                "document": meta.get("document", "unknown"),
                "content": doc.get("content", "")[:300],
                "relevance_score": doc.get("relevance_score", 0),
                "metadata": {
                    k: v for k, v in meta.items()
                    if k not in ("source_type", "document")
                },
            })

    if graph_data and graph_data.get("results") and not graph_data.get("error"):
        sources.append({
            "source_type": "graph_query",
            "document": "Neo4j Knowledge Graph",
            "content": json.dumps(graph_data["results"][:5], default=str)[:300],
            "relevance_score": 1.0,
            "metadata": {"cypher": graph_data.get("cypher", "")},
        })

    return sources


def retrieve_and_generate(question: str) -> Generator[dict, None, None]:
    """Main hybrid retrieval + generation pipeline. Yields streaming chunks."""
    strategy = classify_query(question)
    logger.info(f"Retrieval strategy: {strategy}")

    context_parts: list[str] = []
    vector_docs: list[dict] | None = None
    graph_data: dict | None = None

    # Vector retrieval
    if strategy in ("semantic", "hybrid"):
        try:
            vector_docs = vector_store.search(question, n_results=8)
            context_parts.append(_format_vector_results(vector_docs))
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            context_parts.append(f"[Vector search error: {e}]")

    # Graph retrieval
    if strategy in ("structured", "hybrid"):
        try:
            graph_data = graph_store.generate_and_execute_cypher(question)
            context_parts.append(_format_graph_results(graph_data))
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            context_parts.append(f"[Graph query error: {e}]")

    # If structured-only had no results, fall back to vector
    if strategy == "structured" and (not graph_data or graph_data.get("error") or not graph_data.get("results")):
        logger.info("Structured query failed, falling back to vector search")
        vector_docs = vector_store.search(question, n_results=8)
        context_parts.append(_format_vector_results(vector_docs))

    # Build context and generate answer
    full_context = "\n\n".join(context_parts)
    user_message = ANSWER_WITH_CONTEXT_PROMPT.format(
        context=full_context,
        question=question,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Yield metadata first
    sources = _build_sources(vector_docs, graph_data)
    yield {
        "type": "metadata",
        "strategy": strategy,
        "sources": sources,
    }

    # Stream the answer
    for token in chat_completion_stream(messages):
        yield {
            "type": "token",
            "content": token,
        }

    yield {"type": "done"}
