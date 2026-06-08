"""
ingestor.py — End-to-end document ingestion into rag_documents.
Flow: raw text → chunk → embed (batch) → upsert to DB.
Supports re-ingestion: deletes existing chunks for the same doc_id before inserting.
"""
import structlog
from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag_document import RAGDocument
from app.rag.chunker import chunk_text, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP
from app.rag.embedder import embed_batch

log = structlog.get_logger()


async def ingest_document(
    doc_id: str,
    title: str,
    raw_text: str,
    db: AsyncSession,
    metadata: dict | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    replace: bool = True,
) -> dict:
    """
    Ingest a document into rag_documents.

    Args:
        doc_id:     Logical document identifier (e.g. "ley_inmobiliaria_2024").
        title:      Human-readable title stored with each chunk.
        raw_text:   Full document text.
        db:         Async DB session.
        metadata:   Optional JSON metadata stored per chunk.
        replace:    If True, delete existing chunks for this doc_id first.

    Returns:
        {"doc_id", "chunks_created", "chunks_replaced"}
    """
    if not raw_text.strip():
        return {"doc_id": doc_id, "chunks_created": 0, "chunks_replaced": 0, "error": "empty text"}

    replaced = 0
    if replace:
        result = await db.execute(delete(RAGDocument).where(RAGDocument.doc_id == doc_id))
        replaced = result.rowcount
        log.info("ingestor.replaced_chunks", doc_id=doc_id, count=replaced)

    chunks = chunk_text(raw_text, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        return {"doc_id": doc_id, "chunks_created": 0, "chunks_replaced": replaced}

    texts = [c.content for c in chunks]
    embeddings = await embed_batch(texts)

    meta = metadata or {}
    for chunk, emb in zip(chunks, embeddings):
        doc = RAGDocument(
            doc_id=doc_id,
            title=title,
            chunk_index=chunk.index,
            content=chunk.content,
            embedding=emb,
            metadata_={
                **meta,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(doc)

    await db.commit()
    log.info("ingestor.complete", doc_id=doc_id, chunks=len(chunks))
    return {"doc_id": doc_id, "chunks_created": len(chunks), "chunks_replaced": replaced}


async def list_documents(db: AsyncSession) -> list[dict]:
    """Return one summary row per logical document (doc_id)."""
    from sqlalchemy import func
    stmt = (
        select(
            RAGDocument.doc_id,
            RAGDocument.title,
            func.count(RAGDocument.id).label("chunks"),
            func.max(RAGDocument.created_at).label("last_updated"),
        )
        .group_by(RAGDocument.doc_id, RAGDocument.title)
        .order_by(RAGDocument.title)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"doc_id": r.doc_id, "title": r.title, "chunks": r.chunks, "last_updated": r.last_updated}
        for r in rows
    ]
