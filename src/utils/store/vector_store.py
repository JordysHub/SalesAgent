# src/utils/store/vector_store.py
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from src.config import VECTOR_SIZE, QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

_client = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return _client


def get_collection():
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"[store] Created collection: {COLLECTION_NAME}")
    return client


def add_chunks(chunks, embeddings, metadata, ids):
    client = get_collection()
    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, id_)),
            vector=embedding,
            payload={**meta, "text": chunk}
        )
        for chunk, embedding, meta, id_ in zip(chunks, embeddings, metadata, ids)
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"[store] Upserted {len(points)} chunk(s)")


def collection_count():
    client = get_client()
    return client.count(collection_name=COLLECTION_NAME).count
