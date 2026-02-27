import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    ChatRequest,
    IngestRequest,
    IngestResponse,
    HealthResponse,
)
from app.retrieval.hybrid import retrieve_and_generate
from app.retrieval import vector_store, graph_store
from app.ingestion.pipeline import run_ingestion

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    neo4j_ok = False
    try:
        neo4j_ok = graph_store.verify_connection()
    except Exception:
        pass

    chroma_ready = False
    doc_count = 0
    try:
        doc_count = vector_store.get_document_count()
        chroma_ready = True
    except Exception:
        pass

    return HealthResponse(
        status="ok" if (neo4j_ok and chroma_ready) else "degraded",
        neo4j_connected=neo4j_ok,
        chroma_ready=chroma_ready,
        documents_ingested=doc_count,
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_data(request: Optional[IngestRequest] = None):
    try:
        data_dir = request.data_dir if request else None
        stats = run_ingestion(data_dir)
        return IngestResponse(
            status="success",
            documents_processed=stats["documents_processed"],
            chunks_created=stats["chunks_created"],
            graph_nodes_created=stats["graph_nodes_created"],
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint that streams responses via Server-Sent Events."""

    def event_stream():
        try:
            for chunk in retrieve_and_generate(request.message):
                data = json.dumps(chunk)
                yield f"data: {data}\n\n"
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            error_data = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
