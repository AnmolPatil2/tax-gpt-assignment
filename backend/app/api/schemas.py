from pydantic import BaseModel
from typing import Dict, List, Optional


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class SourceReference(BaseModel):
    source_type: str
    document: str
    content: str
    relevance_score: float = 0.0
    metadata: Dict = {}


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceReference] = []
    retrieval_strategy: str = ""


class IngestRequest(BaseModel):
    data_dir: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    chunks_created: int
    graph_nodes_created: int


class HealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    chroma_ready: bool
    documents_ingested: int
