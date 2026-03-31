# scripts/ingest_source.py
import argparse
import hashlib
import os
import sys
import tempfile
from datetime import datetime, timezone

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, PayloadSchemaType

load_dotenv()

from src.utils.connector.blob_connector import (
    get_blob_service,
    load_registry,
    save_registry,
)
from src.utils.ingestion.chunker import chunk_text
from src.utils.ingestion.embedder import embed_texts
from src.utils.ingestion.parser import parse_document
from src.utils.store.vector_store import add_chunks

EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 256))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 40))
STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "ragdocuments1337")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "documents")

parser = argparse.ArgumentParser(description="Ingest a single file from Azure Blob")
parser.add_argument(
    "--file", type=str, required=True, help="Filename in blob (e.g. proposal_cloud_migration.docx)"
)
args = parser.parse_args()

filename = args.file
ext = os.path.splitext(filename)[1].lower()

# connect to blob
print("[ingest_source] Connecting to blob storage...")
blob_service = get_blob_service()
blob_client = blob_service.get_blob_client(container=CONTAINER_NAME, blob=filename)

if not blob_client.exists():
    print(f"[ingest_source] File not found in blob: {filename}")
    sys.exit(1)

# get blob last_modified
props = blob_client.get_blob_properties()
last_modified = props.last_modified.astimezone(timezone.utc).isoformat()

# download to temp file
with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
    tmp_path = tmp.name
print(f"[ingest_source] Downloading {filename} from blob...")
with open(tmp_path, "wb") as f:
    f.write(blob_client.download_blob().readall())

# delete existing chunks
print(f"[ingest_source] Deleting existing chunks for: {filename}")
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
client.create_payload_index(
    collection_name="rag_docs", field_name="filename", field_schema=PayloadSchemaType.KEYWORD
)
client.delete(
    collection_name="rag_docs",
    points_selector=Filter(
        must=[FieldCondition(key="filename", match=MatchValue(value=filename))]
    ),
)

# parse — returns list of content chunks
doc = {"path": tmp_path, "filename": filename, "extension": ext}
content_chunks = parse_document(doc)
os.unlink(tmp_path)

if not content_chunks:
    print("[ingest_source] Empty content, aborting.")
    sys.exit(1)

# chunk text content, keep table/image chunks as-is
all_chunks = []
for content_chunk in content_chunks:
    if content_chunk["content_type"] == "text":
        sub_chunks = chunk_text(
            content_chunk["text"], chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP
        )
        for sub in sub_chunks:
            all_chunks.append({"text": sub, "content_type": "text"})
    else:
        all_chunks.append(content_chunk)

chunk_count = len(all_chunks)
print(f"[ingest_source] {chunk_count} chunks created")

texts = [c["text"] for c in all_chunks]
embeddings = embed_texts(texts, model_name=EMBED_MODEL)
ingested_at = datetime.now(timezone.utc).isoformat()


def make_chunk_id(filename: str, chunk_index: int) -> str:
    raw = f"{filename}::chunk::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


ids = [make_chunk_id(filename, i) for i in range(chunk_count)]
metadata = [
    {
        "filename": filename,
        "relative_path": filename,
        "chunk_index": i,
        "chunk_count": chunk_count,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "content_type": all_chunks[i]["content_type"],
        "ingested_at": ingested_at,
    }
    for i in range(chunk_count)
]

add_chunks(texts, embeddings, metadata, ids)

# update registry
registry = load_registry()
registry[filename] = {
    "last_modified": last_modified,
    "ingested_at": ingested_at,
    "chunk_count": chunk_count,
    "chunk_size": CHUNK_SIZE,
    "chunk_overlap": CHUNK_OVERLAP,
}
save_registry(registry)

print(f"[ingest_source] Done. Upserted {chunk_count} chunks for {filename}")
print(f"[ingest_source] Registry updated for {filename}")