# rag/store/vector_store.py
import chromadb
from chromadb.config import Settings

_client = None
_collection = None


def get_collection(chroma_path: str, collection_name: str = "rag_docs"):
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=chroma_path)
        _collection = _client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(
    collection,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: list[dict],
    ids: list[str],
):
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadata,
        ids=ids,
    )
    print(f"[store] Added {len(chunks)} chunk(s) to collection.")


def collection_count(collection) -> int:
    return collection.count()
