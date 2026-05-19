from __future__ import annotations

from datetime import datetime


def test_graph_person_route_passes_filter_params(client, monkeypatch):
    import modules.graph.routes as graph_routes

    captured = {}

    def fake_build_person_graph(zjhm, depth=1, relations=None, time_range=None):
        captured.update({
            "zjhm": zjhm,
            "depth": depth,
            "relations": relations,
            "time_range": time_range,
        })
        return {"nodes": [{"id": f"P_{zjhm}"}], "edges": []}

    monkeypatch.setattr(graph_routes, "build_person_graph", fake_build_person_graph)

    response = client.get("/api/graph/person/4401?depth=9&relations=checked_in&time_range=6m")

    assert response.status_code == 200
    assert captured == {
        "zjhm": "4401",
        "depth": 3,
        "relations": "checked_in",
        "time_range": "6m",
    }


def test_graph_case_route_caps_depth_and_returns_not_found(client, monkeypatch):
    import modules.graph.routes as graph_routes

    captured = {}

    def fake_build_case_graph(ajbh, depth=1):
        captured.update({"ajbh": ajbh, "depth": depth})
        return {"nodes": [], "edges": []}

    monkeypatch.setattr(graph_routes, "build_case_graph", fake_build_case_graph, raising=False)

    response = client.get("/api/graph/case/AJ001?depth=9")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"
    assert captured == {"ajbh": "AJ001", "depth": 3}


def test_graph_expand_route_validates_body_and_calls_builder(client, monkeypatch):
    import modules.graph.routes as graph_routes

    missing = client.post("/api/graph/expand", json={"node_id": "P_1"})
    assert missing.status_code == 400

    captured = {}

    def fake_expand_node(node_id, node_type, direction="both"):
        captured.update({"node_id": node_id, "node_type": node_type, "direction": direction})
        return {"nodes": [{"id": "C_AJ001"}], "edges": []}

    monkeypatch.setattr(graph_routes, "expand_node", fake_expand_node, raising=False)

    response = client.post(
        "/api/graph/expand",
        json={"node_id": "P_1", "node_type": "person", "direction": "out"},
    )

    assert response.status_code == 200
    assert response.get_json()["nodes"][0]["id"] == "C_AJ001"
    assert captured == {"node_id": "P_1", "node_type": "person", "direction": "out"}


def test_graph_search_route_passes_type_param(client, monkeypatch):
    import modules.graph.routes as graph_routes

    captured = {}

    def fake_search_nodes(keyword, node_type=None):
        captured.update({"keyword": keyword, "node_type": node_type})
        return [{"id": "门口", "type": "location", "label": "门口"}]

    monkeypatch.setattr(graph_routes, "search_nodes", fake_search_nodes)

    response = client.get("/api/graph/search?keyword=%E9%97%A8&type=location")

    assert response.status_code == 200
    assert response.get_json()["results"][0]["type"] == "location"
    assert captured == {"keyword": "门", "node_type": "location"}


def test_build_person_graph_filters_relations_and_time_range(monkeypatch):
    import modules.graph.services.graph_builder as graph_builder

    calls = []

    monkeypatch.setattr(
        graph_builder,
        "query_one",
        lambda sql, params: {
            "zjhm": params["zjhm"],
            "xm": "张三",
            "total_score": 70,
            "risk_level": "high",
        },
    )

    def fake_cases(zjhm, nodes, edges, since=None):
        calls.append(("cases", since is not None))
        nodes["C_AJ001"] = {"id": "C_AJ001"}
        edges.append({"source": f"P_{zjhm}", "target": "C_AJ001", "type": "SUSPECTED_IN"})

    def fake_appeared(zjhm, nodes, edges):
        calls.append(("appeared", True))
        nodes["L_门口"] = {"id": "L_门口"}
        edges.append({"source": f"P_{zjhm}", "target": "L_门口", "type": "APPEARED_AT"})

    monkeypatch.setattr(graph_builder, "_add_cases", fake_cases)
    monkeypatch.setattr(graph_builder, "_add_co_suspects", lambda *args, **kwargs: calls.append(("co", True)))
    monkeypatch.setattr(graph_builder, "_add_guardian", lambda *args, **kwargs: calls.append(("guardian", True)))
    monkeypatch.setattr(graph_builder, "_add_school", lambda *args, **kwargs: calls.append(("school", True)))
    monkeypatch.setattr(graph_builder, "_add_appeared_at", fake_appeared, raising=False)
    monkeypatch.setattr(graph_builder, "_add_checked_in", lambda *args, **kwargs: calls.append(("hotel", True)), raising=False)

    result = graph_builder.build_person_graph(
        "4401",
        depth=1,
        relations="suspected_in,appeared_at",
        time_range="3m",
    )

    assert {"id": "C_AJ001"} in result["nodes"]
    assert calls == [("cases", True), ("appeared", True)]


