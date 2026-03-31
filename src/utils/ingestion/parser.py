# src/utils/ingestion/parser.py
"""
Document Parser — Ingestion Step 1
Parses documents into a list of content chunks, each with a content_type.
Supported content types: text, table, image.
- text: plain paragraphs
- table: markdown-formatted table (one chunk per table — Decision #5)
- image: vision LLM description of embedded image
Returns list[dict] with keys: text, content_type
"""
import base64
import io


def parse_document(file_meta: dict) -> list[dict]:
    """
    Parse a document into a list of chunks with content_type metadata.
    Each chunk is a dict: {"text": str, "content_type": str}
    """
    ext = file_meta["extension"]
    path = file_meta["path"]

    if ext in (".txt", ".md"):
        return _parse_text(path)
    elif ext == ".pdf":
        return _parse_pdf(path)
    elif ext == ".docx":
        return _parse_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _parse_text(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [{"text": f.read(), "content_type": "text"}]


def _parse_pdf(path: str) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return [{"text": text, "content_type": "text"}]


def _parse_docx(path: str) -> list[dict]:
    from docx import Document

    doc = Document(path)
    chunks = []

    # --- Text: paragraphs ---
    paragraph_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraph_parts.append(para.text.strip())
    if paragraph_parts:
        chunks.append({"text": "\n".join(paragraph_parts), "content_type": "text"})

    # --- Tables: one chunk per table as markdown (Decision #5) ---
    for table in doc.tables:
        rows = []
        for i, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                # add markdown header separator after first row
                rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
        table_text = "\n".join(rows)
        if table_text.strip():
            chunks.append({"text": table_text, "content_type": "table"})

    # --- Images: extract and describe via vision LLM ---
    image_chunks = _extract_and_describe_images(doc)
    chunks.extend(image_chunks)

    return chunks


def _extract_and_describe_images(doc) -> list[dict]:
    """
    Extract embedded images from a DOCX document and describe each
    using the configured vision LLM. Returns list of text chunks.
    """
    from src.utils.llm_client import chat_vision

    chunks = []
    seen = set()

    for rel in doc.part.rels.values():
        if "image" not in rel.reltype:
            continue

        try:
            image_part = rel.target_part
            image_bytes = image_part.blob
            content_type = image_part.content_type  # e.g. image/png, image/jpeg

            # deduplicate by content hash
            image_hash = hash(image_bytes)
            if image_hash in seen:
                continue
            seen.add(image_hash)

            # skip tiny images (icons, bullets) under 5KB
            if len(image_bytes) < 5000:
                continue

            description = chat_vision(
                image_bytes=image_bytes,
                media_type=content_type,
                prompt=(
                    "You are analysing an image extracted from a consulting proposal document. "
                    "Describe the content in detail — if it is a diagram, describe the components "
                    "and relationships. If it is a chart, describe the data and trends. "
                    "If it is a table or matrix, describe the structure and values. "
                    "Write in plain prose suitable for use in a searchable knowledge base."
                ),
            )

            if description:
                chunks.append({"text": description, "content_type": "image"})
                print(f"[parser] Image described: {len(description)} chars")

        except Exception as e:
            print(f"[parser] Skipping image: {e}")
            continue

    return chunks