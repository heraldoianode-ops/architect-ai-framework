"""
test_rag.py — L2 unit tests for Node 4.1: RAG pipeline.
Tests: chunker, embedder batch logic, retriever threshold, ingestor flow.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.chunker import chunk_text, Chunk, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP
from app.rag.retriever import format_context, RetrievedChunk, MIN_SIMILARITY


# ─── Chunker ───────────────────────────────────────────────────────────────────
class TestChunker:
    def test_short_text_single_chunk(self):
        text = "Texto corto."
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].index == 0

    def test_empty_text_returns_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_long_text_produces_multiple_chunks(self):
        # ~5x the chunk size
        text = ("Palabra. " * 400).strip()
        chunks = chunk_text(text, chunk_size=500, overlap=100)
        assert len(chunks) >= 2

    def test_chunks_are_indexed_sequentially(self):
        text = "\n\n".join([f"Parrafo numero {i} con contenido." * 10 for i in range(20)])
        chunks = chunk_text(text, chunk_size=800, overlap=150)
        for i, c in enumerate(chunks):
            assert c.index == i

    def test_overlap_content_shared(self):
        # Two consecutive chunks should share some content due to overlap
        text = "\n\n".join([f"Parrafo {i}: " + "contenido relevante " * 30 for i in range(10)])
        chunks = chunk_text(text, chunk_size=600, overlap=120)
        if len(chunks) >= 2:
            # Verify chunk 1 contains text that appeared near end of chunk 0
            tail = chunks[0].content[-80:].split()[-3:]  # last 3 words of chunk 0
            has_overlap = any(word in chunks[1].content for word in tail)
            assert has_overlap, "Consecutive chunks should share content via overlap"

    def test_chunk_size_respected(self):
        text = "\n\n".join(["A" * 300 for _ in range(20)])
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        for c in chunks[:-1]:  # last chunk can be smaller
            assert len(c.content) <= 500 + 50  # small tolerance

    def test_returns_chunk_objects(self):
        chunks = chunk_text("Hello world.")
        assert isinstance(chunks[0], Chunk)
        assert hasattr(chunks[0], "char_start")
        assert hasattr(chunks[0], "char_end")


# ─── format_context ───────────────────────────────────────────────────────────
class TestFormatContext:
    def _chunk(self, content, sim=0.85):
        return RetrievedChunk(
            doc_id="doc1",
            title="Ley de Alquileres 2024",
            content=content,
            chunk_index=0,
            similarity=sim,
        )

    def test_empty_list(self):
        assert format_context([]) == ""

    def test_single_chunk_included(self):
        chunk = self._chunk("El contrato debe ser registrado.")
        ctx = format_context([chunk])
        assert "El contrato debe ser registrado." in ctx
        assert "[1]" in ctx
        assert "0.85" in ctx

    def test_multiple_chunks_numbered(self):
        chunks = [self._chunk(f"Contenido del chunk {i}") for i in range(3)]
        ctx = format_context(chunks)
        assert "[1]" in ctx
        assert "[2]" in ctx
        assert "[3]" in ctx

    def test_max_chars_respected(self):
        big = self._chunk("X" * 2000)
        ctx = format_context([big, big, big, big], max_chars=3000)
        assert len(ctx) <= 3000 + 200  # header overhead


# ─── MIN_SIMILARITY threshold ───────────────────────────────────────────────────
def test_min_similarity_defined():
    assert 0.0 < MIN_SIMILARITY < 1.0


# ─── Ingestor ──────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ingest_empty_text_returns_error():
    from app.rag.ingestor import ingest_document
    db = AsyncMock()
    result = await ingest_document("doc1", "Test", "", db)
    assert result["chunks_created"] == 0
    assert "error" in result


@pytest.mark.asyncio
async def test_ingest_creates_chunks_and_commits():
    from app.rag.ingestor import ingest_document

    fake_embedding = [0.1] * 768

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(rowcount=0))
    db.add = MagicMock()
    db.commit = AsyncMock()

    text = "\n\n".join([f"Parrafo {i}: " + "texto relevante " * 20 for i in range(5)])

    with patch("app.rag.ingestor.embed_batch", AsyncMock(return_value=[fake_embedding] * 20)):
        result = await ingest_document("ley_alquileres", "Ley de Alquileres", text, db)

    assert result["chunks_created"] >= 1
    assert db.commit.await_count == 1
    assert db.add.call_count == result["chunks_created"]


@pytest.mark.asyncio
async def test_ingest_replace_deletes_old_chunks():
    from app.rag.ingestor import ingest_document

    fake_embedding = [0.0] * 768
    mock_delete_result = MagicMock(rowcount=3)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_delete_result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    text = "Contenido de prueba para reemplazo de chunks." * 10

    with patch("app.rag.ingestor.embed_batch", AsyncMock(return_value=[fake_embedding] * 10)):
        result = await ingest_document("doc_replace", "Doc", text, db, replace=True)

    assert result["chunks_replaced"] == 3
    db.execute.assert_awaited()  # DELETE was called


@pytest.mark.asyncio
async def test_ingest_no_replace_skips_delete():
    from app.rag.ingestor import ingest_document

    fake_embedding = [0.0] * 768
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    text = "Solo insertar sin borrar." * 20

    with patch("app.rag.ingestor.embed_batch", AsyncMock(return_value=[fake_embedding] * 10)):
        result = await ingest_document("doc_append", "Doc", text, db, replace=False)

    assert result["chunks_replaced"] == 0
    db.execute.assert_not_awaited()  # no DELETE
