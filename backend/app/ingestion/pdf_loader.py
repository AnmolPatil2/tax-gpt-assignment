from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber
import tiktoken

from app.config import settings
from app.retrieval import vector_store, graph_store

logger = logging.getLogger(__name__)

_enc = None

def _get_encoder():
    global _enc
    if _enc is None:
        _enc = tiktoken.encoding_for_model("gpt-4o")
    return _enc


def _chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    enc = _get_encoder()
    tokens = enc.encode(text)

    chunks = []
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        if chunk_text.strip():
            chunks.append(chunk_text.strip())
        start += chunk_size - chunk_overlap

    return chunks


def _extract_sections_from_pages(page_texts: list[tuple[int, str]]) -> list[dict]:
    sections = []
    header_pattern = re.compile(
        r"^((?:Chapter|Section|Part|Schedule|Line|Form)\s+[\w\d.]+[:\s\u2014\u2013-].*"
        r"|[A-Z][A-Za-z\s,]+(?:\.{3,}|\s{3,})\d+)",
        re.IGNORECASE,
    )

    for page_num, text in page_texts:
        for line in text.split("\n"):
            line_s = line.strip()
            if header_pattern.match(line_s) and len(line_s) > 5:
                sections.append({
                    "title": line_s[:200],
                    "page": page_num,
                    "content_preview": "",
                })

    return sections[:500]


def ingest(file_path: str | Path) -> dict:
    file_path = Path(file_path)
    logger.info(f"Ingesting PDF: {file_path.name}")

    # Stream pages and embed in batches to handle huge PDFs
    EMBED_BATCH = 50  # embed every 50 chunks to avoid memory buildup

    all_page_texts: list[tuple[int, str]] = []
    pending_ids = []
    pending_texts = []
    pending_metas = []
    chunk_idx = 0
    total_embedded = 0
    pages_processed = 0

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        logger.info(f"PDF has {total_pages} pages — processing in streaming batches")

        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue

            pages_processed += 1
            all_page_texts.append((i + 1, text))

            chunks = _chunk_text(text, settings.chunk_size, settings.chunk_overlap)
            for chunk in chunks:
                pending_ids.append(f"pdf_{file_path.stem}_{chunk_idx}")
                pending_texts.append(chunk)
                pending_metas.append({
                    "source_type": "pdf",
                    "document": file_path.name,
                    "page": i + 1,
                })
                chunk_idx += 1

            # Flush batch to ChromaDB when we have enough
            if len(pending_ids) >= EMBED_BATCH:
                vector_store.add_documents(pending_ids, pending_texts, pending_metas)
                total_embedded += len(pending_ids)
                logger.info(
                    f"  [{file_path.name}] Embedded {total_embedded} chunks "
                    f"(page {i + 1}/{total_pages})"
                )
                pending_ids.clear()
                pending_texts.clear()
                pending_metas.clear()

    # Flush remaining chunks
    if pending_ids:
        vector_store.add_documents(pending_ids, pending_texts, pending_metas)
        total_embedded += len(pending_ids)

    logger.info(
        f"PDF {file_path.name} complete: {pages_processed} pages, "
        f"{total_embedded} chunks embedded"
    )

    # Graph: document structure
    sections = _extract_sections_from_pages(all_page_texts)
    if sections:
        try:
            graph_store.insert_document_structure(
                title=file_path.name,
                doc_type="PDF",
                sections=sections,
            )
            logger.info(f"Added {len(sections)} sections to Neo4j for {file_path.name}")
        except Exception as e:
            logger.warning(f"Failed to add document structure to Neo4j: {e}")

    return {
        "pages_processed": pages_processed,
        "vector_chunks": total_embedded,
        "graph_sections": len(sections),
    }
