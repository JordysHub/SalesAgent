# scripts/debug_parse.py
import argparse
import os
import sys

from src.utils.ingestion.parser import parse_document

parser = argparse.ArgumentParser(description="Debug document parsing")
parser.add_argument("--file", type=str, required=True, help="Filename in data/documents/")
args = parser.parse_args()

DOCS_PATH = os.getenv("DOCS_PATH", "./data/documents")
filepath = os.path.join(DOCS_PATH, args.file)
ext = os.path.splitext(args.file)[1].lower()

if not os.path.exists(filepath):
    print(f"File not found: {filepath}")
    sys.exit(1)

doc = {"path": filepath, "filename": args.file, "extension": ext}
chunks = parse_document(doc)

print(f"\n{args.file}")
print(f"Total chunks: {len(chunks)}")
print("---")

for i, chunk in enumerate(chunks):
    print(f"\nChunk {i + 1} | type: {chunk['content_type']} | chars: {len(chunk['text'])}")
    print(chunk["text"][:300])
    print("---")