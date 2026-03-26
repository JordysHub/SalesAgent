# src/utils/rfp/orchestrator.py

"""
RFP Orchestrator — Pipeline Step 1

Parses an RFP document and extracts all questions a respondent must answer.
Uses an LLM (Groq) to interpret document structure rather than regex, making
it robust to varying RFP formats and numbering conventions.

Returns a structured list of questions with id, category, and question text.
This output is passed directly to the answer agent.
"""

import os
import json
import requests
from dotenv import load_dotenv
from src.utils.ingestion.parser import parse_document

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def extract_questions(filepath: str) -> list[dict]:
    ext = os.path.splitext(filepath)[1].lower()
    doc = {"path": filepath, "filename": os.path.basename(filepath), "extension": ext}
    text = parse_document(doc)

    print(f"[orchestrator] Parsed {len(text)} characters from {os.path.basename(filepath)}")
    print(f"[orchestrator] Extracting questions via LLM...")

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

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"].strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)["questions"]