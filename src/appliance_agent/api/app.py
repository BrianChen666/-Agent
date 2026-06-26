from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from appliance_agent.agent import ApplianceAgent


class ChatRequest(BaseModel):
    session_id: str = Field(default="default")
    message: str


class SearchRequest(BaseModel):
    query: str
    model: str | None = None
    fault_code: str | None = None
    source_types: list[str] | None = None
    top_k: int = 5


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    project_root = Path(__file__).resolve().parents[3]
    resolved_data_dir = Path(data_dir) if data_dir else project_root / "原始数据"
    agent = ApplianceAgent.from_data_dir(resolved_data_dir)
    app = FastAPI(title="Aqualink 家电售后智能客服 Agent", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat")
    def chat(request: ChatRequest) -> dict[str, Any]:
        response = agent.chat(request.session_id, request.message)
        return {
            "answer": response.answer,
            "intent": response.intent,
            "contexts": response.contexts,
            "citations": response.citations,
            "metadata": response.metadata,
        }

    @app.post("/search")
    def search(request: SearchRequest) -> dict[str, Any]:
        results = agent.retriever.hybrid_search(
            request.query,
            model=request.model,
            fault_code=request.fault_code,
            source_types=request.source_types,
            top_k=request.top_k,
        )
        return {
            "results": [
                {
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "text": result.text,
                    "metadata": result.metadata,
                }
                for result in results
            ]
        }

    return app


app = create_app()
