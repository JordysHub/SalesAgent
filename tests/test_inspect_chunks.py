# tests/test_inspect_chunks.py
import os
from dotenv import load_dotenv
from src.utils.store.vector_store import get_collection

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

collection = get_collection(CHROMA_PATH)

results = collection.get(limit=5, include=["documents", "metadatas"])

print(f"Total chunks in store: {collection.count()}\n")

for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"]), 1):
    print(f"--- Chunk {i} ---")
    print(f"Source : {meta.get('filename')}")
    print(f"Index  : {meta.get('chunk_index')}")
    print(f"Text   : {doc[:300]}")
    print()
