# rag/ingestion/parser.py
from pathlib import Path


def parse_document(file_meta: dict) -> str:
    """
    Parse a document to raw text based on its extension.
    Returns extracted text as a single string.
    """
    ext = file_meta["extension"]
    path = file_meta["path"]

    if ext == ".txt" or ext == ".md":
        return _parse_text(path)
    elif ext == ".pdf":
        return _parse_pdf(path)
    elif ext == ".docx":
        return _parse_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _parse_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _parse_pdf(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def _parse_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])