# scripts/delete_source.py
import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PayloadSchemaType
from collections import defaultdict

load_dotenv()

client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

def get_all_sources():
    results = client.scroll(
        collection_name="rag_docs",
        limit=1000,
        with_payload=True,
        with_vectors=False
    )[0]
    return list({r.payload.get("filename") for r in results if r.payload.get("filename")})

def delete_source(source: str):
    client.create_payload_index(
        collection_name="rag_docs",
        field_name="filename",
        field_schema=PayloadSchemaType.KEYWORD
    )
    client.delete(
        collection_name="rag_docs",
        points_selector=Filter(
            must=[FieldCondition(key="filename", match=MatchValue(value=source))]
        )
    )
    print(f"Deleted: {source}")

if len(sys.argv) < 2:
    print("Usage:")
    print("  python scripts/delete_source.py <filename>   # delete one")
    print("  python scripts/delete_source.py --all        # delete all")
    sys.exit(1)

if sys.argv[1] == "--all":
    sources = get_all_sources()
    if not sources:
        print("No sources found in store.")
        sys.exit(0)
    print(f"Found {len(sources)} source(s):")
    for s in sources:
        print(f"  {s}")
    confirm = input(f"\nDelete all {len(sources)} source(s)? [y/N]: ")
    if confirm.lower() != "y":
        print("Aborted.")
        sys.exit(0)
    for source in sources:
        delete_source(source)
    print(f"\nDone. Deleted {len(sources)} source(s).")
else:
    source = sys.argv[1]
    confirm = input(f"Delete all chunks for '{source}'? [y/N]: ")
    if confirm.lower() != "y":
        print("Aborted.")
        sys.exit(0)
    delete_source(source)