# src/api.py
from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.utils.retrieval.retriever import query_rag

load_dotenv()

app = FastAPI()


class QueryRequest(BaseModel):
    question: str = Field(..., description="The question to search for",
                          example="What is this document about?")
    top_k: int = Field(5, description="Number of results to return", example=5)


class QueryResponse(BaseModel):
    question: str
    results: list[dict]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    results = query_rag(request.question, top_k=request.top_k)
    return {"question": request.question, "results": results}


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
            }
        }
    }


app.openapi = custom_openapi
