"""
retriever.py — ANN search in pgvector for RAG.
Uses cosine distance (<=> operator) with the ivfflat index on rag_documents.embedding.
Returns top-k chunks ranked by similarity.
"""
import structlog
from dataclasses import dataclass
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag_document import RAGDocument
from app.rag.embedder import embed_text

log = structlog.get_logger()

DEFAULT_TOP_K = 5
MIN_SIMILARITY = 0.25  # discard chunks below this cosine similarity


@dataclass
class RetrievedChunk:
    doc_id: str
    title: str
    content: str
    chunk_index: int
    similarity: float


async def retrieve(
    query: str,
    db: AsyncSession,
    top_k: int = DEFAULT_TOP_K,
    doc_id_filter: str | None = None,
) -> list[RetrievedChunk]:
    """
    Embed query → ANN search → return top_k chunks above MIN_SIMILARITY.
    Optionally filter to a specific doc_id (logical document group).
    """
    query_vector = await embed_text(query)

    # pgvector cosine distance: 1 - similarity
    distance_expr = RAGDocument.embedding.op("<=>")(
        text(f"'{query_vector}'::vector")
    )

    stmt = (
        select(
            RAGDocument.doc_id,
            RAGDocument.title,
            RAGDocument.content,
            RAGDocument.chunk_index,
            (1 - distance_expr).label("similarity"),
        )
        .where(RAGDocument.embedding.is_not(None))
        .order_by(distance_expr)
        .limit(top_k * 2)  # fetch extra, filter below threshold
    )

    if doc_id_filter:
        stmt = stmt.where(RAGDocument.doc_id == doc_id_filter)

    rows = (await db.execute(stmt)).all()

    chunks = [
        RetrievedChunk(
            doc_id=row.doc_id,
            title=row.title,
            content=row.content,
            chunk_index=row.chunk_index,
            similarity=float(row.similarity),
        )
        for row in rows
        if float(row.similarity) >= MIN_SIMILARITY
    ][:top_k]

    log.debug("retriever.results", query=query[:60], found=len(chunks))
    return chunks


def format_context(chunks: list[RetrievedChunk], max_chars: int = 6000) -> str:
    """
    Format retrieved chunks as a numbered context block for the LLM prompt.
    Truncates to max_chars to stay within context window.
    """
    parts: list[str] = []
    total = 0
    for i, chunk in enumerate(chunks, 1):
        block = f"[{i}] {chunk.title} (similitud: {chunk.similarity:.2f})\n{chunk.content}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts)
