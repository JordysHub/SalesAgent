# scripts/run_pipeline.py
import os
import sys
import json
import argparse
from dotenv import load_dotenv

load_dotenv()

from src.utils.rfp.orchestrator import extract_questions
from src.utils.rfp.answer_agent import answer_all
from src.utils.rfp.qa_verifier import verify
from src.utils.rfp.composer import compose_proposal
from src.utils.rfp.answerer import answer_question

parser = argparse.ArgumentParser(description="Run full RFP response pipeline")
parser.add_argument("--file", type=str, required=True, help="Path to RFP DOCX or PDF")
parser.add_argument("--top-k", type=int, default=5, help="Chunks to retrieve per question")
parser.add_argument("--max-questions", type=int, default=5, help="Limit number of questions to process")
parser.add_argument("--output", type=str, default="data/rfp-outputs/proposal_output.docx")
parser.add_argument("--save-questions", type=str, default="data/rfp-questions/rfp_questions.json")
args = parser.parse_args()

print("\n=== RFP Response Pipeline ===\n")

# step 1: extract questions
questions = extract_questions(args.file)
print(f"[pipeline] Extracted {len(questions)} questions")

if args.max_questions:
    questions = questions[:args.max_questions]
    print(f"[pipeline] Limited to {len(questions)} questions")

if args.save_questions:
    with open(args.save_questions, "w") as f:
        json.dump({"questions": questions, "source": os.path.basename(args.file)}, f, indent=2)

# step 2: answer all questions
results = answer_all(questions, top_k=args.top_k)

# step 3: verify
verified = verify(results, answer_question, top_k=args.top_k)

# step 4: compose proposal
compose_proposal(verified, os.path.basename(args.file), args.output)

print(f"\n=== Done. Proposal saved to {args.output} ===")