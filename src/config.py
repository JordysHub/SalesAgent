# src/config.py
"""
Central configuration for all tunable pipeline parameters.
Adjust these values to tune retrieval quality and answer generation behaviour.
All values can be overridden via environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Embedding & Retrieval ────────────────────────────────────────────────────
EMBED_MODEL         = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE          = int(os.getenv("CHUNK_SIZE", 256))
CHUNK_OVERLAP       = int(os.getenv("CHUNK_OVERLAP", 40))
TOP_K               = int(os.getenv("TOP_K", 8))
MIN_SCORE           = float(os.getenv("MIN_SCORE", 0.25))
LOW_CONFIDENCE      = float(os.getenv("LOW_CONFIDENCE", 0.3))

# ─── LLM ─────────────────────────────────────────────────────────────────────
GROQ_MODEL          = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
TEMPERATURE         = float(os.getenv("TEMPERATURE", 0.0))

# ─── QA Verifier ─────────────────────────────────────────────────────────────
QA_MAX_RETRIES      = int(os.getenv("QA_MAX_RETRIES", 2))
QA_RETRY_TOP_K      = int(os.getenv("QA_RETRY_TOP_K", 3))  # added to TOP_K on retry

# ─── Ingestion ────────────────────────────────────────────────────────────────
DOCS_PATH           = os.getenv("DOCS_PATH", "./data/documents")

# ─── Azure Storage ────────────────────────────────────────────────────────────
STORAGE_ACCOUNT     = os.getenv("AZURE_STORAGE_ACCOUNT", "ragdocuments1337")
STORAGE_KEY         = os.getenv("AZURE_STORAGE_KEY")
CONTAINER_NAME      = os.getenv("AZURE_CONTAINER_NAME", "documents")
SAS_EXPIRY_DAYS     = int(os.getenv("SAS_EXPIRY_DAYS", 7))

# ─── Qdrant ───────────────────────────────────────────────────────────────────
QDRANT_URL          = os.getenv("QDRANT_URL")
QDRANT_API_KEY      = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME     = "rag_docs"
VECTOR_SIZE         = 384  # must match EMBED_MODEL output dimension