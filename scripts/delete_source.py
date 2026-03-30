# scripts/delete_source.py
import os
import sys

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, PayloadSchemaType

from src.utils.connector.blob_connector import load_registry, save_registry

load_dotenv()

client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))


def get_all_sources():
    results = client.scroll(
        collection_name="rag_docs", limit=1000, with_payload=True, with_vectors=False
    )[0]
    return list({r.payload.get("filename") for r in results if r.payload.get("filename")})


def delete_source(source: str):
    client.create_payload_index(
        collection_name="rag_docs", field_name="filename", field_schema=PayloadSchemaType.KEYWORD
    )
    client.delete(
        collection_name="rag_docs",
        points_selector=Filter(
            must=[FieldCondition(key="filename", match=MatchValue(value=source))]
        ),
    )
    print(f"Deleted chunks: {source}")


def remove_from_registry(sources: list[str]):
    registry = load_registry()
    removed = []
    for source in sources:
        if source in registry:
            del registry[source]
            removed.append(source)
    if removed:
        save_registry(registry)
        for s in removed:
            print(f"Removed from registry: {s}")
    else:
        print("No registry entries found for deleted sources.")


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
    remove_from_registry(sources)
    print(f"\nDone. Deleted {len(sources)} source(s).")
else:
    source = sys.argv[1]
    confirm = input(f"Delete all chunks for '{source}'? [y/N]: ")
    if confirm.lower() != "y":
        print("Aborted.")
        sys.exit(0)
    delete_source(source)
    remove_from_registry([source])
