# scripts/inspect_chunks.py
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from collections import Counter

load_dotenv()

client = QdrantClient(url=os.getenv("QDRANT_URL"),
                      api_key=os.getenv("QDRANT_API_KEY"))

results = client.scroll(
    collection_name="rag_docs",
    limit=1000,
    with_payload=True,
    with_vectors=False
)[0]

sources = Counter([r.payload.get("filename") for r in results])
print(f"\nTotal chunks: {sum(sources.values())}")
print("\nChunks per source:")
for source, count in sources.most_common():
    print(f"  {source}: {count} chunks")
