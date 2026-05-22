from __future__ import annotations


def test_validators_accept_expected_values():
    from shared.validators import (
        validate_depth,
        validate_int_range,
        validate_relations,
        validate_time_range,
        validate_zjhm,
    )

    assert validate_zjhm("441901200812045018") is True
    assert validate_zjhm("11010519491231002X") is True
    assert validate_zjhm("130503670401001") is True
    assert validate_zjhm("4401") is False
    assert validate_zjhm("44190120081204501A") is False

    assert validate_depth(1) is True
    assert validate_depth(3) is True
    assert validate_depth(0) is False
    assert validate_depth(4) is False

    assert validate_relations("suspected_in,checked_in") is True
    assert validate_relations("all") is True
    assert validate_relations("none") is True
    assert validate_relations("suspected_in,unknown") is False

    assert validate_time_range(None) is True
    assert validate_time_range("6m") is True
    assert validate_time_range("2y") is False

    assert validate_int_range(20, 1, 100) is True
    assert validate_int_range(None, 1, 100) is False
    assert validate_int_range(0, 1, 100) is False


def test_core_routes_reject_invalid_query_params(client):
    invalid_zjhm_response = client.get("/api/graph/person/4401")
    assert invalid_zjhm_response.status_code == 400
    assert invalid_zjhm_response.get_json()["error"] == "invalid_zjhm"

    invalid_depth_response = client.get("/api/graph/case/AJ001?depth=0")
    assert invalid_depth_response.status_code == 400
    assert invalid_depth_response.get_json()["error"] == "invalid_depth"

    invalid_score_response = client.get("/api/score/list?min_score=90&max_score=10")
    assert invalid_score_response.status_code == 400
    assert invalid_score_response.get_json()["error"] == "invalid_score_range"

    invalid_profile_response = client.get("/api/profile/4401/trajectory?days=30")
    assert invalid_profile_response.status_code == 400
    assert invalid_profile_response.get_json()["error"] == "invalid_zjhm"

    invalid_dashboard_response = client.get("/api/dashboard/trend?months=0&metric=cases")
    assert invalid_dashboard_response.status_code == 400
    assert invalid_dashboard_response.get_json()["error"] == "invalid_months"


def test_run_migrations_executes_versioned_sql_in_order(monkeypatch, tmp_path):
    from scripts import run_migrations

    calls: list[str] = []
    (tmp_path / "v1_1_sample_data.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / "v1_0_init_tables.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "notes.sql").write_text("SELECT 3;", encoding="utf-8")

    monkeypatch.setattr(run_migrations, "execute", lambda sql: calls.append(sql) or 0)

    assert run_migrations.run_migrations(str(tmp_path)) is True
    assert calls == ["SELECT 1;", "SELECT 2;"]
