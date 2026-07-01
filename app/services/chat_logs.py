from __future__ import annotations

import os
from typing import Any

from psycopg.types.json import Jsonb
from starlette.requests import Request

from app.services.postgres import get_connection


def _should_log_client_ip() -> bool:
    """
    Client IP is personal data, so allow deployments to disable it for privacy.

    Set CHAT_LOG_INCLUDE_CLIENT_IP=0 (or false/no/off) to store NULL for IPs.
    """
    value = os.environ.get("CHAT_LOG_INCLUDE_CLIENT_IP", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def client_info(request: Request) -> tuple[str | None, str | None]:
    """
    Return a best-effort (client_ip, user_agent) for one request.

    The app runs behind Cloud Run / Cloudflare, so prefer the first hop of
    X-Forwarded-For and fall back to the direct peer. IP is omitted when
    CHAT_LOG_INCLUDE_CLIENT_IP is disabled.
    """
    user_agent = request.headers.get("user-agent")

    if not _should_log_client_ip():
        return None, user_agent

    forwarded = request.headers.get("x-forwarded-for")

    if forwarded:
        client_ip: str | None = forwarded.split(",")[0].strip()
    elif request.client is not None:
        client_ip = request.client.host
    else:
        client_ip = None

    return client_ip, user_agent


def _maybe_jsonb(value: Any) -> Jsonb | None:
    return Jsonb(value) if value is not None else None


def log_chat_interaction(
    *,
    endpoint: str,
    question: str,
    status: str,
    dataset_id: str | None = None,
    error: str | None = None,
    latency_ms: int | None = None,
    model: str | None = None,
    answer: str | None = None,
    raw_model_response: str | None = None,
    retrieval_queries: Any = None,
    candidate_series_ids: Any = None,
    selected_series_ids: Any = None,
    selected_reference_chunk_ids: Any = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Insert one chat interaction row.

    This is best-effort by design: logging must never break a chat request, so
    any failure (e.g. the table is missing or the database is briefly
    unreachable) is caught and reported rather than raised.
    """
    sql = """
        INSERT INTO chat_interaction_logs (
            endpoint,
            status,
            question,
            dataset_id,
            error,
            latency_ms,
            model,
            answer,
            raw_model_response,
            retrieval_queries,
            candidate_series_ids,
            selected_series_ids,
            selected_reference_chunk_ids,
            client_ip,
            user_agent
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        endpoint,
                        status,
                        question,
                        dataset_id,
                        error,
                        latency_ms,
                        model,
                        answer,
                        raw_model_response,
                        _maybe_jsonb(retrieval_queries),
                        _maybe_jsonb(candidate_series_ids),
                        _maybe_jsonb(selected_series_ids),
                        _maybe_jsonb(selected_reference_chunk_ids),
                        client_ip,
                        user_agent,
                    ),
                )
            conn.commit()
    except Exception as exc:  # logging must never break chat
        print(f"WARNING: failed to log chat interaction: {exc!r}")
