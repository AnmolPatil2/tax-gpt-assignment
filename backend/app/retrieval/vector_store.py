from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.llm.client import get_embedding, get_embeddings_batch


_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_documents(
    ids: list[str],
    texts: list[str],
    metadatas: list[dict],
    batch_size: int = 100,
) -> int:
    collection = get_collection()
    total_added = 0

    for i in range(0, len(texts), batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_texts = texts[i : i + batch_size]
        batch_metas = metadatas[i : i + batch_size]

        embeddings = get_embeddings_batch(batch_texts)

        collection.upsert(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_metas,
        )
        total_added += len(batch_ids)

    return total_added


def search(query: str, n_results: int = 10, where: dict | None = None) -> list[dict]:
    collection = get_collection()
    query_embedding = get_embedding(query)

    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    documents = []
    if results["documents"] and results["metadatas"] and results["distances"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            documents.append({
                "content": doc,
                "metadata": meta,
                "relevance_score": 1 - dist,  # cosine distance to similarity
            })

    return documents


def get_document_count() -> int:
    collection = get_collection()
    return collection.count()


def reset() -> None:
    global _collection, _chroma_client
    client = get_chroma_client()
    try:
        client.delete_collection(settings.chroma_collection_name)
    except Exception:
        pass
    _collection = None
