# src/utils/ingestion/chunker.py
import re
import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def split_into_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs on double newlines."""
    paragraphs = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
    split_by: str = "sentence",  # "sentence", "paragraph", or "token"
) -> list[str]:
    """
    Split text into chunks with overlap.

    split_by options:
    - "sentence" : respects sentence boundaries (recommended)
    - "paragraph": respects paragraph boundaries (good for structured docs)
    - "token"    : raw token splitting (original behaviour, cuts mid-sentence)
    """
    if split_by == "token":
        return _chunk_by_tokens(text, chunk_size, overlap)
    elif split_by == "paragraph":
        units = split_into_paragraphs(text)
    else:
        units = split_into_sentences(text)

    return _chunk_by_units(units, chunk_size, overlap)


def _chunk_by_units(units: list[str], chunk_size: int, overlap: int) -> list[str]:
    """
    Greedily pack sentences/paragraphs into chunks under chunk_size tokens.
    Overlap is achieved by re-including the last N tokens of the previous chunk.
    """
    chunks = []
    current_units = []
    current_tokens = 0

    for unit in units:
        unit_tokens = count_tokens(unit)

        # If a single unit exceeds chunk_size, split it by tokens
        if unit_tokens > chunk_size:
            if current_units:
                chunks.append(" ".join(current_units))
                current_units = []
                current_tokens = 0
            sub_chunks = _chunk_by_tokens(unit, chunk_size, overlap)
            chunks.extend(sub_chunks)
            continue

        if current_tokens + unit_tokens > chunk_size:
            # Save current chunk
            chunks.append(" ".join(current_units))

            # Build overlap: walk back from end of current_units
            overlap_units = []
            overlap_token_count = 0
            for u in reversed(current_units):
                u_tokens = count_tokens(u)
                if overlap_token_count + u_tokens > overlap:
                    break
                overlap_units.insert(0, u)
                overlap_token_count += u_tokens

            current_units = overlap_units
            current_tokens = overlap_token_count

        current_units.append(unit)
        current_tokens += unit_tokens

    if current_units:
        chunks.append(" ".join(current_units))

    return chunks


def _chunk_by_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Original token-based chunking — fallback for oversized units."""
    tokens = ENCODING.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(ENCODING.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start += chunk_size - overlap
    return chunks