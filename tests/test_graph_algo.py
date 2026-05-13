from __future__ import annotations

from typing import Any
from unittest.mock import call

import pytest


# ---------------------------------------------------------------------------
# detect_gangs
# ---------------------------------------------------------------------------


class TestDetectGangs:
    def test_raises_when_table_missing(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        monkeypatch.setattr(algo, "table_exists", lambda s, t: False)

        with pytest.raises(RuntimeError, match="hm_gang_result not found"):
            algo.detect_gangs()

    def test_returns_early_when_no_edges(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        monkeypatch.setattr(algo, "table_exists", lambda s, t: True)
        monkeypatch.setattr(algo, "run_query", lambda cypher, params=None: [{"edge_count": 0}])

        result = algo.detect_gangs()

        assert result["ok"] is True
        assert result["gang_count"] == 0
        assert result["member_count"] == 0
        assert "no CO_SUSPECT" in result["message"]

    def test_creates_projection_and_runs_louvain(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        calls = []

        def fake_run_query(cypher, params=None):
            calls.append(cypher)
            if "gds.graph.exists" in cypher:
                return [{"exists": False}]
            if "count(r)" in cypher:
                return [{"edge_count": 10}]
            if "gds.graph.project" in cypher:
                return [{"graphName": "hm-co-suspect", "nodeCount": 5, "relationshipCount": 10}]
            if "gds.louvain" in cypher:
                return [
                    {"nodeId": 0, "communityId": 1},
                    {"nodeId": 1, "communityId": 1},
                    {"nodeId": 2, "communityId": 1},
                ]
            if "gds.betweenness" in cypher:
                return [
                    {"nodeId": 0, "score": 1.0},
                    {"nodeId": 1, "score": 0.5},
                    {"nodeId": 2, "score": 0.0},
                ]
            if "gds.graph.drop" in cypher:
                return [{"graphName": "hm-co-suspect"}]
            if "gds.util.asNode" in cypher or "sfzh" in cypher:
                return []
            return []

        def fake_run_query_with_nodes(cypher, params=None):
            calls.append(cypher)
            if "gds.graph.exists" in cypher:
                return [{"exists": False}]
            if "count(r)" in cypher:
                return [{"edge_count": 10}]
            if "gds.graph.project" in cypher:
                return [{"graphName": "hm-co-suspect", "nodeCount": 3, "relationshipCount": 2}]
            if "gds.louvain" in cypher:
                return [
                    {"nodeId": 0, "communityId": 1},
                    {"nodeId": 1, "communityId": 1},
                ]
            if "gds.betweenness" in cypher:
                return [
                    {"nodeId": 0, "score": 1.0},
                    {"nodeId": 1, "score": 0.0},
                ]
            if "gds.graph.drop" in cypher:
                return [{"graphName": "hm-co-suspect"}]
            return []

        # Mock gds.util.asNode to return properties
        class MockNode:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        def fake_run_query_full(cypher, params=None):
            calls.append(cypher)
            if "gds.graph.exists" in cypher:
                return [{"exists": False}]
            if "count(r)" in cypher:
                return [{"edge_count": 10}]
            if "gds.graph.project" in cypher:
                return [{"graphName": "hm-co-suspect", "nodeCount": 3, "relationshipCount": 2}]
            if "gds.louvain" in cypher:
                return [
                    {"nodeId": 0, "communityId": 1, "member_sfzh": "110", "member_name": "A", "member_age": 25, "is_wcnr": False, "area_code": "320100"},
                    {"nodeId": 1, "communityId": 1, "member_sfzh": "220", "member_name": "B", "member_age": 30, "is_wcnr": False, "area_code": "320100"},
                ]
            if "gds.betweenness" in cypher:
                return [
                    {"member_sfzh": "110", "score": 1.0},
                    {"member_sfzh": "220", "score": 0.0},
                ]
            if "gds.graph.drop" in cypher:
                return [{"graphName": "hm-co-suspect"}]
            return []

        monkeypatch.setattr(algo, "table_exists", lambda s, t: True)
        monkeypatch.setattr(algo, "run_query", fake_run_query_full)
        monkeypatch.setattr(algo, "execute_many", lambda sql, params: None)

        result = algo.detect_gangs(min_size=2)

        assert result["ok"] is True
        assert result["gang_count"] == 1
        assert result["member_count"] == 2
        # Verify GDS projection was created and algorithms were called
        assert any("gds.graph.project" in c for c in calls)
        assert any("gds.louvain" in c for c in calls)
        assert any("gds.betweenness" in c for c in calls)

    def test_filters_by_min_size(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        def fake_run_query(cypher, params=None):
            if "gds.graph.exists" in cypher:
                return [{"exists": False}]
            if "count(r)" in cypher:
                return [{"edge_count": 10}]
            if "gds.graph.project" in cypher:
                return [{"graphName": "hm-co-suspect", "nodeCount": 4, "relationshipCount": 3}]
            if "gds.louvain" in cypher:
                return [
                    {"nodeId": 0, "communityId": 1, "member_sfzh": "110", "member_name": "A", "member_age": 25, "is_wcnr": False, "area_code": ""},
                    {"nodeId": 1, "communityId": 1, "member_sfzh": "220", "member_name": "B", "member_age": 30, "is_wcnr": False, "area_code": ""},
                    {"nodeId": 2, "communityId": 1, "member_sfzh": "330", "member_name": "C", "member_age": 28, "is_wcnr": False, "area_code": ""},
                    {"nodeId": 3, "communityId": 2, "member_sfzh": "440", "member_name": "D", "member_age": 22, "is_wcnr": True, "area_code": ""},
                ]
            if "gds.betweenness" in cypher:
                return [
                    {"member_sfzh": "110", "score": 1.0},
                    {"member_sfzh": "220", "score": 0.5},
                    {"member_sfzh": "330", "score": 0.0},
                    {"member_sfzh": "440", "score": 0.0},
                ]
            if "gds.graph.drop" in cypher:
                return [{"graphName": "hm-co-suspect"}]
            return []

        inserted = []

        def fake_execute_many(sql, params):
            inserted.extend(params)

        monkeypatch.setattr(algo, "table_exists", lambda s, t: True)
        monkeypatch.setattr(algo, "run_query", fake_run_query)
        monkeypatch.setattr(algo, "execute_many", fake_execute_many)

        result = algo.detect_gangs(min_size=3)

        assert result["ok"] is True
        assert result["gang_count"] == 1  # only community with >= 3 members
        assert result["member_count"] == 3

    def test_writes_results_to_kingbase(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        def fake_run_query(cypher, params=None):
            if "gds.graph.exists" in cypher:
                return [{"exists": False}]
            if "count(r)" in cypher:
                return [{"edge_count": 5}]
            if "gds.graph.project" in cypher:
                return [{"graphName": "hm-co-suspect", "nodeCount": 2, "relationshipCount": 1}]
            if "gds.louvain" in cypher:
                return [
                    {"nodeId": 0, "communityId": 1, "member_sfzh": "110", "member_name": "A", "member_age": 25, "is_wcnr": False, "area_code": "320100"},
                    {"nodeId": 1, "communityId": 1, "member_sfzh": "220", "member_name": "B", "member_age": 30, "is_wcnr": True, "area_code": "320100"},
                ]
            if "gds.betweenness" in cypher:
                return [
                    {"member_sfzh": "110", "score": 2.0},
                    {"member_sfzh": "220", "score": 0.0},
                ]
            if "gds.graph.drop" in cypher:
                return [{"graphName": "hm-co-suspect"}]
            return []

        inserted_rows = []

        def fake_execute_many(sql, params):
            inserted_rows.extend(params)

        monkeypatch.setattr(algo, "table_exists", lambda s, t: True)
        monkeypatch.setattr(algo, "run_query", fake_run_query)
        monkeypatch.setattr(algo, "execute_many", fake_execute_many)

        result = algo.detect_gangs()

        assert result["ok"] is True
        assert len(inserted_rows) == 2
        # Check first inserted row structure
        row = inserted_rows[0]
        assert row[0] == "community_1"  # gang_id
        assert row[1]  # run_id (uuid)
        assert row[2] in ("110", "220")  # member_sfzh
        assert row[7] in (2.0, 0.0)  # centrality_score
        assert row[8] == "louvain"  # algo_type


# ---------------------------------------------------------------------------
# predict_links
# ---------------------------------------------------------------------------


class TestPredictLinks:
    def test_returns_common_neighbors(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        fake_links = [
            {"source_sfzh": "110", "source_name": "A", "source_age": 25, "target_sfzh": "330", "target_name": "C", "target_age": 28, "common_neighbors": 3},
            {"source_sfzh": "220", "source_name": "B", "source_age": 30, "target_sfzh": "440", "target_name": "D", "target_age": 22, "common_neighbors": 2},
        ]

        def fake_run_query(cypher, params=None):
            assert "$min_common" in cypher
            assert "$limit" in cypher
            return fake_links

        monkeypatch.setattr(algo, "run_query", fake_run_query)

        result = algo.predict_links(limit=50, min_common=2)

        assert result["ok"] is True
        assert result["count"] == 2
        assert result["links"] == fake_links

    def test_respects_min_common_param(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        captured_params = {}

        def fake_run_query(cypher, params=None):
            captured_params.update(params or {})
            return []

        monkeypatch.setattr(algo, "run_query", fake_run_query)

        algo.predict_links(limit=10, min_common=5)

        assert captured_params["min_common"] == 5
        assert captured_params["limit"] == 10

    def test_returns_empty_when_no_links(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        monkeypatch.setattr(algo, "run_query", lambda cypher, params=None: [])

        result = algo.predict_links()

        assert result["ok"] is True
        assert result["count"] == 0
        assert result["links"] == []


# ---------------------------------------------------------------------------
# list_gangs
# ---------------------------------------------------------------------------


class TestListGangs:
    def test_returns_empty_when_no_table(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        monkeypatch.setattr(algo, "table_exists", lambda s, t: False)

        result = algo.list_gangs()

        assert result["ok"] is True
        assert result["table_ready"] is False
        assert result["items"] == []

    def test_returns_empty_when_no_runs(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        monkeypatch.setattr(algo, "table_exists", lambda s, t: True)
        monkeypatch.setattr(algo, "fetch_value", lambda sql, params=None: "")

        result = algo.list_gangs()

        assert result["ok"] is True
        assert result["table_ready"] is True
        assert result["items"] == []


# ---------------------------------------------------------------------------
# get_gang_detail
# ---------------------------------------------------------------------------


class TestGetGangDetail:
    def test_returns_none_when_no_table(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        monkeypatch.setattr(algo, "table_exists", lambda s, t: False)

        result = algo.get_gang_detail("community_1")

        assert result is None

    def test_returns_members_links_cases(self, monkeypatch):
        import modules.graph.services.algo_service as algo

        fake_members = [
            {"gang_id": "community_1", "run_id": "abc", "member_sfzh": "110", "member_name": "A", "centrality_score": 1.0},
        ]

        def fake_run_query(cypher, params=None):
            if "CO_SUSPECT" in cypher and "a.sfzh" in cypher:
                return [{"source": {"sfzh": "110"}, "target": {"sfzh": "220"}, "rel": {"weight": 3}}]
            if "SAME_CASE" in cypher:
                return [{"sfzh": "110", "case_node": {"ajbh": "A001"}, "rel": {}}]
            return []

        monkeypatch.setattr(algo, "table_exists", lambda s, t: True)
        monkeypatch.setattr(algo, "fetch_value", lambda sql, params=None: "abc")
        monkeypatch.setattr(algo, "fetch_all", lambda sql, params=None: fake_members)
        monkeypatch.setattr(algo, "run_query", fake_run_query)

        result = algo.get_gang_detail("community_1")

        assert result is not None
        assert result["ok"] is True
        assert len(result["members"]) == 1
        assert len(result["links"]) == 1
        assert len(result["cases"]) == 1
