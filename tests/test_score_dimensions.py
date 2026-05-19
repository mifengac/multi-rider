from __future__ import annotations

import sys
from pathlib import Path


def test_family_score_uses_columns_present_in_local_qskj_schema(monkeypatch):
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from modules.score.services import dim_family

    captured = {}

    def fake_query_one(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return {}

    monkeypatch.setattr(dim_family, "query_one", fake_query_one)

    score, detail = dim_family.calc_family_score("441702201202196991")

    assert score == 0
    assert detail == {"source": "no_data"}
    assert "qttsqk AS jtqk" in captured["sql"]
    assert "jhr1xm" in captured["sql"]
    assert "jhr1lxdh" in captured["sql"]
    assert "NULL::VARCHAR AS fmsftswc" in captured["sql"]
    assert "SELECT jtqk, knjtlx, etlb, fmsftswc, jhr1xm, jhr1lxdh" not in captured["sql"]


def test_profile_dropout_education_query_uses_real_dropout_columns(monkeypatch):
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from modules.profile.services import profile_assembler

    captured = {}

    def fake_query_one(sql, params):
        captured.setdefault("sql", sql)
        return {"zjhm": params["zjhm"], "xm": "test"}

    monkeypatch.setattr(profile_assembler, "query_one", fake_query_one)

    education = profile_assembler.get_education_info("441702201202196991")

    assert education["status"] == "dropout"
    assert "NULL::VARCHAR AS yxx" in captured["sql"]
    assert "NULL::VARCHAR AS nj" in captured["sql"]
    assert "NULL::VARCHAR AS ssbm" in captured["sql"]
    assert "SELECT zjhm, xm, yxx, nj, jxqk, ssbm" not in captured["sql"]
