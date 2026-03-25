# src/utils/rfp/qa_verifier.py
import time

MAX_RETRIES = 2

def verify(results: list[dict], answer_fn, top_k: int = 5) -> list[dict]:
    verified = []

    for item in results:
        attempt = 0
        current = item

        while attempt <= MAX_RETRIES:
            issues = []

            if current["chunks_used"] == 0:
                print(f"[qa] Q{current['id']} — no chunks found, skipping retries (content gap)")
                current["verified"] = False
                current["issues"] = ["no chunks retrieved — content gap"]
                break

            if current["answer"].strip().startswith("INSUFFICIENT CONTEXT"):
                issues.append("insufficient context")

            if current["low_confidence"]:
                issues.append(f"low confidence score ({current['avg_score']})")

            if not issues:
                current["verified"] = True
                current["issues"] = []
                break

            if attempt < MAX_RETRIES:
                print(f"[qa] Q{current['id']} failed ({', '.join(issues)}) — retrying ({attempt + 1}/{MAX_RETRIES})")
                try:
                    retry = answer_fn(current["question"], top_k=top_k + 3)
                    current = {
                        **current,
                        **retry,
                        "id": item["id"],
                        "category": item["category"],
                        "question": item["question"]
                    }
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        print(f"[qa] Rate limit hit — waiting 60s...")
                        time.sleep(60)
                        continue
                    raise
                attempt += 1
            else:
                print(f"[qa] Q{current['id']} failed after {MAX_RETRIES} retries — flagging")
                current["verified"] = False
                current["issues"] = issues
                break

        verified.append(current)

    passed = sum(1 for r in verified if r["verified"])
    flagged = sum(1 for r in verified if not r.get("verified", True))
    print(f"[qa] {passed}/{len(verified)} verified | {flagged} flagged")
    return verified