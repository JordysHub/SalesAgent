# rag/retrieval/retriever.py
from rag.ingestion.embedder import embed_texts
from rag.store.vector_store import get_collection
import os


def query_rag(
    question: str,
    top_k: int = 5,
    chroma_path: str = "./chroma_db",
    collection_name: str = "rag_docs",
) -> list[dict]:
    """
    Main retrieval interface for the agent.
    Returns list of dicts: {text, source, score}
    """
    collection = get_collection(chroma_path, collection_name)

    query_embedding = embed_texts([question])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "text": doc,
            "source": meta.get("filename", "unknown"),
            "relative_path": meta.get("relative_path", ""),
            "score": round(1 - dist, 4),  # cosine similarity
        })

    return output
