# src/ingest.py
import hashlib
import os
import tempfile
from datetime import datetime, timezone

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, PayloadSchemaType

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBED_MODEL,
    QDRANT_API_KEY,
    QDRANT_URL,
)
from src.utils.connector.blob_connector import (
    download_blob,
    list_blobs,
    load_registry,
    save_registry,
)
from src.utils.ingestion.chunker import chunk_text
from src.utils.ingestion.embedder import embed_texts
from src.utils.ingestion.parser import parse_document
from src.utils.store.vector_store import add_chunks, collection_count

load_dotenv()


def make_chunk_id(filename: str, chunk_index: int) -> str:
    raw = f"{filename}::chunk::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def delete_source(client: QdrantClient, filename: str):
    client.create_payload_index(
        collection_name="rag_docs", field_name="filename", field_schema=PayloadSchemaType.KEYWORD
    )
    client.delete(
        collection_name="rag_docs",
        points_selector=Filter(
            must=[FieldCondition(key="filename", match=MatchValue(value=filename))]
        ),
    )


def ingest():
    print("=== RAG Ingestion Pipeline ===")

    blobs = list_blobs()
    if not blobs:
        print("No documents found in blob.")
        return

    registry = load_registry()
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    ingested_count = 0
    skipped_count = 0
    ingested_at = datetime.now(timezone.utc).isoformat()

    for blob in blobs:
        filename = blob["filename"]
        last_modified = blob["last_modified"]

        # check registry
        entry = registry.get(filename)
        if (
            entry
            and entry.get("last_modified") == last_modified
            and entry.get("chunk_size") == CHUNK_SIZE
            and entry.get("chunk_overlap") == CHUNK_OVERLAP
        ):
            print(f"[ingest] Skipping (unchanged): {filename}")
            skipped_count += 1
            continue

        print(f"\n[ingest] Processing: {filename}")

        # download to temp file
        with tempfile.NamedTemporaryFile(suffix=blob["extension"], delete=False) as tmp:
            tmp_path = tmp.name
        download_blob(filename, tmp_path)

        # parse
        try:
            doc = {"path": tmp_path, "filename": filename, "extension": blob["extension"]}
            text = parse_document(doc)
        except Exception as e:
            print(f"[ingest] Failed to parse {filename}: {e}")
            os.unlink(tmp_path)
            continue
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if not text.strip():
            print(f"[ingest] Empty content, skipping: {filename}")
            continue

        # delete old chunks
        delete_source(qdrant, filename)

        # chunk + embed
        chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        chunk_count = len(chunks)
        print(f"[ingest] {chunk_count} chunks from {filename}")

        embeddings = embed_texts(chunks, model_name=EMBED_MODEL)
        ids = [make_chunk_id(filename, i) for i in range(chunk_count)]
        metadata = [
            {
                "filename": filename,
                "relative_path": filename,
                "chunk_index": i,
                "chunk_count": chunk_count,
                "chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
                "ingested_at": ingested_at,
            }
            for i in range(chunk_count)
        ]

        add_chunks(chunks, embeddings, metadata, ids)

        # update registry
        registry[filename] = {
            "last_modified": last_modified,
            "ingested_at": ingested_at,
            "chunk_count": chunk_count,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
        }
        ingested_count += 1

    save_registry(registry)

    print(
        f"\n=== Done. Ingested: {ingested_count} | Skipped: {skipped_count} | Total chunks: {collection_count()} ==="
    )


if __name__ == "__main__":
    ingest()
