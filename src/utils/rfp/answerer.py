# src/utils/rfp/answerer.py
import os
from groq import Groq
from dotenv import load_dotenv
from src.utils.retrieval.retriever import query_rag

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def synthesise(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join([
        f"[Source: {c['source']} | Score: {c['score']}]\n{c['text']}"
        for c in chunks
    ])

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """You are a professional proposal writer.
Answer the question strictly using the provided context chunks.
Rules:
- Only use information present in the context
- Cite the source filename after every claim e.g. [source.pdf]
- If context is insufficient write: INSUFFICIENT CONTEXT: [what is missing]
- Be concise and professional
- Do not use your own knowledge"""
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
    )
    return response.choices[0].message.content


def answer_question(question: str, top_k: int = 5, include_chunks: bool = False) -> dict:
    chunks = query_rag(question, top_k=top_k)

    avg_score = sum(c["score"] for c in chunks) / len(chunks) if chunks else 0
    low_confidence = avg_score < 0.4  # warn but don't block

    answer = synthesise(question, chunks)

    return {
        "answer": answer,
        "sources": list(set([c["source"] for c in chunks])),
        "chunks_used": len(chunks),
        "low_confidence": low_confidence,  # flag for the agent to use
        "avg_score": round(avg_score, 4),
        "chunks": chunks if include_chunks else []
    }
