# src/utils/ingestion/embedder.py
from sentence_transformers import SentenceTransformer

_model = None


def get_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[embedder] Loading model: {model_name}")
        _model = SentenceTransformer(model_name)
    return _model


def embed_texts(texts: list[str], model_name: str = "all-MiniLM-L6-v2") -> list[list[float]]:
    model = get_model(model_name)
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()