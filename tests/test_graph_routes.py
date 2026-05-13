from __future__ import annotations

import pytest
from flask import Flask


@pytest.fixture()
def graph_client():
    from modules.graph.routes import graph_bp

    app = Flask(__name__)
    app.secret_key = "graph-test-secret"
    app.register_blueprint(graph_bp)
    return app.test_client()


def test_graph_status_route_returns_payload(graph_client, monkeypatch):
    import modules.graph.routes as routes

    monkeypatch.setattr(
        routes,
        "get_graph_backend_status",
        lambda: {"ok": True, "kingbase": {"ok": True}, "neo4j": {"ok": True}},
    )

    response = graph_client.get("/api/graph/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["kingbase"]["ok"] is True


def test_graph_sync_submit_enqueues_task(graph_client, monkeypatch):
    import modules.graph.routes as routes

    captured = {}

    def fake_submit_task(task_type, payload=None, *, owner_key="", owner_ip="", task_id=None):
        captured["task_type"] = task_type
        captured["payload"] = payload
        captured["owner_key"] = owner_key
        captured["owner_ip"] = owner_ip
        return "graph-task-1"

    monkeypatch.setattr(routes, "submit_task", fake_submit_task)

    response = graph_client.post("/api/graph/sync", json={"limit": 25, "theft_only": False})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["task_id"] == "graph-task-1"
    assert captured["task_type"] == "graph_sync"
    assert captured["payload"] == {"limit": 25, "theft_only": False, "incremental": False}


def test_graph_gang_detail_returns_404_when_missing(graph_client, monkeypatch):
    import modules.graph.routes as routes

    monkeypatch.setattr(routes, "get_gang_detail", lambda gang_id, run_id="": None)

    response = graph_client.get("/api/graph/gangs/community_404")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["ok"] is False