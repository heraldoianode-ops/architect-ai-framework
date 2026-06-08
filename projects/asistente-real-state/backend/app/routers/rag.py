"""
rag.py — RAG admin + query endpoints.

Admin (administrador only):
  POST /rag/documents          — ingest a document (plain text or extracted PDF)
  DELETE /rag/documents/{id}   — delete all chunks for a doc_id
  GET /rag/documents           — list all ingested documents

Agent-accessible:
  POST /rag/query              — semantic search (used by agent tools)
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin, require_agent_or_above
from app.core.database import get_db
from app.models.rag_document import RAGDocument
from app.rag.ingestor import ingest_document, list_documents
from app.rag.retriever import retrieve, format_context

router = APIRouter(prefix="/rag", tags=["rag"])


# ─── Schemas ──────────────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    doc_id: str = Field(..., min_length=1, max_length=120, pattern=r"^[a-z0-9_\-]+$")
    title: str = Field(..., min_length=1, max_length=300)
    text: str = Field(..., min_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)
    replace: bool = True


class IngestResponse(BaseModel):
    doc_id: str
    chunks_created: int
    chunks_replaced: int


class DocumentInfo(BaseModel):
    doc_id: str
    title: str
    chunks: int


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(5, ge=1, le=20)
    doc_id_filter: str | None = None
    return_context: bool = True  # False → return raw chunks list


class ChunkResult(BaseModel):
    doc_id: str
    title: str
    content: str
    chunk_index: int
    similarity: float


class RAGQueryResponse(BaseModel):
    context: str | None        # formatted block for LLM prompt
    chunks: list[ChunkResult]  # raw chunks
    total_found: int


# ─── Admin endpoints ───────────────────────────────────────────────────────────
@router.post("/documents", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest(
    body: IngestRequest,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    result = await ingest_document(
        doc_id=body.doc_id,
        title=body.title,
        raw_text=body.text,
        db=db,
        metadata=body.metadata,
        replace=body.replace,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/documents", response_model=list[DocumentInfo])
async def list_docs(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    return await list_documents(db)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    result = await db.execute(delete(RAGDocument).where(RAGDocument.doc_id == doc_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.commit()


# ─── Query endpoint ────────────────────────────────────────────────────────────
@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    body: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
):
    """Semantic search over ingested documents. Used by the ReAct agent tool."""
    chunks = await retrieve(
        query=body.query,
        db=db,
        top_k=body.top_k,
        doc_id_filter=body.doc_id_filter,
    )
    context = format_context(chunks) if body.return_context and chunks else None
    return RAGQueryResponse(
        context=context,
        chunks=[
            ChunkResult(
                doc_id=c.doc_id,
                title=c.title,
                content=c.content,
                chunk_index=c.chunk_index,
                similarity=c.similarity,
            )
            for c in chunks
        ],
        total_found=len(chunks),
    )
