# src/utils/rfp/answerer.py

"""
Answerer — Core RAG Answer Function

Handles retrieval and synthesis for a single question. Queries Qdrant via
query_rag() to retrieve the most relevant chunks, then passes them to the
LLM for grounded answer generation.

Key design decision: the LLM is strictly prohibited from using its own
knowledge. Every claim must be supported by a retrieved chunk and cited
with a source filename. If context is insufficient, the answer begins with
INSUFFICIENT CONTEXT rather than fabricating a response.

Used directly by the answer agent and by the QA verifier during retries.
"""

from dotenv import load_dotenv

from src.config import LOW_CONFIDENCE, TEMPERATURE, TOP_K
from src.utils.llm_client import chat
from src.utils.retrieval.retriever import query_rag

load_dotenv()


def synthesise(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        [f"[Source: {c['source']} | Score: {c['score']}]\n{c['text']}" for c in chunks]
    )
    messages = [
        {
            "role": "system",
            "content": """You are a professional proposal writer.
            Answer the question strictly using the provided context chunks.
            Rules:
            - Only use information present in the context
            - Cite the source filename after every claim e.g. [source.pdf]
            - If context is insufficient write: INSUFFICIENT CONTEXT: [what is missing]
            - Be concise and professional
            - Do not use your own knowledge""",
        },
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ]
    return chat(messages, temperature=TEMPERATURE)


def answer_question(question: str, top_k: int = TOP_K, include_chunks: bool = False) -> dict:
    chunks = query_rag(question, top_k=top_k)

    avg_score = sum(c["score"] for c in chunks) / len(chunks) if chunks else 0
    low_confidence = avg_score < LOW_CONFIDENCE  # warn but don't block

    answer = synthesise(question, chunks)

    return {
        "answer": answer,
        "sources": list(set([c["source"] for c in chunks])),
        "chunks_used": len(chunks),
        "low_confidence": low_confidence,  # flag for the agent to use
        "avg_score": round(avg_score, 4),
        "chunks": chunks if include_chunks else [],
    }
