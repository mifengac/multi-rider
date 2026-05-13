from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_fetch_all(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Default no-op fetch that returns empty list."""
    return []


def _make_person_row(sfzh: str = "320102199001011234", ts: str = "2026-05-10T08:00:00") -> dict[str, Any]:
    return {
        "sfzh": sfzh,
        "name": "Test",
        "gender": "M",
        "birth_date": date(1990, 1, 1),
        "is_wcnr": False,
        "hjd": None,
        "jzdz": None,
        "area_code": "320100",
        "_ts": datetime.fromisoformat(ts),
    }


def _make_case_row(ajbh: str = "A20260101001", ts: str = "2026-05-10T09:00:00") -> dict[str, Any]:
    return {
        "ajbh": ajbh,
        "aymc": "盗窃",
        "ajlx": "刑事",
        "fasj": datetime.fromisoformat(ts),
        "area_code": "320100",
        "cbdw_mc": "测试派出所",
        "_ts": datetime.fromisoformat(ts),
    }


def _make_same_case_row(ts: str = "2026-05-10T09:00:00") -> dict[str, Any]:
    return {
        "sfzh": "320102199001011234",
        "ajbh": "A20260101001",
        "aymc": "盗窃",
        "case_date": datetime.fromisoformat(ts),
        "area_code": "320100",
        "_ts": datetime.fromisoformat(ts),
    }


def _make_co_suspect_row() -> dict[str, Any]:
    return {
        "source_sfzh": "320102199001011234",
        "target_sfzh": "320102199002025678",
        "weight": 3,
        "first_case_date": datetime(2026, 1, 1),
        "last_case_date": datetime(2026, 5, 1),
        "case_types": "盗窃",
    }


def _make_trajectory_row(ts: str = "2026-05-10T10:00:00") -> dict[str, Any]:
    return {
        "sfzh": "320102199001011234",
        "shot_time": datetime.fromisoformat(ts),
        "shot_end_time": None,
        "longitude": 118.7969,
        "latitude": 32.0603,
        "location": "南京市鼓楼区",
        "phone": "13800138000",
        "station": "鼓楼分局",
        "bureau": "南京市公安局",
    }


# ---------------------------------------------------------------------------
# _fetch_person_rows
# ---------------------------------------------------------------------------


class TestFetchPersonRows:
    def test_normalizes_output(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        monkeypatch.setattr(etl, "fetch_all", lambda sql, params=None: [_make_person_row()])
        monkeypatch.setattr(etl, "table_exists", lambda s, t: True)

        rows, max_ts = etl._fetch_person_rows()

        assert len(rows) == 1
        assert rows[0]["sfzh"] == "320102199001011234"
        assert rows[0]["name"] == "Test"
        assert rows[0]["age"] is not None
        assert rows[0]["is_wcnr"] is False
        assert max_ts == "2026-05-10T08:00:00"

    def test_returns_empty_when_no_data(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        monkeypatch.setattr(etl, "fetch_all", _fake_fetch_all)

        rows, max_ts = etl._fetch_person_rows()

        assert rows == []
        assert max_ts == ""

    def test_passes_since_cursor_as_param(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        captured_sql = {}

        def capture_fetch(sql, params=None):
            captured_sql["sql"] = sql
            captured_sql["params"] = params
            return []

        monkeypatch.setattr(etl, "fetch_all", capture_fetch)

        etl._fetch_person_rows(since_cursor="2026-05-01T00:00:00")

        assert "COALESCE(x.xyrxx_lrsj, x.xyrxx_xgsj) >" in captured_sql["sql"]
        assert "2026-05-01T00:00:00" in (captured_sql["params"] or ())

    def test_max_ts_from_multiple_rows(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        rows_data = [
            _make_person_row("110101199001010001", "2026-05-08T10:00:00"),
            _make_person_row("110101199001010002", "2026-05-12T14:00:00"),
            _make_person_row("110101199001010003", "2026-05-10T08:00:00"),
        ]
        monkeypatch.setattr(etl, "fetch_all", lambda sql, params=None: rows_data)

        rows, max_ts = etl._fetch_person_rows()

        assert len(rows) == 3
        assert max_ts == "2026-05-12T14:00:00"


# ---------------------------------------------------------------------------
# _fetch_case_rows
# ---------------------------------------------------------------------------


class TestFetchCaseRows:
    def test_normalizes_output(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        monkeypatch.setattr(etl, "fetch_all", lambda sql, params=None: [_make_case_row()])

        rows, max_ts = etl._fetch_case_rows(theft_only=True)

        assert len(rows) == 1
        assert rows[0]["ajbh"] == "A20260101001"
        assert rows[0]["is_theft"] is True
        assert max_ts == "2026-05-10T09:00:00"

    def test_theft_filter_applied(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        captured_sql = {}

        def capture_fetch(sql, params=None):
            captured_sql["sql"] = sql
            return []

        monkeypatch.setattr(etl, "fetch_all", capture_fetch)

        etl._fetch_case_rows(theft_only=True)

        assert "盗" in captured_sql["sql"]


# ---------------------------------------------------------------------------
# _fetch_co_suspect_rows
# ---------------------------------------------------------------------------


class TestFetchCoSuspectRows:
    def test_returns_co_suspect_data(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        monkeypatch.setattr(etl, "fetch_all", lambda sql, params=None: [_make_co_suspect_row()])

        rows = etl._fetch_co_suspect_rows()

        assert len(rows) == 1
        assert rows[0]["source_sfzh"] == "320102199001011234"
        assert rows[0]["weight"] == 3
        assert rows[0]["first_case_date"] is not None


# ---------------------------------------------------------------------------
# _upsert_people batching
# ---------------------------------------------------------------------------


class TestUpsertPeople:
    def test_batches_500(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        call_count = []

        def fake_run_query(cypher, params=None):
            call_count.append(len(params.get("rows", [])))
            return []

        monkeypatch.setattr(etl, "run_query", fake_run_query)

        rows = [_make_person_row(f"11010119900101{i:04d}") for i in range(1200)]
        etl._upsert_people(rows)

        assert len(call_count) == 3
        assert call_count == [500, 500, 200]


# ---------------------------------------------------------------------------
# get_last_cursor
# ---------------------------------------------------------------------------


class TestGetLastCursor:
    def test_returns_none_when_no_history(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        monkeypatch.setattr(etl, "table_exists", lambda s, t: True)
        monkeypatch.setattr(etl, "fetch_one", lambda sql, params=None: None)

        result = etl.get_last_cursor()

        assert result is None

    def test_returns_none_when_table_missing(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        monkeypatch.setattr(etl, "table_exists", lambda s, t: False)

        result = etl.get_last_cursor()

        assert result is None

    def test_parses_json_cursor(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        cursor_data = {"person_ts": "2026-05-10T08:00:00", "case_ts": "2026-05-10T09:00:00", "trajectory_ts": "2026-05-10T10:00:00"}

        monkeypatch.setattr(etl, "table_exists", lambda s, t: True)
        monkeypatch.setattr(etl, "fetch_one", lambda sql, params=None: {"sync_cursor": json.dumps(cursor_data)})

        result = etl.get_last_cursor()

        assert result == cursor_data

    def test_returns_none_for_invalid_json(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        monkeypatch.setattr(etl, "table_exists", lambda s, t: True)
        monkeypatch.setattr(etl, "fetch_one", lambda sql, params=None: {"sync_cursor": "not-json"})

        result = etl.get_last_cursor()

        assert result is None


# ---------------------------------------------------------------------------
# run_graph_sync
# ---------------------------------------------------------------------------


class TestRunGraphSync:
    def test_full_sync_calls_all_fetches(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        fetch_calls = []
        upsert_calls = []

        def fake_fetch_person(limit=None, *, theft_only=True, since_cursor=""):
            fetch_calls.append("person")
            return [_make_person_row()], "2026-05-10T08:00:00"

        def fake_fetch_case(limit=None, *, theft_only=True, since_cursor=""):
            fetch_calls.append("case")
            return [_make_case_row()], "2026-05-10T09:00:00"

        def fake_fetch_same_case(limit=None, *, theft_only=True, since_cursor=""):
            fetch_calls.append("same_case")
            return [_make_same_case_row()], "2026-05-10T09:00:00"

        def fake_fetch_co_suspect(limit=None, *, theft_only=True):
            fetch_calls.append("co_suspect")
            return [_make_co_suspect_row()]

        def fake_fetch_trajectory(limit=None, *, since_cursor=""):
            fetch_calls.append("trajectory")
            return [_make_trajectory_row()], "2026-05-10T10:00:00"

        def fake_upsert(rows):
            upsert_calls.append(len(rows))

        monkeypatch.setattr(etl, "_fetch_person_rows", fake_fetch_person)
        monkeypatch.setattr(etl, "_fetch_case_rows", fake_fetch_case)
        monkeypatch.setattr(etl, "_fetch_same_case_rows", fake_fetch_same_case)
        monkeypatch.setattr(etl, "_fetch_co_suspect_rows", fake_fetch_co_suspect)
        monkeypatch.setattr(etl, "_fetch_trajectory_rows", fake_fetch_trajectory)
        monkeypatch.setattr(etl, "_upsert_people", fake_upsert)
        monkeypatch.setattr(etl, "_upsert_cases", fake_upsert)
        monkeypatch.setattr(etl, "_upsert_same_case_relationships", fake_upsert)
        monkeypatch.setattr(etl, "_upsert_co_suspect_relationships", fake_upsert)
        monkeypatch.setattr(etl, "_upsert_trajectory", fake_upsert)
        monkeypatch.setattr(etl, "_start_sync_log", lambda *a, **kw: 1)
        monkeypatch.setattr(etl, "_finish_sync_log", lambda *a, **kw: None)

        result = etl.run_graph_sync(limit=100, theft_only=True)

        assert result["ok"] is True
        assert result["incremental"] is False
        assert set(fetch_calls) == {"person", "case", "same_case", "co_suspect", "trajectory"}
        assert len(upsert_calls) == 5

    def test_incremental_sync_passes_cursor(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        cursor_data = {"person_ts": "2026-05-01T00:00:00", "case_ts": "2026-05-01T00:00:00", "trajectory_ts": "2026-05-01T00:00:00"}
        captured_cursors = {}

        def fake_fetch_person(limit=None, *, theft_only=True, since_cursor=""):
            captured_cursors["person"] = since_cursor
            return [], ""

        def fake_fetch_case(limit=None, *, theft_only=True, since_cursor=""):
            captured_cursors["case"] = since_cursor
            return [], ""

        def fake_fetch_same_case(limit=None, *, theft_only=True, since_cursor=""):
            captured_cursors["same_case"] = since_cursor
            return [], ""

        def fake_fetch_co_suspect(limit=None, *, theft_only=True):
            return []

        def fake_fetch_trajectory(limit=None, *, since_cursor=""):
            captured_cursors["trajectory"] = since_cursor
            return [], ""

        monkeypatch.setattr(etl, "get_last_cursor", lambda: cursor_data)
        monkeypatch.setattr(etl, "_fetch_person_rows", fake_fetch_person)
        monkeypatch.setattr(etl, "_fetch_case_rows", fake_fetch_case)
        monkeypatch.setattr(etl, "_fetch_same_case_rows", fake_fetch_same_case)
        monkeypatch.setattr(etl, "_fetch_co_suspect_rows", fake_fetch_co_suspect)
        monkeypatch.setattr(etl, "_fetch_trajectory_rows", fake_fetch_trajectory)
        monkeypatch.setattr(etl, "_upsert_people", lambda rows: None)
        monkeypatch.setattr(etl, "_upsert_cases", lambda rows: None)
        monkeypatch.setattr(etl, "_upsert_same_case_relationships", lambda rows: None)
        monkeypatch.setattr(etl, "_upsert_co_suspect_relationships", lambda rows: None)
        monkeypatch.setattr(etl, "_upsert_trajectory", lambda rows: None)
        monkeypatch.setattr(etl, "_start_sync_log", lambda *a, **kw: 1)
        monkeypatch.setattr(etl, "_finish_sync_log", lambda *a, **kw: None)

        result = etl.run_graph_sync(incremental=True)

        assert result["ok"] is True
        assert result["incremental"] is True
        assert captured_cursors["person"] == "2026-05-01T00:00:00"
        assert captured_cursors["case"] == "2026-05-01T00:00:00"
        assert captured_cursors["trajectory"] == "2026-05-01T00:00:00"

    def test_logs_failure_on_exception(self, monkeypatch):
        import modules.graph.services.etl_service as etl

        log_calls = []

        def fake_start_log(sync_type, source, sync_cursor=""):
            return 1

        def fake_finish_log(log_id, *, status, records_read=0, nodes_created=0, rels_created=0, error_msg="", sync_cursor=""):
            log_calls.append({"status": status, "error_msg": error_msg})

        def fake_fetch_person(limit=None, *, theft_only=True, since_cursor=""):
            raise RuntimeError("db connection failed")

        monkeypatch.setattr(etl, "_fetch_person_rows", fake_fetch_person)
        monkeypatch.setattr(etl, "_start_sync_log", fake_start_log)
        monkeypatch.setattr(etl, "_finish_sync_log", fake_finish_log)

        with pytest.raises(RuntimeError, match="db connection failed"):
            etl.run_graph_sync()

        assert len(log_calls) == 1
        assert log_calls[0]["status"] == "failed"
        assert "db connection failed" in log_calls[0]["error_msg"]