def test_build_case_graph_adds_suspects_and_victims(monkeypatch):
    import modules.graph.services.graph_builder as graph_builder

    def fake_query_one(sql, params):
        if '"zq_zfba_ajxx"' in sql:
            return {
                "ajxx_ajbh": params["ajbh"],
                "ajxx_ajmc": "盗窃案",
                "ajxx_ay": "盗窃",
                "ajxx_fasj": datetime(2026, 5, 1, 8, 30),
            }
        return {"total_score": 80, "risk_level": "extreme"}

    def fake_query_all(sql, params):
        if '"zq_zfba_xyrxx"' in sql:
            return [{"xyrxx_sfzh": "S1", "xyrxx_xm": "嫌疑人"}]
        return []

    monkeypatch.setattr(graph_builder, "query_one", fake_query_one)
    monkeypatch.setattr(graph_builder, "query_all", fake_query_all)
    monkeypatch.setattr(
        graph_builder,
        "victims_of_case",
        lambda ajbh: [{"zjhm": "V1", "xm": "受害人"}],
        raising=False,
    )

    graph = graph_builder.build_case_graph("AJ001")

    assert {node["id"] for node in graph["nodes"]} == {"C_AJ001", "P_S1", "P_V1"}
    assert {edge["type"] for edge in graph["edges"]} == {"SUSPECTED_IN", "VICTIM_OF"}


