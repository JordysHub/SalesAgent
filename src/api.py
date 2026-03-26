# src/api.py
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

from src.utils.retrieval.retriever import query_rag
from src.utils.store.vector_store import collection_count
from src.utils.rfp.answerer import answer_question
from src.utils.rfp.orchestrator import extract_questions
from src.utils.rfp.answer_agent import answer_all
from src.utils.rfp.qa_verifier import verify
from src.utils.rfp.composer import compose_proposal
from src.utils.connector.blob_connector import get_blob_service

from src.config import STORAGE_ACCOUNT, CONTAINER_NAME, SAS_EXPIRY_DAYS, TOP_K

from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from pydantic import BaseModel, Field, validator

import os
import time
import logging
import tempfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("fastembed").setLevel(logging.WARNING)

load_dotenv()

app = FastAPI()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    body = await request.body()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)

    if request.url.path in ("/health", "/stats"):
        return response

    user_agent = request.headers.get("user-agent", "unknown")
    client_id = request.headers.get("x-client-id", None)
    client_ip = request.headers.get("x-forwarded-for", request.client.host)

    if client_id:
        caller = client_id
    elif "curl" in user_agent.lower():
        caller = "curl"
    elif "swagger" in user_agent.lower() or "openapi" in user_agent.lower():
        caller = "swagger"
    elif "python" in user_agent.lower():
        caller = "python-script"
    else:
        caller = user_agent[:50]

    logger.info(
        f"endpoint={request.url.path} "
        f"status={response.status_code} "
        f"ms={duration} "
        f"caller={caller} "
        f"ip={client_ip} "
        f"body={body.decode()[:300]}"
    )
    return response


# ─── Models ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., description="The question to search for")
    top_k: int = Field(TOP_K, description="Number of results to return")

    @validator("question")
    def question_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("question must not be empty")
        return v


class AnswerRequest(BaseModel):
    question: str = Field(..., description="The question to ask")
    top_k: int = Field(TOP_K, description="Number of chunks to retrieve")
    include_chunks: bool = Field(
        False, description="Include raw chunks in response")

    @validator("question")
    def question_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("question must not be empty")
        return v


class PipelineRequest(BaseModel):
    filename: str = Field(...,
                          description="RFP filename in blob rfp-inputs/ folder")
    top_k: int = Field(TOP_K, description="Chunks to retrieve per question")
    max_questions: int = Field(
        0, description="Maximum questions to process. 0 = all questions.")


class QueryResponse(BaseModel):
    question: str
    results: list[dict]


class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]
    chunks_used: int
    chunks: list[dict] = []
    low_confidence: bool = False
    avg_score: float = 0.0


class PipelineResponse(BaseModel):
    status: str
    rfp_filename: str
    questions_extracted: int
    questions_answered: int
    questions_verified: int
    questions_flagged: int
    output_filename: str
    output_url: str
    output_url_expires: str


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    count = collection_count()
    return {"total_chunks": count}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    results = query_rag(request.question, top_k=request.top_k)
    return {"question": request.question, "results": results}


@app.post("/answer", response_model=AnswerResponse)
def answer(request: AnswerRequest):
    result = answer_question(
        request.question,
        top_k=request.top_k,
        include_chunks=request.include_chunks
    )
    return result


