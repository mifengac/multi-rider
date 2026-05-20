import json


class _FakeResponse:
    status = 200

    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_internal_dashboard_probe_writes_json(monkeypatch, tmp_path):
    from scripts.diagnostics import internal_dashboard_probe as probe

    def fake_query_one(sql, params=None):
        if "information_schema.tables" in sql:
            return {"exists": 1}
        if "MIN" in sql or "MAX" in sql:
            return {"rows": 1, "min_fasj": "2026-01-01", "max_fasj": "2026-05-20"}
        return {
            "rows": 1,
            "with_ssfj": 1,
            "with_csrq": 1,
            "distinct_ssfj": 1,
            "score_60": 1,
            "score_80": 0,
            "distinct_calc_days": 1,
            "recent_30d": 1,
            "valid_sfzh": 1,
            "with_yxx": 1,
        }

    def fake_query_all(sql, params=None):
        if "information_schema.columns" in sql:
            return [{"column_name": "zjhm"}, {"column_name": "xm"}]
        if "GROUP BY risk_level" in sql:
            return [{"risk_level": "high", "count": 1}]
        if "GROUP BY alert_type" in sql:
            return [{"alert_type": "high_risk_face_hit", "count": 1}]
        if "DISTINCT calc_time" in sql:
            return [{"calc_time": "2026-05-20"}]
        if "age_bucket" in sql:
            return [{"age_bucket": "14-15", "count": 1}]
        if "GROUP BY yxx" in sql:
            return [{"yxx": "第一中学", "count": 1}]
        return [{"zjhm": "441901200812045018", "xm": "张三"}]

    def fake_urlopen(request, timeout=10):
        url = request.full_url
        if "alerts" in url:
            raise OSError("service unavailable")
        return _FakeResponse({"items": [{"id": 1}], "points": [{"month": "2026-05"}]})

    out_path = tmp_path / "probe.json"
    monkeypatch.setattr(probe, "query_one", fake_query_one)
    monkeypatch.setattr(probe, "query_all", fake_query_all)
    monkeypatch.setattr(probe.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(probe.subprocess, "check_output", lambda *args, **kwargs: "abc123\n")

    exit_code = probe.main([
        "--base-url",
        "http://127.0.0.1:5001",
        "--zjhm",
        "441901200812045018",
        "--out",
        str(out_path),
    ])

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert set(payload) == {"meta", "db_probes", "api_probes"}
    assert payload["meta"]["git_head"] == "abc123"
    assert "wcnr_target_pool" in payload["db_probes"]
    assert "b_per_qscxwcnr" in payload["db_probes"]
    assert any("/api/graph/person/441901200812045018?depth=1" in item["url"] for item in payload["api_probes"])
    assert any(item["error"] == "service unavailable" for item in payload["api_probes"])
