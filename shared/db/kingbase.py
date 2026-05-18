from contextlib import contextmanager
import os
import threading
from typing import Any, Iterator

from shared.config.config import logger


try:
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    pool = None
    RealDictCursor = None


KINGBASE_HOST = os.getenv("KINGBASE_HOST", "")
KINGBASE_PORT = int(os.getenv("KINGBASE_PORT", "54321"))
KINGBASE_DB = os.getenv("KINGBASE_DB", "")
KINGBASE_USER = os.getenv("KINGBASE_USER", "")
KINGBASE_PASSWORD = os.getenv("KINGBASE_PASSWORD", "")


_kingbase_pool = None
_pool_lock = threading.Lock()


def _connection_kwargs() -> dict[str, Any]:
    return {
        "host": KINGBASE_HOST,
        "port": KINGBASE_PORT,
        "database": KINGBASE_DB,
        "user": KINGBASE_USER,
        "password": KINGBASE_PASSWORD,
    }


def init_pool():
    """Initialize the shared KingBase connection pool lazily."""
    global _kingbase_pool
    if _kingbase_pool is not None:
        return _kingbase_pool

    if psycopg2 is None or pool is None:
        raise RuntimeError("psycopg2 driver not available")

    with _pool_lock:
        if _kingbase_pool is None:
            _kingbase_pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                **_connection_kwargs(),
            )
            logger.info(
                "KingBase connection pool initialized: %s:%s/%s",
                KINGBASE_HOST,
                KINGBASE_PORT,
                KINGBASE_DB,
            )
    return _kingbase_pool


def close_pool() -> None:
    """Close all connections in the shared KingBase pool."""
    global _kingbase_pool
    with _pool_lock:
        if _kingbase_pool is not None:
            _kingbase_pool.closeall()
            _kingbase_pool = None
            logger.info("KingBase connection pool closed")


@contextmanager
def get_connection() -> Iterator[Any]:
    """Acquire a KingBase connection from the shared pool."""
    conn = None
    db_pool = init_pool()
    try:
        conn = db_pool.getconn()
        yield conn
        conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            db_pool.putconn(conn)


def query_one(sql: str, params: dict | tuple | list | None = None) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else {}


def query_all(sql: str, params: dict | tuple | list | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]


def execute(sql: str, params: dict | tuple | list | None = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount
