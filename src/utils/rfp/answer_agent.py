# src/utils/rfp/answer_agent.py

"""
Answer Agent — Pipeline Step 2

Iterates over the question list produced by the orchestrator and calls
answer_question() for each. Collects results into a structured list
preserving question metadata (id, category) alongside the generated answer,
sources, chunk count, confidence score, and low_confidence flag.

Does not perform any verification — that is handled by the QA verifier.
"""

from src.utils.rfp.answerer import answer_question


def answer_all(questions: list[dict], top_k: int = 5) -> list[dict]:
    results = []
    total = len(questions)

    for q in questions:
        print(f"[answer_agent] {q['id']}/{total} {q['category']} — {q['question'][:60]}...")
        result = answer_question(q["question"], top_k=top_k, include_chunks=False)
        results.append(
            {
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "answer": result["answer"],
                "sources": result["sources"],
                "chunks_used": result["chunks_used"],
                "avg_score": result["avg_score"],
                "low_confidence": result["low_confidence"],
            }
        )

    return results
