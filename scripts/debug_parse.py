# scripts/debug_parse.py
from src.utils.ingestion.parser import parse_document
import os
import sys
sys.path.insert(0, os.path.abspath("."))


docs = [
    {"path": "data/documents/proposal_cloud_migration.docx",
        "filename": "proposal_cloud_migration.docx", "extension": ".docx"},
    {"path": "data/documents/proposal_ai_customer.docx",
        "filename": "proposal_ai_customer.docx", "extension": ".docx"},
    {"path": "data/documents/proposal_cybersecurity.docx",
        "filename": "proposal_cybersecurity.docx", "extension": ".docx"},
]

for doc in docs:
    text = parse_document(doc)
    print(f"\n{doc['filename']}")
    print(f"Characters extracted: {len(text)}")
    print(f"First 500 chars:\n{text[:500]}")
    print("---")
