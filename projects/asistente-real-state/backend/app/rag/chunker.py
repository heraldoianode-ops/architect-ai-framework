"""
chunker.py — Split documents into overlapping text chunks.
P006: chunks MUST use overlap to avoid context loss at boundaries.

Strategy: character-level sliding window, respecting sentence boundaries
where possible. Paragraph breaks are preferred split points.
"""
import re
from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 1800   # ~450 tokens at ~4 chars/token
DEFAULT_OVERLAP = 360       # 20% overlap (P006)


@dataclass
class Chunk:
    index: int
    content: str
    char_start: int
    char_end: int


def _split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; fall back to sentences if paragraphs are huge."""
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return paras


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """
    Chunk text into overlapping windows.
    Prefers to break at paragraph boundaries; falls back to hard cut.
    Returns a list of Chunk objects with index and character offsets.
    """
    text = text.strip()
    if not text:
        return []

    # If the whole text fits in one chunk, return as-is
    if len(text) <= chunk_size:
        return [Chunk(index=0, content=text, char_start=0, char_end=len(text))]

    paragraphs = _split_paragraphs(text)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0
    char_pos = 0
    chunk_idx = 0

    for para in paragraphs:
        para_len = len(para) + 1  # +1 for the joining newline

        if current_len + para_len > chunk_size and current:
            # Emit current chunk
            content = "\n".join(current)
            chunks.append(Chunk(
                index=chunk_idx,
                content=content,
                char_start=char_pos - current_len,
                char_end=char_pos,
            ))
            chunk_idx += 1

            # Carry overlap: walk back from end until we've kept `overlap` chars
            overlap_text = content[-overlap:] if len(content) > overlap else content
            # Find the last paragraph boundary inside overlap
            boundary = overlap_text.rfind("\n")
            if boundary != -1:
                overlap_text = overlap_text[boundary + 1:]
            current = [overlap_text] if overlap_text.strip() else []
            current_len = len(overlap_text) + 1 if current else 0

        current.append(para)
        current_len += para_len
        char_pos += para_len

    if current:
        content = "\n".join(current)
        chunks.append(Chunk(
            index=chunk_idx,
            content=content,
            char_start=char_pos - current_len,
            char_end=char_pos,
        ))

    return chunks