@app.post("/pipeline", response_model=PipelineResponse)
def pipeline(request: PipelineRequest):
    """
    Trigger the full RFP pipeline for the given filename.

    The pipeline consists of four steps: extract questions from the RFP, answer the questions using the knowledge base, verify the answers, and compose the proposal document.

    Parameters:
        request (PipelineRequest): the request containing the RFP filename and other options

    Returns:
        PipelineResponse: the response containing the pipeline status, RFP filename, question counts, output filename, and output URL

    Raises:
        ValueError: if the RFP is not found in the blob
    """
    logger.info(f"[pipeline] Starting for {request.filename}")

    blob_path = f"rfp-inputs/{request.filename}"
    ext = os.path.splitext(request.filename)[1].lower()

    service = get_blob_service()
    blob_client = service.get_blob_client(
        container=CONTAINER_NAME, blob=blob_path)

    if not blob_client.exists():
        raise ValueError(f"RFP not found in blob: {blob_path}")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(blob_client.download_blob().readall())

    logger.info(f"[pipeline] Downloaded {request.filename} to temp file")

    # step 1: extract questions
    all_questions = extract_questions(tmp_path)
    os.unlink(tmp_path)

    questions = all_questions[:request.max_questions] if request.max_questions > 0 else all_questions
    logger.info(
        f"[pipeline] Extracted {len(all_questions)} questions, processing {len(questions)}")

    # step 2: answer
    results = answer_all(questions, top_k=request.top_k)

    # step 3: verify
    verified = verify(results, answer_question, top_k=request.top_k)

    # step 4: compose
    output_filename = f"proposal_{request.filename}"
    output_path = f"/tmp/{output_filename}"
    compose_proposal(verified, request.filename, output_path)

    # upload to blob
    output_blob_path = f"rfp-outputs/{output_filename}"
    output_blob_client = service.get_blob_client(
        container=CONTAINER_NAME, blob=output_blob_path)
    with open(output_path, "rb") as f:
        output_blob_client.upload_blob(f, overwrite=True)
    os.unlink(output_path)

    # generate SAS URL valid for 7 days
    expiry = datetime.now(timezone.utc) + timedelta(days=7)
    sas_token = generate_blob_sas(
        account_name=STORAGE_ACCOUNT,
        container_name=CONTAINER_NAME,
        blob_name=output_blob_path,
        account_key=os.getenv("AZURE_STORAGE_KEY"),
        permission=BlobSasPermissions(read=True),
        expiry=expiry
    )
    output_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/{CONTAINER_NAME}/{output_blob_path}?{sas_token}"

    questions_verified = sum(1 for r in verified if r.get("verified", False))
    questions_flagged = sum(1 for r in verified if not r.get("verified", True))

    logger.info(
        f"[pipeline] Done. {questions_verified}/{len(verified)} verified. Output: {output_blob_path}")

    return PipelineResponse(
        status="completed",
        rfp_filename=request.filename,
        questions_extracted=len(all_questions),
        questions_answered=len(results),
        questions_verified=questions_verified,
        questions_flagged=questions_flagged,
        output_filename=output_filename,
        output_url=output_url,
        output_url_expires=expiry.strftime("%Y-%m-%d %H:%M UTC")
    )


# ─── OpenAPI ─────────────────────────────────────────────────────────────────

def custom_openapi():
    """
    Return a custom OpenAPI document for the RAG API.

    The OpenAPI document defines the API endpoints, request and response bodies, and other metadata.

    Returns:
        dict: the OpenAPI document
    """
    return {
        "openapi": "3.0.0",
        "info": {"title": "RAG API", "version": "0.1.0"},
        "paths": {
            "/query": {
                "post": {
                    "summary": "Query the knowledge base",
                    "operationId": "queryKnowledgeBase",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["question"],
                                    "properties": {
                                        "question": {"type": "string"},
                                        "top_k": {"type": "integer", "default": 5}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/answer": {
                "post": {
                    "summary": "Answer a question using retrieved context",
                    "operationId": "answerQuestion",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["question"],
                                    "properties": {
                                        "question": {"type": "string"},
                                        "top_k": {"type": "integer", "default": 5},
                                        "include_chunks": {"type": "boolean", "default": False}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/pipeline": {
                "post": {
                    "summary": "Run full RFP response pipeline",
                    "operationId": "runPipeline",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["filename"],
                                    "properties": {
                                        "filename": {
                                            "type": "string",
                                            "description": "RFP filename in blob rfp-inputs/ folder"
                                        },
                                        "top_k": {"type": "integer", "default": 8},
                                        "max_questions": {
                                            "type": "integer",
                                            "default": 0,
                                            "description": "0 = all questions"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Pipeline completed",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "rfp_filename": {"type": "string"},
                                            "questions_extracted": {"type": "integer"},
                                            "questions_answered": {"type": "integer"},
                                            "questions_verified": {"type": "integer"},
                                            "questions_flagged": {"type": "integer"},
                                            "output_filename": {"type": "string"},
                                            "output_url": {"type": "string"},
                                            "output_url_expires": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


app.openapi = custom_openapi
