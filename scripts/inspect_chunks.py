# scripts/inspect_chunks.py
import argparse
import os
from collections import Counter, defaultdict

from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

parser = argparse.ArgumentParser(description="Inspect Qdrant chunks")
parser.add_argument("--duplicates", action="store_true", help="Check for duplicate chunks")
parser.add_argument("--file", type=str, default=None, help="Filter by filename")
args = parser.parse_args()

client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

results = client.scroll(
    collection_name="rag_docs", limit=1000, with_payload=True, with_vectors=False
)[0]

if args.file:
    results = [r for r in results if r.payload.get("filename") == args.file]

if not results:
    print("No chunks found.")
    exit()

# group by filename
by_file = defaultdict(list)
for r in results:
    by_file[r.payload.get("filename")].append(r)

print(f"\nTotal chunks: {len(results)}")
print(f"Total sources: {len(by_file)}")
print("\nChunks per source:")

for filename, chunks in sorted(by_file.items()):
    payload = chunks[0].payload
    ingested_at = payload.get("ingested_at", "unknown")
    chunk_size = payload.get("chunk_size", "unknown")
    chunk_overlap = payload.get("chunk_overlap", "unknown")
    print(f"\n  {filename}")
    print(f"    chunks      : {len(chunks)}")
    print(f"    chunk_size  : {chunk_size}")
    print(f"    overlap     : {chunk_overlap}")
    print(f"    ingested_at : {ingested_at}")

if args.duplicates:
    print("\nDuplicate check:")
    seen_ids = Counter([r.id for r in results])
    seen_keys = Counter(
        [f"{r.payload.get('filename')}::chunk::{r.payload.get('chunk_index')}" for r in results]
    )
    duplicates = {k: v for k, v in seen_keys.items() if v > 1}
    if duplicates:
        print(f"  {len(duplicates)} duplicate(s) found:")
        for k, v in duplicates.items():
            print(f"    {k} — {v}x")
    else:
        print("  No duplicates found.")
