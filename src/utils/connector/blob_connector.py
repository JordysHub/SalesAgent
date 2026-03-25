# src/utils/connector/blob_connector.py
import os
import json
from datetime import timezone
from azure.storage.blob import BlobServiceClient

STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "ragdocuments1337")
STORAGE_KEY = os.getenv("AZURE_STORAGE_KEY")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "documents")
REGISTRY_BLOB = "registry.json"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def get_blob_service() -> BlobServiceClient:
    return BlobServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=STORAGE_KEY
    )


def list_blobs() -> list[dict]:
    """List all supported documents in the container with metadata."""
    service = get_blob_service()
    container = service.get_container_client(CONTAINER_NAME)
    blobs = []
    for blob in container.list_blobs():
        ext = os.path.splitext(blob.name)[1].lower()
        if ext in SUPPORTED_EXTENSIONS and blob.name != REGISTRY_BLOB:
            last_modified = blob.last_modified.astimezone(
                timezone.utc).isoformat()
            blobs.append({
                "filename": blob.name,
                "extension": ext,
                "last_modified": last_modified,
                "size": blob.size,
            })
    print(f"[blob] Found {len(blobs)} document(s) in blob")
    return blobs


def download_blob(filename: str, dest_path: str):
    """Download a single blob to a local path."""
    service = get_blob_service()
    blob_client = service.get_blob_client(
        container=CONTAINER_NAME, blob=filename)
    with open(dest_path, "wb") as f:
        f.write(blob_client.download_blob().readall())


def load_registry() -> dict:
    """Load registry.json from blob. Returns empty dict if not found."""
    service = get_blob_service()
    blob_client = service.get_blob_client(
        container=CONTAINER_NAME, blob=REGISTRY_BLOB)
    try:
        data = blob_client.download_blob().readall()
        registry = json.loads(data)
        print(f"[registry] Loaded registry with {len(registry)} entries")
        return registry
    except Exception:
        print("[registry] No registry found, starting fresh")
        return {}


def save_registry(registry: dict):
    """Upload registry.json to blob."""
    service = get_blob_service()
    blob_client = service.get_blob_client(
        container=CONTAINER_NAME, blob=REGISTRY_BLOB)
    blob_client.upload_blob(
        json.dumps(registry, indent=2).encode(),
        overwrite=True
    )
    print(f"[registry] Saved registry with {len(registry)} entries")
