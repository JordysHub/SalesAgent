# src/utils/retrieval/retriever.py
import os
from src.utils.ingestion.embedder import embed_texts
from src.utils.store.vector_store import get_client, COLLECTION_NAME


def query_rag(question: str, top_k: int = 5) -> list[dict]:
    client = get_client()
    query_embedding = embed_texts([question])[0]

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=top_k,
        with_payload=True,
    ).points

    return [
        {
            "text": r.payload.get("text", ""),
            "source": r.payload.get("filename", "unknown"),
            "relative_path": r.payload.get("relative_path", ""),
            "score": round(r.score, 4),
        }
        for r in results
    ]
