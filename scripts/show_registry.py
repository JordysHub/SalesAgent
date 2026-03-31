from dotenv import load_dotenv

from src.utils.connector.blob_connector import load_registry

load_dotenv()

registry = load_registry()

if not registry:
    print("Registry is empty.")
else:
    print(f"\nRegistry — {len(registry)} entries:\n")
    for filename, entry in sorted(registry.items()):
        print(f"  {filename}")
        print(f"    last_modified : {entry.get('last_modified', 'unknown')}")
        print(f"    ingested_at   : {entry.get('ingested_at', 'unknown')}")
        print(f"    chunk_count   : {entry.get('chunk_count', 'unknown')}")
        print(f"    chunk_size    : {entry.get('chunk_size', 'unknown')}")
        print(f"    chunk_overlap : {entry.get('chunk_overlap', 'unknown')}")
        print()
