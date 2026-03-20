# main.py — ingestion pipeline
import os
import hashlib
from dotenv import load_dotenv

from src.utils.connector.local_connector import load_documents
from src.utils.ingestion.parser import parse_document
from src.utils.ingestion.chunker import chunk_text
from src.utils.ingestion.embedder import embed_texts
from src.utils.store.vector_store import add_chunks, collection_count

load_dotenv()

DOCS_PATH = os.getenv("DOCS_PATH", "./documents")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 512))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))


def make_chunk_id(filename: str, chunk_index: int) -> str:
    raw = f"{filename}::chunk::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest():
    print("=== RAG Ingestion Pipeline ===")

    documents = load_documents(DOCS_PATH)

    if not documents:
        print("No documents found. Add files to ./documents and re-run.")
        return

    total_chunks = 0

    for doc in documents:
        print(f"\n[ingest] Processing: {doc['filename']}")

        try:
            text = parse_document(doc)
        except Exception as e:
            print(f"[ingest] Failed to parse {doc['filename']}: {e}")
            continue

        if not text.strip():
            print(f"[ingest] Empty content, skipping: {doc['filename']}")
            continue

        chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        print(f"[ingest] {len(chunks)} chunks from {doc['filename']}")

        embeddings = embed_texts(chunks, model_name=EMBED_MODEL)

        ids = [make_chunk_id(doc["filename"], i) for i in range(len(chunks))]
        metadata = [
            {
                "filename": doc["filename"],
                "relative_path": doc["relative_path"],
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]

        add_chunks(chunks, embeddings, metadata, ids)
        total_chunks += len(chunks)

    print(f"\n=== Done. Total chunks in store: {collection_count()} ===")


if __name__ == "__main__":
    ingest()
