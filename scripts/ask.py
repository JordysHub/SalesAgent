# scripts/ask.py
import argparse
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

parser = argparse.ArgumentParser(description="Query the RAG system")
parser.add_argument("question", type=str, help="Question to ask")
parser.add_argument("--top-k", type=int, default=None,
                    help="Number of chunks to retrieve (default: uses API default)")
parser.add_argument("--show-chunks", action="store_true",
                    help="Show retrieved chunks")
parser.add_argument("--endpoint", type=str, default="answer",
                    choices=["answer", "query"], help="Endpoint to call")
args = parser.parse_args()

payload = {
    "question": args.question,
    "include_chunks": args.show_chunks
}
if args.top_k is not None:
    payload["top_k"] = args.top_k

response = requests.post(
    f"{API_URL}/{args.endpoint}",
    json=payload
)

if not response.text.strip():
    print("Error: empty response from API. Is uvicorn running and the database ingested?")
    exit(1)

data = response.json()

print(f"\nQuestion: {args.question}\n")

if args.endpoint == "answer":
    print(f"Answer:\n{data['answer']}\n")
    print(f"Sources    : {', '.join(data['sources'])}")
    print(f"Chunks used: {data['chunks_used']}")
    print(f"Avg score  : {data.get('avg_score', 'n/a')}")

    if data.get("low_confidence"):
        print("⚠️  Low confidence — results may not be strongly relevant")

    if args.show_chunks and data.get("chunks"):
        print("\n--- Retrieved Chunks ---")
        for i, chunk in enumerate(data["chunks"], 1):
            print(
                f"\nChunk {i} | Source: {chunk['source']} | Score: {chunk['score']}")
            print(f"{chunk['text'][:300]}...")

elif args.endpoint == "query":
    for i, chunk in enumerate(data["results"], 1):
        print(f"--- Chunk {i} ---")
        print(f"Source : {chunk['source']}")
        print(f"Score  : {chunk['score']}")
        if args.show_chunks:
            print(f"Text   : {chunk['text'][:300]}...")
        print()
