from __future__ import annotations

import logging
from pathlib import Path

from app.config import settings
from app.retrieval import graph_store, vector_store
from app.ingestion import csv_loader, pdf_loader, ppt_loader

logger = logging.getLogger(__name__)


def _vectors_exist() -> bool:
    try:
        return vector_store.get_document_count() > 100
    except Exception:
        return False


def _graph_exists() -> bool:
    try:
        return graph_store.get_node_count() > 100
    except Exception:
        return False


def run_ingestion(data_dir: str | None = None, force: bool = False) -> dict:
    """Smart ingestion pipeline:
    - If ChromaDB already has embeddings, skip vector ingestion (saves API cost).
    - If Neo4j is empty, always load graph data (no API calls needed).
    - Use force=True to re-ingest everything.
    """
    vectors_ready = not force and _vectors_exist()
    graph_ready = not force and _graph_exists()

    if vectors_ready and graph_ready:
        vec_count = vector_store.get_document_count()
        logger.info(f"All data already ingested ({vec_count} vectors, graph loaded). Skipping.")
        return {
            "documents_processed": 0,
            "chunks_created": 0,
            "graph_nodes_created": 0,
            "status": "already_ingested",
            "existing_vectors": vec_count,
        }

    data_path = Path(data_dir or settings.data_dir)
    logger.info(f"Starting ingestion from {data_path}")
    logger.info(f"  Vectors: {'SKIP (already loaded)' if vectors_ready else 'WILL EMBED'}")
    logger.info(f"  Graph:   {'SKIP (already loaded)' if graph_ready else 'WILL LOAD'}")

    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    # Initialize graph schema
    if not graph_ready:
        try:
            graph_store.create_constraints()
            graph_store.create_indexes()
            logger.info("Neo4j constraints and indexes created")
        except Exception as e:
            logger.warning(f"Could not set up Neo4j schema (is it running?): {e}")

    stats = {
        "documents_processed": 0,
        "chunks_created": 0,
        "graph_nodes_created": 0,
    }

    # Process CSV files
    for csv_file in data_path.glob("*.csv"):
        try:
            result = csv_loader.ingest(
                csv_file,
                skip_vectors=vectors_ready,
                skip_graph=graph_ready,
            )
            stats["documents_processed"] += 1
            stats["chunks_created"] += result.get("vector_chunks", 0)
            stats["graph_nodes_created"] += result.get("graph_nodes", 0)
            logger.info(f"CSV ingestion complete: {result}")
        except Exception as e:
            logger.error(f"Failed to ingest {csv_file.name}: {e}", exc_info=True)

    # Process PDF files
    for pdf_file in data_path.glob("*.pdf"):
        if vectors_ready:
            logger.info(f"Skipping PDF {pdf_file.name} (vectors already loaded)")
            continue
        try:
            result = pdf_loader.ingest(pdf_file)
            stats["documents_processed"] += 1
            stats["chunks_created"] += result["vector_chunks"]
            stats["graph_nodes_created"] += result.get("graph_sections", 0)
            logger.info(f"PDF ingestion complete: {result}")
        except Exception as e:
            logger.error(f"Failed to ingest {pdf_file.name}: {e}", exc_info=True)

    # Process PPT/PPTX files
    for pattern in ("*.ppt", "*.pptx"):
        for ppt_file in data_path.glob(pattern):
            if vectors_ready:
                logger.info(f"Skipping PPT {ppt_file.name} (vectors already loaded)")
                continue
            try:
                result = ppt_loader.ingest(ppt_file)
                stats["documents_processed"] += 1
                stats["chunks_created"] += result["vector_chunks"]
                logger.info(f"PPT ingestion complete: {result}")
            except Exception as e:
                logger.error(f"Failed to ingest {ppt_file.name}: {e}", exc_info=True)

    logger.info(f"Ingestion pipeline complete: {stats}")
    return stats
