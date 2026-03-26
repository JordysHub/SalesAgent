# tests/test_api.py
import pytest
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv(
    "API_URL",
    "https://rag-api.orangepond-15ea034f.northeurope.azurecontainerapps.io"
)


# ─── Health ──────────────────────────────────────────────────────────────────

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ─── Stats ───────────────────────────────────────────────────────────────────

def test_stats_returns_chunk_count():
    response = requests.get(f"{BASE_URL}/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_chunks" in data
    assert isinstance(data["total_chunks"], int)
    assert data["total_chunks"] > 0


# ─── Answer ──────────────────────────────────────────────────────────────────

def test_answer_response_shape():
    response = requests.post(f"{BASE_URL}/answer", json={
        "question": "What services does Accenture offer?",
        "top_k": 5
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert "chunks_used" in data
    assert isinstance(data["chunks_used"], int)
    assert "avg_score" in data
    assert isinstance(data["avg_score"], float)
    assert "low_confidence" in data
    assert isinstance(data["low_confidence"], bool)


def test_answer_empty_question_fails():
    response = requests.post(f"{BASE_URL}/answer", json={
        "question": "",
        "top_k": 5
    })
    assert response.status_code in (400, 422)


def test_answer_missing_question_fails():
    response = requests.post(f"{BASE_URL}/answer", json={"top_k": 5})
    assert response.status_code == 422


# ─── Pipeline ────────────────────────────────────────────────────────────────

def test_pipeline_response_shape():
    response = requests.post(f"{BASE_URL}/pipeline", json={
        "filename": "RFP_TechCorp_AI_Platform_2026.docx",
        "top_k": 5,
        "max_questions": 1
    }, timeout=120)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["rfp_filename"] == "RFP_TechCorp_AI_Platform_2026.docx"
    assert isinstance(data["questions_extracted"], int)
    assert data["questions_extracted"] > 0
    assert isinstance(data["questions_answered"], int)
    assert isinstance(data["questions_verified"], int)
    assert isinstance(data["questions_flagged"], int)
    assert data["output_url"].startswith("https://")
    assert "output_url_expires" in data


def test_pipeline_missing_filename_fails():
    response = requests.post(f"{BASE_URL}/pipeline", json={"top_k": 5})
    assert response.status_code == 422


def test_pipeline_nonexistent_file_fails():
    response = requests.post(f"{BASE_URL}/pipeline", json={
        "filename": "nonexistent_file.docx",
        "max_questions": 1
    }, timeout=30)
    assert response.status_code == 500
