# src/api.py
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.utils.retrieval.retriever import query_rag
from src.utils.store.vector_store import collection_count
from src.utils.rfp.answerer import answer_question

import time
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

# Immediately after app = FastAPI()
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    body = await request.body()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    logger.info(
        f"endpoint={request.url.path} "
        f"status={response.status_code} "
        f"ms={duration} "
        f"body={body.decode()[:300]}"
    )
    return response

class QueryRequest(BaseModel):
    question: str = Field(..., description="The question to search for", example="What is this document about?")
    top_k: int = Field(5, description="Number of results to return", example=5)


class AnswerRequest(BaseModel):
    question: str = Field(..., description="The question to ask", example="What is this document about?")
    top_k: int = Field(5, description="Number of chunks to retrieve", example=5)
    include_chunks: bool = Field(False, description="Include raw chunks in response")


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


def custom_openapi():
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
                                        "question": {
                                            "type": "string",
                                            "description": "The question to search for"
                                        },
                                        "top_k": {
                                            "type": "integer",
                                            "description": "Number of results to return",
                                            "default": 5
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "question": {"type": "string"},
                                            "results": {"type": "array"}
                                        }
                                    }
                                }
                            }
                        }
                    }
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
                                        "question": {
                                            "type": "string",
                                            "description": "The question to answer"
                                        },
                                        "top_k": {
                                            "type": "integer",
                                            "description": "Number of chunks to retrieve",
                                            "default": 5
                                        },
                                        "include_chunks": {
                                            "type": "boolean",
                                            "description": "Include raw chunks in response",
                                            "default": False
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "answer": {"type": "string"},
                                            "sources": {"type": "array"},
                                            "chunks_used": {"type": "integer"},
                                            "chunks": {"type": "array"}
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