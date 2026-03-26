import os
import json
from datetime import timezone
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from src.config import STORAGE_ACCOUNT, STORAGE_KEY, CONTAINER_NAME

load_dotenv()


REGISTRY_BLOB = "registry.json"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def get_blob_service() -> BlobServiceClient:
    return BlobServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=STORAGE_KEY
    )


def list_blobs() -> list[dict]:
    service = get_blob_service()
    container = service.get_container_client(CONTAINER_NAME)
    blobs = []
    for blob in container.list_blobs():
        ext = os.path.splitext(blob.name)[1].lower()
        if ext in SUPPORTED_EXTENSIONS and blob.name != REGISTRY_BLOB:
            if blob.name.startswith("rfp-inputs/") or blob.name.startswith("rfp-outputs/"):
                continue
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
    service = get_blob_service()
    blob_client = service.get_blob_client(
        container=CONTAINER_NAME, blob=filename)
    with open(dest_path, "wb") as f:
        f.write(blob_client.download_blob().readall())


def load_registry() -> dict:
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
    service = get_blob_service()
    blob_client = service.get_blob_client(
        container=CONTAINER_NAME, blob=REGISTRY_BLOB)
    blob_client.upload_blob(
        json.dumps(registry, indent=2).encode(),
        overwrite=True
    )
    print(f"[registry] Saved registry with {len(registry)} entries")
