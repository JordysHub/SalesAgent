# rag/connector/local_connector.py
import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def load_documents(docs_path: str) -> list[dict]:
    """
    Walk the local documents directory and return a list of file metadata dicts.
    Each dict contains: path, filename, extension.
    """
    docs_dir = Path(docs_path)
    if not docs_dir.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_path}")

    documents = []
    for file_path in docs_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.append({
                "path": str(file_path),
                "filename": file_path.name,
                "extension": file_path.suffix.lower(),
                "relative_path": str(file_path.relative_to(docs_dir)),
            })

    print(f"[connector] Found {len(documents)} document(s) in {docs_path}")
    return documents