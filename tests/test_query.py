# tests/test_query.py
from src.utils.retrieval.retriever import query_rag
from dotenv import load_dotenv
import os
import sys
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()


CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

question = "What is this document about?"  # replace with your test query

print(f"\nQuery: {question}\n")
results = query_rag(question, top_k=3, chroma_path=CHROMA_PATH)

for i, r in enumerate(results, 1):
    print(f"--- Result {i} ---")
    print(f"Source : {r['source']}")
    print(f"Score  : {r['score']}")
    print(f"Text   : {r['text'][:300]}...")
    print()
