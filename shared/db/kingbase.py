from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable

import psycopg2
from psycopg2.extras import RealDictCursor

from shared.config.config import (
    KINGBASE_DBNAME,
    KINGBASE_HOST,
    KINGBASE_PASSWORD,
    KINGBASE_PORT,
    KINGBASE_USER,
)


DEFAULT_CONNECT_TIMEOUT_SECONDS = 5


def connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=KINGBASE_HOST,
        port=KINGBASE_PORT,
        dbname=KINGBASE_DBNAME,
        user=KINGBASE_USER,
        password=KINGBASE_PASSWORD,
        connect_timeout=DEFAULT_CONNECT_TIMEOUT_SECONDS,
    )


@contextmanager
def get_connection() -> Iterable[psycopg2.extensions.connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: Any = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def fetch_one(query: str, params: Any = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
    return dict(row) if row is not None else None


def fetch_value(query: str, params: Any = None) -> Any:
    row = fetch_one(query, params)
    if not row:
        return None
    return next(iter(row.values()))


def execute(query: str, params: Any = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            affected = cur.rowcount
        conn.commit()
    return max(affected, 0)


def execute_many(query: str, rows: Iterable[tuple[Any, ...]]) -> int:
    batch = list(rows)
    if not batch:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, batch)
        conn.commit()
    return len(batch)


def table_exists(schema_name: str, table_name: str) -> bool:
    return bool(
        fetch_value(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            """,
            (schema_name, table_name),
        )
    )


def ping() -> dict[str, Any]:
    version = fetch_value("SELECT version()")
    return {
        "ok": True,
        "host": KINGBASE_HOST,
        "port": KINGBASE_PORT,
        "dbname": KINGBASE_DBNAME,
        "user": KINGBASE_USER,
        "version": str(version or ""),
    }