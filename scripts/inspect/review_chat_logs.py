"""
Review recent Chat interaction logs.

Usage examples:
    python -m scripts.inspect.review_chat_logs
    python -m scripts.inspect.review_chat_logs --limit 50 --endpoint ask
    python -m scripts.inspect.review_chat_logs --errors-only
    python -m scripts.inspect.review_chat_logs --search "ignore previous"

The --search filter is handy for spotting prompt-injection attempts: it matches
the raw question and the raw model response, so you can see both what was asked
and whether the model's output changed in response.
"""
from __future__ import annotations

import argparse
import textwrap
from typing import Any

from app.services.postgres import get_connection


def fetch_logs(
    limit: int,
    endpoint: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if endpoint:
        clauses.append("endpoint = %s")
        params.append(endpoint)

    if status:
        clauses.append("status = %s")
        params.append(status)

    if search:
        clauses.append("(question ILIKE %s OR raw_model_response ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT
            log_id, created_at, endpoint, status, latency_ms, dataset_id,
            client_ip, user_agent, question, answer, raw_model_response, error
        FROM chat_interaction_logs
        {where}
        ORDER BY created_at DESC
        LIMIT %s
    """
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.fetchall()


def _short(value: Any, width: int = 400) -> str:
    if value is None:
        return ""
    return textwrap.shorten(" ".join(str(value).split()), width=width, placeholder=" …")


def main() -> None:
    parser = argparse.ArgumentParser(description="Review recent Chat interaction logs.")
    parser.add_argument("--limit", type=int, default=20, help="Max rows to show.")
    parser.add_argument("--endpoint", choices=["ask", "retrieve"], help="Filter by endpoint.")
    parser.add_argument("--status", choices=["ok", "error"], help="Filter by status.")
    parser.add_argument("--errors-only", action="store_true", help="Shortcut for --status error.")
    parser.add_argument("--search", help="Match text in the question or raw model response.")

    args = parser.parse_args()
    status = "error" if args.errors_only else args.status

    rows = fetch_logs(
        limit=args.limit,
        endpoint=args.endpoint,
        status=status,
        search=args.search,
    )

    if not rows:
        print("No chat interaction logs found.")
        return

    for row in rows:
        latency = row["latency_ms"]
        latency_text = f"{latency}ms" if latency is not None else "-"

        print("=" * 88)
        print(
            f"#{row['log_id']}  {row['created_at']:%Y-%m-%d %H:%M:%S}  "
            f"{row['endpoint']}/{row['status']}  {latency_text}  "
            f"dataset={row['dataset_id'] or '-'}  ip={row['client_ip'] or '-'}"
        )
        print(f"  Q: {_short(row['question'])}")

        if row["answer"]:
            print(f"  A: {_short(row['answer'])}")

        if row["raw_model_response"]:
            print(f"  raw: {_short(row['raw_model_response'])}")

        if row["error"]:
            print(f"  error: {_short(row['error'], 300)}")

    print("=" * 88)
    print(f"{len(rows)} row(s).")


if __name__ == "__main__":
    main()
