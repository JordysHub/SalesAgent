# scripts/debug_parse.py
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from src.utils.ingestion.parser import parse_document

all_docs = [
    {"path": "data/documents/proposal_cloud_migration.docx",
     "filename": "proposal_cloud_migration.docx", "extension": ".docx"},
    {"path": "data/documents/proposal_ai_customer.docx",
     "filename": "proposal_ai_customer.docx", "extension": ".docx"},
    {"path": "data/documents/proposal_cybersecurity.docx",
     "filename": "proposal_cybersecurity.docx", "extension": ".docx"},
]

parser = argparse.ArgumentParser(description="Debug document parsing")
parser.add_argument("--file", type=str, default=None,
                    help="Filename to parse (e.g. proposal_cloud_migration.docx). Parses all if omitted.")
args = parser.parse_args()

docs = [d for d in all_docs if d["filename"] == args.file] if args.file else all_docs

if not docs:
    print(f"File not found in known documents: {args.file}")
    sys.exit(1)

for doc in docs:
    text = parse_document(doc)
    print(f"\n{doc['filename']}")
    print(f"Characters extracted: {len(text)}")
    print(f"First 500 chars:\n{text[:500]}")
    print("---")