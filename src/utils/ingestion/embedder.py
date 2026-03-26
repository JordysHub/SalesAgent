# src/utils/ingestion/embedder.py
from fastembed import TextEmbedding
from src.config import EMBED_MODEL

_model = None


def get_model():
    global _model
    if _model is None:
        print("[embedder] Loading fastembed model...")
        _model = TextEmbedding(EMBED_MODEL)
    return _model


def embed_texts(texts: list[str], model_name: str = None) -> list[list[float]]:
    model = get_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]
