# src/utils/rfp/orchestrator.py

"""
RFP Orchestrator — Pipeline Step 1

Parses an RFP document and extracts all questions a respondent must answer.
Uses an LLM (Groq) to interpret document structure rather than regex, making
it robust to varying RFP formats and numbering conventions.

Returns a structured list of questions with id, category, and question text.
This output is passed directly to the answer agent.
"""

import json
import os

from dotenv import load_dotenv

from src.utils.ingestion.parser import parse_document
from src.utils.llm_client import chat

load_dotenv()


def extract_questions(filepath: str) -> list[dict]:
    ext = os.path.splitext(filepath)[1].lower()
    doc = {"path": filepath, "filename": os.path.basename(filepath), "extension": ext}
    text = parse_document(doc)

    print(f"[orchestrator] Parsed {len(text)} characters from {os.path.basename(filepath)}")
    print("[orchestrator] Extracting questions via LLM...")

    prompt = f"""You are a procurement analyst. Extract all questions that a respondent must answer from the RFP document below.

            Return ONLY a valid JSON object in this exact format, with no preamble or explanation:
            {{
            "questions": [
                {{
                "id": 1,
                "category": "Category name",
                "question": "Full question text"
                }}
            ]
            }}

            RFP DOCUMENT:
            {text}"""

    messages = [{"role": "user", "content": prompt}]
    raw = chat(messages, temperature=0).strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)["questions"]