def test_expand_node_person_uses_incremental_helpers(monkeypatch):
    import modules.graph.services.graph_builder as graph_builder

    def add_case(zjhm, nodes, edges, since=None):
        nodes["C_AJ001"] = {"id": "C_AJ001"}
        edges.append({"source": f"P_{zjhm}", "target": "C_AJ001", "type": "SUSPECTED_IN"})

    monkeypatch.setattr(graph_builder, "_add_cases", add_case)
    monkeypatch.setattr(graph_builder, "_add_co_suspects", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_guardian", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_school", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_appeared_at", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(graph_builder, "_add_checked_in", lambda *args, **kwargs: None, raising=False)

    result = graph_builder.expand_node("P_4401", "person")

    assert result == {
        "nodes": [{"id": "C_AJ001"}],
        "edges": [{"source": "P_4401", "target": "C_AJ001", "type": "SUSPECTED_IN"}],
    }


def test_search_nodes_supports_location_only(monkeypatch):
    import modules.graph.services.graph_builder as graph_builder

    captured = {}

    def fake_query_all(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [{"device_name": "学校门口"}]

    monkeypatch.setattr(graph_builder, "query_all", fake_query_all)

    results = graph_builder.search_nodes("学校", "location")

    assert results == [{"id": "学校门口", "type": "location", "label": "学校门口"}]
    assert '"jcgkzx_monitor"."wcnr_ryrl_gj"' in captured["sql"]


def test_relation_engine_helpers_return_graph_parts(monkeypatch):
    from modules.graph.services import relation_engine

    def fake_query_all(sql, params):
        if "wcnr_ryrl_gj" in sql:
            return [{"device_name": "路口", "count": 4, "last_time": datetime(2026, 5, 1)}]
        if "wcnr_ly_checkin" in sql:
            return [{"lgmc": "平安旅馆", "lgdz": "一号路", "count": 2, "last_time": datetime(2026, 5, 2)}]
        return [{"saryxx_sfzh": "V1", "saryxx_xm": "受害人"}]

    monkeypatch.setattr(relation_engine, "query_all", fake_query_all)

    assert relation_engine.appeared_at("4401")[0]["edge"]["type"] == "APPEARED_AT"
    assert relation_engine.checked_in("4401")[0]["node"]["type"] == "organization"
    assert relation_engine.victims_of_case("AJ001")[0]["zjhm"] == "V1"


def test_score_batch_recalculate_route_is_registered(client):
    rules = {str(rule) for rule in client.application.url_map.iter_rules()}
    assert "/api/score/batch-recalculate" in rules


def test_timeline_service_merges_sorts_and_drops_null_times(monkeypatch):
    from modules.profile.services import timeline_service

    def fake_query_all(sql, params):
        if '"zq_zfba_ajxx"' in sql:
            return [{"time": datetime(2026, 5, 1, 10), "title": "盗窃", "ajbh": "AJ001"}]
        if '"t_wcnrxwjl_xx"' in sql:
            return [{"time": None, "title": "无时间行为"}]
        if '"wcnr_ryrl_gj"' in sql:
            return [{"time": datetime(2026, 5, 3, 9), "title": "学校门口"}]
        return [{"time": datetime(2026, 5, 2, 8), "title": "平安旅馆"}]

    monkeypatch.setattr(timeline_service, "query_all", fake_query_all)

    timeline = timeline_service.build_timeline("4401")

    assert [item["type"] for item in timeline] == ["trajectory", "hotel", "case"]
    assert timeline[0]["time"] == "2026-05-03T09:00:00"


def test_profile_assemble_includes_gang_relation(monkeypatch):
    import modules.profile.services.profile_assembler as profile_assembler

    monkeypatch.setattr(profile_assembler, "get_basic_info", lambda zjhm: {"zjhm": zjhm, "xm": "中心"})
    monkeypatch.setattr(profile_assembler, "get_photo", lambda zjhm: {})
    monkeypatch.setattr(profile_assembler, "get_family_info", lambda zjhm: {})
    monkeypatch.setattr(profile_assembler, "get_education_info", lambda zjhm: {})
    monkeypatch.setattr(profile_assembler, "get_cases", lambda zjhm: [])
    monkeypatch.setattr(profile_assembler, "get_behaviors", lambda zjhm: [])
    monkeypatch.setattr(profile_assembler, "get_hotel_records", lambda zjhm: [])
    monkeypatch.setattr(profile_assembler, "get_score_info", lambda zjhm: {})
    monkeypatch.setattr(profile_assembler, "get_score_trend", lambda zjhm, months: [], raising=False)
    monkeypatch.setattr(
        profile_assembler,
        "get_co_suspects",
        lambda zjhm: [{"zjhm": "A", "xm": "甲"}, {"zjhm": "B", "xm": "乙"}],
    )
    monkeypatch.setattr(
        profile_assembler,
        "query_all",
        lambda sql, params: [
            {"ajbh": "AJ001", "zjhm": "4401", "xm": "中心"},
            {"ajbh": "AJ001", "zjhm": "A", "xm": "甲"},
            {"ajbh": "AJ001", "zjhm": "B", "xm": "乙"},
        ],
    )

    profile = profile_assembler.assemble_profile("4401")

    assert profile["relations"]["gang"] == {
        "is_gang": True,
        "size": 3,
        "members": [
            {"zjhm": "4401", "xm": "中心"},
            {"zjhm": "A", "xm": "甲"},
            {"zjhm": "B", "xm": "乙"},
        ],
    }


def test_dashboard_heatmap_service_returns_weighted_grid(monkeypatch):
    from modules.dashboard.services import heatmap_service

    monkeypatch.setattr(
        heatmap_service,
        "query_all",
        lambda sql, params: [{"lng": 113.123, "lat": 23.456, "weight": 7}],
    )

    assert heatmap_service.get_heatmap(7) == [{"lng": 113.123, "lat": 23.456, "weight": 7}]


def test_dashboard_ranking_supports_school(client, monkeypatch):
    import modules.dashboard.routes as dashboard_routes

    monkeypatch.setattr(dashboard_routes, "get_area_distribution", lambda: [{"label": "分局", "value": 1}])
    monkeypatch.setattr(
        dashboard_routes,
        "get_school_ranking",
        lambda metric="risk_count": [{"label": "第一中学", "value": 2}],
        raising=False,
    )

    response = client.get("/api/dashboard/ranking?by=school&metric=risk_count")

    assert response.status_code == 200
    assert response.get_json() == {
        "by": "school",
        "metric": "risk_count",
        "items": [{"label": "第一中学", "value": 2}],
    }


def test_models_packages_export_lightweight_dataclasses():
    from modules.dashboard.models import DashboardItem
    from modules.graph.models import GraphEdge, GraphNode
    from modules.profile.models import TimelineEvent
    from modules.score.models import ScoreResult

    assert GraphNode(id="P_1", type="person", label="张三").to_dict()["id"] == "P_1"
    assert GraphEdge(source="P_1", target="C_1", type="SUSPECTED_IN").to_dict()["type"] == "SUSPECTED_IN"
    assert ScoreResult(zjhm="P_1", total_score=70, risk_level="high").to_dict()["total_score"] == 70
    assert TimelineEvent(time="2026-05-01T00:00:00", type="case", title="案件").to_dict()["type"] == "case"
    assert DashboardItem(label="分局", value=3).to_dict()["value"] == 3


def test_alert_rule_engine_scans_high_risk_face_hit_and_skips_duplicate(monkeypatch):
    from modules.dashboard.services import alert_rule_engine

    shot_time = datetime(2026, 5, 18, 23, 0)
    inserted = []
    duplicate = {"exists": False}

    def fake_query_one(sql, params=None):
        params = params or {}
        if "information_schema.tables" in sql:
            return {"exists": 1}
        if params.get("alert_type") == "high_risk_face_hit":
            return {"id": 1} if duplicate["exists"] else {}
        return {}

    monkeypatch.setattr(alert_rule_engine, "query_one", fake_query_one)
    monkeypatch.setattr(
        alert_rule_engine,
        "query_all",
        lambda sql, params=None: [
            {
                "zjhm": "4401",
                "xm": "张三",
                "device_name": "学校门口",
                "shot_time": shot_time,
                "total_score": 88,
            }
        ],
    )
    monkeypatch.setattr(alert_rule_engine, "execute", lambda sql, params=None: inserted.append(params) or 1)

    assert alert_rule_engine.scan_high_risk_face_hit(5) == 1
    assert inserted[0]["alert_type"] == "high_risk_face_hit"
    assert inserted[0]["alert_level"] == "critical"
    assert "张三 在 学校门口 出现" in inserted[0]["alert_content"]

    duplicate["exists"] = True
    assert alert_rule_engine.scan_high_risk_face_hit(5) == 0


def test_alert_rule_engine_scans_night_aggregation_and_skips_duplicate(monkeypatch):
    from modules.dashboard.services import alert_rule_engine

    inserted = []

    def fake_query_one(sql, params=None):
        params = params or {}
        if "information_schema.tables" in sql:
            return {"exists": 1}
        if params.get("alert_type") == "night_aggregation":
            return {"id": 9}
        return {}

    monkeypatch.setattr(alert_rule_engine, "query_one", lambda sql, params=None: {"exists": 1} if "information_schema.tables" in sql else {})
    monkeypatch.setattr(
        alert_rule_engine,
        "query_all",
        lambda sql, params=None: [
            {
                "device_name": "网吧门口",
                "person_count": 3,
                "high_risk_count": 2,
                "last_time": datetime(2026, 5, 18, 23, 30),
                "names": "张三、李四、王五",
            }
        ],
    )
    monkeypatch.setattr(alert_rule_engine, "execute", lambda sql, params=None: inserted.append(params) or 1)

    assert alert_rule_engine.scan_night_aggregation() == 1
    assert inserted[0]["alert_type"] == "night_aggregation"
    assert inserted[0]["alert_level"] == "warning"

    monkeypatch.setattr(alert_rule_engine, "query_one", fake_query_one)
    assert alert_rule_engine.scan_night_aggregation() == 0


def test_alert_rule_engine_scans_abnormal_hotel_checkin_and_degrades(monkeypatch):
    from modules.dashboard.services import alert_rule_engine

    inserted = []
    missing_table = {"name": None}

    def fake_query_one(sql, params=None):
        params = params or {}
        if "information_schema.tables" in sql:
            return {} if params.get("t") == missing_table["name"] else {"exists": 1}
        return {}

    monkeypatch.setattr(alert_rule_engine, "query_one", fake_query_one)
    monkeypatch.setattr(
        alert_rule_engine,
        "query_all",
        lambda sql, params=None: [
            {
                "zjhm": "4401",
                "xm": "张三",
                "lgmc": "平安旅馆",
                "lgdz": "一号路",
                "rzsj": datetime(2026, 5, 18, 21, 0),
                "tfrxm": None,
                "jhr1xm": "监护人",
            }
        ],
    )
    monkeypatch.setattr(alert_rule_engine, "execute", lambda sql, params=None: inserted.append(params) or 1)

    assert alert_rule_engine.scan_abnormal_hotel_checkin() == 1
    assert inserted[0]["alert_type"] == "abnormal_hotel_checkin"

    missing_table["name"] = "wcnr_ly_checkin"
    assert alert_rule_engine.scan_abnormal_hotel_checkin() == 0


def test_dashboard_alert_scan_route_calls_rule_engine(client, monkeypatch):
    import modules.dashboard.routes as dashboard_routes

    expected = {"high_risk_face_hit": 1, "night_aggregation": 2, "abnormal_hotel_checkin": 3}
    monkeypatch.setattr(dashboard_routes, "run_all_rules", lambda: expected, raising=False)

    response = client.post("/api/dashboard/alerts/scan")

    assert response.status_code == 200
    assert response.get_json() == {"result": expected}


def test_monthly_decay_updates_scores_and_risk_level(monkeypatch):
    import modules.score.services.score_engine as score_engine

    captured = {}

    def fake_execute(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return 4

    monkeypatch.setattr(score_engine, "execute", fake_execute, raising=False)

    assert score_engine.monthly_decay(2) == {"updated": 4}
    assert 'UPDATE "jcgkzx_monitor"."wcnr_score"' in captured["sql"]
    assert "GREATEST(total_score - %(decrement)s, 0)" in captured["sql"]
    assert "CASE" in captured["sql"]
    assert captured["params"] == {"decrement": 2}


def test_profile_assemble_includes_score_trend(monkeypatch):
    import modules.profile.services.profile_assembler as profile_assembler

    monkeypatch.setattr(profile_assembler, "get_basic_info", lambda zjhm: {"zjhm": zjhm, "xm": "张三"})
    monkeypatch.setattr(profile_assembler, "get_photo", lambda zjhm: {})
    monkeypatch.setattr(profile_assembler, "get_family_info", lambda zjhm: {})
    monkeypatch.setattr(profile_assembler, "get_education_info", lambda zjhm: {})
    monkeypatch.setattr(profile_assembler, "get_cases", lambda zjhm: [])
    monkeypatch.setattr(profile_assembler, "get_behaviors", lambda zjhm: [])
    monkeypatch.setattr(profile_assembler, "get_hotel_records", lambda zjhm: [])
    monkeypatch.setattr(profile_assembler, "get_score_info", lambda zjhm: {})
    monkeypatch.setattr(profile_assembler, "get_co_suspects", lambda zjhm: [])
    monkeypatch.setattr(profile_assembler, "detect_gang", lambda zjhm, xm, co: {"is_gang": False, "size": 0, "members": []})
    monkeypatch.setattr(
        profile_assembler,
        "get_score_trend",
        lambda zjhm, months: [{"total_score": 72, "risk_level": "high", "calc_time": "2026-05-01"}],
        raising=False,
    )

    profile = profile_assembler.assemble_profile("4401")

    assert profile["score_trend"] == [{"total_score": 72, "risk_level": "high", "calc_time": "2026-05-01"}]


def test_dashboard_summary_adds_change_fields_and_degrades_missing_optional_tables(monkeypatch):
    from modules.dashboard.services import summary_service

    def fake_query_one(sql, params=None):
        params = params or {}
        if "information_schema.tables" in sql:
            return {}
        if 'COUNT(*) AS total FROM "jcgkzx_monitor"."wcnr_target_pool"' in sql:
            return {"total": 100}
        if 'COUNT(*) AS total FROM "jcgkzx_monitor"."wcnr_score"' in sql and "total_score >= 60" in sql:
            return {"total": 20}
        if 'COUNT(*) AS total FROM "jcgkzx_monitor"."wcnr_score"' in sql and "total_score >= 80" in sql:
            return {"total": 5}
        if "ROUND(AVG(total_score), 1)" in sql:
            return {"avg_score": 66.6}
        if "DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'" in sql:
            return {"total": 4}
        if "DATE_TRUNC('month', CURRENT_DATE)" in sql:
            return {"total": 6}
        return {"total": 0}

    monkeypatch.setattr(summary_service, "query_one", fake_query_one)

    summary = summary_service.get_summary()

    assert summary["month_cases"] == 6
    assert summary["month_cases_prev"] == 4
    assert summary["month_cases_change_pct"] == 50.0
    assert summary["high_risk_count_prev"] is None
    assert summary["high_risk_count_change_pct"] is None
    assert "visit_total_month" not in summary
    assert "visit_pass_rate" not in summary


def test_relation_engine_new_relationships_return_graph_parts(monkeypatch):
    from modules.graph.services import relation_engine

    def fake_query_one(sql, params=None):
        if "wcnr_czrk" in sql:
            return {"hjdz": "户籍路1号", "xzdxz": "现住路2号"}
        if "b_per_qscxwcnr" in sql:
            return {"yxx": "第一中学"}
        if "wcnr_target_pool" in sql:
            return {"sspcs": "南山派出所"}
        return {}

    def fake_query_all(sql, params=None):
        if "b_per_qscxwcnr" in sql:
            return [{"zjhm": "4402", "xm": "李四"}]
        if "wcnr_target_pool" in sql:
            return [{"zjhm": "4403", "xm": "王五"}]
        return []

    monkeypatch.setattr(relation_engine, "query_one", fake_query_one, raising=False)
    monkeypatch.setattr(relation_engine, "query_all", fake_query_all)

    assert relation_engine.lives_at("4401")[0]["edge"]["type"] == "LIVES_AT"
    assert relation_engine.same_school("4401")[0]["edge"]["type"] == "SAME_SCHOOL"
    assert relation_engine.same_area("4401")[0]["edge"]["type"] == "SAME_AREA"


def test_build_person_graph_enables_new_relations_only_when_explicit(monkeypatch):
    import modules.graph.services.graph_builder as graph_builder

    calls = []
    monkeypatch.setattr(
        graph_builder,
        "query_one",
        lambda sql, params: {
            "zjhm": params["zjhm"],
            "xm": "张三",
            "total_score": 70,
            "risk_level": "high",
        },
    )
    monkeypatch.setattr(graph_builder, "_add_cases", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_co_suspects", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_guardian", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_school", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_appeared_at", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_checked_in", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_lives_at", lambda *args, **kwargs: calls.append("lives_at"), raising=False)
    monkeypatch.setattr(graph_builder, "_add_same_school", lambda *args, **kwargs: calls.append("same_school"), raising=False)
    monkeypatch.setattr(graph_builder, "_add_same_area", lambda *args, **kwargs: calls.append("same_area"), raising=False)

    graph_builder.build_person_graph("4401")
    assert calls == []

    graph_builder.build_person_graph("4401", relations="lives_at,same_school,same_area")
    assert calls == ["lives_at", "same_school", "same_area"]
