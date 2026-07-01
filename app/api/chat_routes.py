from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path as FilePath
from pydantic import BaseModel

from app.services.chat import ask_chat, build_chat_retrieval_bundle
from app.services.chat_logs import client_info, log_chat_interaction
from app.services.postgres import list_datasets

BASE_DIR = FilePath(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter()


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


class ChatRequest(BaseModel):
    question: str
    dataset_id: str | None = None


@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request) -> HTMLResponse:
    """
    Experimental source-grounded chat page.
    """
    datasets = list_datasets()

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "datasets": datasets,
            "active_nav": "chat",
        },
    )


@router.post("/v1/chat/retrieve")
def chat_retrieve_endpoint(
    request_body: ChatRequest,
    request: Request,
) -> dict[str, Any]:
    """
    Retrieve SDMX series and reference chunks for a chat question.

    This endpoint is useful for debugging the grounding before generation.
    """
    question = request_body.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question must not be empty.",
        )

    client_ip, user_agent = client_info(request)
    started = time.monotonic()

    try:
        bundle = build_chat_retrieval_bundle(
            question=question,
            dataset_id=request_body.dataset_id,
        )
    except Exception as exc:
        log_chat_interaction(
            endpoint="retrieve",
            question=question,
            status="error",
            dataset_id=request_body.dataset_id,
            error=str(exc),
            latency_ms=_elapsed_ms(started),
            client_ip=client_ip,
            user_agent=user_agent,
        )

        if isinstance(exc, RuntimeError):
            raise HTTPException(
                status_code=503,
                detail=f"Chat retrieval is not available: {exc}",
            ) from exc

        raise

    log_chat_interaction(
        endpoint="retrieve",
        question=question,
        status="ok",
        dataset_id=request_body.dataset_id,
        latency_ms=_elapsed_ms(started),
        retrieval_queries=bundle.get("retrieval_queries"),
        candidate_series_ids=[
            row.get("series_id") for row in bundle.get("series_matches", [])
        ],
        client_ip=client_ip,
        user_agent=user_agent,
    )

    return bundle


@router.post("/v1/chat/ask")
def chat_ask_endpoint(
    request_body: ChatRequest,
    request: Request,
) -> dict[str, Any]:
    """
    Retrieve source-backed context and generate a short grounded answer.
    """
    question = request_body.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question must not be empty.",
        )

    client_ip, user_agent = client_info(request)
    started = time.monotonic()

    try:
        result = ask_chat(
            question=question,
            dataset_id=request_body.dataset_id,
        )
    except Exception as exc:
        log_chat_interaction(
            endpoint="ask",
            question=question,
            status="error",
            dataset_id=request_body.dataset_id,
            error=str(exc),
            latency_ms=_elapsed_ms(started),
            client_ip=client_ip,
            user_agent=user_agent,
        )

        if isinstance(exc, RuntimeError):
            raise HTTPException(
                status_code=503,
                detail=f"Chat is not available: {exc}",
            ) from exc

        raise

    debug = result.get("debug", {})

    log_chat_interaction(
        endpoint="ask",
        question=question,
        status="ok",
        dataset_id=request_body.dataset_id,
        latency_ms=_elapsed_ms(started),
        model=result.get("model"),
        answer=result.get("answer"),
        raw_model_response=debug.get("raw_model_response"),
        retrieval_queries=debug.get("retrieval_queries"),
        candidate_series_ids=[
            row.get("series_id") for row in debug.get("candidate_series", [])
        ],
        selected_series_ids=debug.get("selected_series_ids"),
        selected_reference_chunk_ids=debug.get("selected_reference_chunk_ids"),
        client_ip=client_ip,
        user_agent=user_agent,
    )

    return result
