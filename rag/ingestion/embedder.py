# rag/ingestion/embedder.py
import chromadb.utils.embedding_functions as ef

_embed_fn = None

def get_embed_fn():
    global _embed_fn
    if _embed_fn is None:
        _embed_fn = ef.DefaultEmbeddingFunction()
    return _embed_fn

def embed_texts(texts: list[str], model_name: str = None) -> list[list[float]]:
    return get_embed_fn()(texts)