# rag/ingestion/chunker.py
import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """
    Split text into token-based chunks with overlap.
    Returns list of text chunks.
    """
    tokens = ENCODING.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = ENCODING.decode(chunk_tokens)
        chunks.append(chunk_text)
        if end == len(tokens):
            break
        start += chunk_size - overlap

    return chunks