from __future__ import annotations

from threading import Lock
from typing import Any

from shared.config.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


class Neo4jDependencyError(RuntimeError):
    pass


_DRIVER = None
_DRIVER_LOCK = Lock()


def _load_graph_database():
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise Neo4jDependencyError("neo4j Python driver is not installed") from exc
    return GraphDatabase


def get_driver():
    global _DRIVER
    if _DRIVER is None:
        with _DRIVER_LOCK:
            if _DRIVER is None:
                graph_database = _load_graph_database()
                _DRIVER = graph_database.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _DRIVER


def close_driver() -> None:
    global _DRIVER
    if _DRIVER is not None:
        _DRIVER.close()
        _DRIVER = None


def verify_connectivity() -> dict[str, Any]:
    driver = get_driver()
    driver.verify_connectivity()
    return {
        "ok": True,
        "uri": NEO4J_URI,
        "user": NEO4J_USER,
        "database": NEO4J_DATABASE,
    }


def run_query(cypher: str, parameters: dict[str, Any] | None = None, *, database: str | None = None) -> list[dict[str, Any]]:
    driver = get_driver()
    with driver.session(database=database or NEO4J_DATABASE) as session:
        result = session.run(cypher, parameters or {})
        return [record.data() for record in result]