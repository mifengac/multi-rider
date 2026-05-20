from __future__ import annotations

from datetime import datetime
import threading


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

    response = client.get("/api/graph/person/441901200812045018?depth=3&relations=checked_in&time_range=6m")

    assert response.status_code == 200
    assert captured == {
        "zjhm": "441901200812045018",
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

    response = client.get("/api/graph/case/AJ001?depth=3")

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


def test_add_school_skips_undefined_column(monkeypatch):
    import psycopg2
    import modules.graph.services.graph_builder as graph_builder

    def fake_query_one(sql, params=None):
        raise psycopg2.errors.UndefinedColumn("column yxx does not exist")

    monkeypatch.setattr(graph_builder, "query_one", fake_query_one)

    nodes = {"P_4401": {"id": "P_4401"}}
    edges = []

    graph_builder._add_school("4401", nodes, edges)

    assert nodes == {"P_4401": {"id": "P_4401"}}
    assert edges == []


def test_build_person_graph_skips_failed_child_query_but_keeps_other_relations(monkeypatch):
    import psycopg2
    import modules.graph.services.graph_builder as graph_builder

    def fake_query_one(sql, params=None):
        if '"jcgkzx_monitor"."wcnr_target_pool"' in sql:
            return {
                "zjhm": params["zjhm"],
                "xm": "张三",
                "total_score": 70,
                "risk_level": "high",
            }
        raise psycopg2.errors.UndefinedColumn("column yxx does not exist")

    def fake_cases(zjhm, nodes, edges, since=None):
        nodes["C_AJ001"] = {"id": "C_AJ001"}
        edges.append({"source": f"P_{zjhm}", "target": "C_AJ001", "type": "SUSPECTED_IN"})

    monkeypatch.setattr(graph_builder, "query_one", fake_query_one)
    monkeypatch.setattr(graph_builder, "_add_cases", fake_cases)
    monkeypatch.setattr(graph_builder, "_add_co_suspects", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_guardian", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_appeared_at", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_builder, "_add_checked_in", lambda *args, **kwargs: None)

    graph = graph_builder.build_person_graph("4401", relations="suspected_in,studies_at")

    assert {node["id"] for node in graph["nodes"]} == {"P_4401", "C_AJ001"}
    assert graph["edges"] == [{"source": "P_4401", "target": "C_AJ001", "type": "SUSPECTED_IN"}]


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


def test_build_case_graph_adds_related_case_edges_when_depth_enabled(monkeypatch):
    import modules.graph.services.graph_builder as graph_builder

    def fake_query_one(sql, params):
        if '"zq_zfba_ajxx"' in sql:
            return {
                "ajxx_ajbh": params["ajbh"],
                "ajxx_ajmc": "中心盗窃案",
                "ajxx_ay": "盗窃",
                "ajxx_fasj": datetime(2026, 5, 10, 8, 30),
                "ajxx_cbdw_mc": "南山分局一所",
                "ssfj": "南山分局",
            }
        return {}

    def fake_query_all(sql, params=None):
        if '"zq_zfba_xyrxx"' in sql:
            return []
        if "RELATED_CASE" in sql or "ajxx_fasj BETWEEN" in sql:
            return [
                {
                    "ajxx_ajbh": "AJ002",
                    "ajxx_ajmc": "相似盗窃案",
                    "ajxx_ay": "盗窃",
                    "ajxx_fasj": datetime(2026, 5, 15, 9, 0),
                    "ajxx_cbdw_mc": "南山分局二所",
                    "ssfj": "南山分局",
                },
                {
                    "ajxx_ajbh": "AJ003",
                    "ajxx_ajmc": "同类盗窃案",
                    "ajxx_ay": "盗窃",
                    "ajxx_fasj": datetime(2026, 5, 20, 9, 0),
                    "ajxx_cbdw_mc": "南山分局三所",
                    "ssfj": "南山分局",
                },
            ]
        return []

    monkeypatch.setattr(graph_builder, "query_one", fake_query_one)
    monkeypatch.setattr(graph_builder, "query_all", fake_query_all)
    monkeypatch.setattr(graph_builder, "victims_of_case", lambda ajbh: [], raising=False)

    graph = graph_builder.build_case_graph("AJ001", depth=1)

    assert {"C_AJ001", "C_AJ002", "C_AJ003"} <= {node["id"] for node in graph["nodes"]}
    related_edges = [edge for edge in graph["edges"] if edge["type"] == "RELATED_CASE"]
    assert {edge["target"] for edge in related_edges} == {"C_AJ002", "C_AJ003"}
    assert all(edge["style"]["stroke"] == "#a78bfa" for edge in related_edges)
    assert all(edge["style"]["lineDash"] == [4, 4] for edge in related_edges)

    graph_depth_zero = graph_builder.build_case_graph("AJ001", depth=0)
    assert "RELATED_CASE" not in {edge["type"] for edge in graph_depth_zero["edges"]}


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


def test_alert_rule_engine_scans_school_perimeter(monkeypatch):
    from modules.dashboard.services import alert_rule_engine

    inserted = []

    def fake_query_one(sql, params=None):
        params = params or {}
        if "information_schema.tables" in sql:
            return {"exists": 1}
        if params.get("alert_type") == "school_perimeter_high_risk":
            return {}
        return {}

    def fake_query_all(sql, params=None):
        if "information_schema.columns" in sql:
            return [{"column_name": "xxmc"}, {"column_name": "jd"}, {"column_name": "wd"}]
        return [
            {
                "zjhm": "4401",
                "xm": "张三",
                "xxmc": "第一中学",
                "dist": 123.4,
                "shot_time": datetime(2026, 5, 18, 8, 30),
            }
        ]

    monkeypatch.setattr(alert_rule_engine, "query_one", fake_query_one)
    monkeypatch.setattr(alert_rule_engine, "query_all", fake_query_all)
    monkeypatch.setattr(alert_rule_engine, "execute", lambda sql, params=None: inserted.append(params) or 1)

    assert alert_rule_engine.scan_school_perimeter(200) == 1
    assert inserted[0]["alert_type"] == "school_perimeter_high_risk"
    assert inserted[0]["alert_level"] == "warning"
    assert "张三 出现在学校 第一中学 周边 ~123米" == inserted[0]["alert_content"]


def test_alert_rule_engine_scans_speeding_detection(monkeypatch):
    from modules.dashboard.services import alert_rule_engine

    inserted = []

    monkeypatch.setattr(alert_rule_engine, "_table_exists", lambda schema, table: True)
    monkeypatch.setattr(
        alert_rule_engine,
        "_call_detection_repository",
        lambda window_minutes, min_confidence: [
            {
                "category": "飙车",
                "confidence": 0.86,
                "device_id": "DEV001",
                "source_name": "路口摄像头",
                "trigger_time": datetime(2026, 5, 18, 9, 0),
            }
        ],
    )
    monkeypatch.setattr(alert_rule_engine, "query_one", lambda sql, params=None: {})
    monkeypatch.setattr(alert_rule_engine, "execute", lambda sql, params=None: inserted.append(params) or 1)

    assert alert_rule_engine.scan_speeding_detection() == 1
    assert inserted[0]["alert_type"] == "speeding_detected"
    assert inserted[0]["alert_level"] == "warning"
    assert inserted[0]["alert_content"] == "飙车检测命中 device=DEV001"


def test_alert_rule_engine_run_all_rules_includes_round3_rules(monkeypatch):
    from modules.dashboard.services import alert_rule_engine

    monkeypatch.setattr(alert_rule_engine, "scan_high_risk_face_hit", lambda: 1)
    monkeypatch.setattr(alert_rule_engine, "scan_night_aggregation", lambda: 2)
    monkeypatch.setattr(alert_rule_engine, "scan_abnormal_hotel_checkin", lambda: 3)
    monkeypatch.setattr(alert_rule_engine, "scan_school_perimeter", lambda: 4)
    monkeypatch.setattr(alert_rule_engine, "scan_speeding_detection", lambda: 5)

    assert alert_rule_engine.run_all_rules() == {
        "high_risk_face_hit": 1,
        "night_aggregation": 2,
        "abnormal_hotel_checkin": 3,
        "school_perimeter_high_risk": 4,
        "speeding_detected": 5,
    }


def test_dashboard_alert_scan_route_calls_rule_engine(client, monkeypatch):
    import modules.dashboard.routes as dashboard_routes

    expected = {"high_risk_face_hit": 1, "night_aggregation": 2, "abnormal_hotel_checkin": 3}
    monkeypatch.setattr(dashboard_routes, "run_all_rules", lambda: expected, raising=False)

    response = client.post("/api/dashboard/alerts/scan")

    assert response.status_code == 200
    assert response.get_json() == {"result": expected}


def test_dashboard_alert_stream_sends_parseable_sse(client, monkeypatch):
    import json
    import modules.dashboard.routes as dashboard_routes

    monkeypatch.setattr(
        dashboard_routes,
        "get_recent_alerts",
        lambda limit=5: [
            {
                "id": 7,
                "zjhm": "4401",
                "xm": "张三",
                "alert_type": "high_risk_face_hit",
                "alert_level": "critical",
                "alert_content": "张三 在 学校门口 出现",
                "location": "学校门口",
                "trigger_time": "2026-05-18T23:00:00",
            }
        ],
        raising=False,
    )

    response = client.get("/api/dashboard/alerts/stream", buffered=False)
    first_chunk = next(response.response).decode("utf-8")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert first_chunk.startswith("data: ")
    assert json.loads(first_chunk.removeprefix("data: ").strip())["id"] == 7
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Accel-Buffering"] == "no"


def test_dashboard_dispatch_from_person_validates_target_and_returns_redirect(client, monkeypatch):
    import modules.dashboard.routes as dashboard_routes

    captured = {}

    def fake_query_one(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return {"zjhm": params["zjhm"], "xm": "张三"}

    monkeypatch.setattr(dashboard_routes, "query_one", fake_query_one, raising=False)

    response = client.post("/api/dashboard/dispatch/from-person", json={"zjhm": "441901200812045018"})

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "zjhm": "441901200812045018",
        "redirect": "/dispatch?zjhm=441901200812045018",
    }
    assert '"jcgkzx_monitor"."wcnr_target_pool"' in captured["sql"]


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


def test_score_incremental_recalculate_only_updates_stale_people(monkeypatch):
    import modules.score.services.score_engine as score_engine

    new_time = datetime(2026, 5, 19, 10, 0)
    calculated = []

    monkeypatch.setattr(
        score_engine,
        "query_all",
        lambda sql, params=None: [
            {"zjhm": "A", "last_event_time": new_time, "calc_time": None},
            {"zjhm": "B", "last_event_time": new_time, "calc_time": datetime(2026, 5, 19, 9, 0)},
            {"zjhm": "C", "last_event_time": new_time, "calc_time": datetime(2026, 5, 19, 11, 0)},
        ],
    )
    monkeypatch.setattr(score_engine, "calculate_score", lambda zjhm: calculated.append(zjhm) or {"zjhm": zjhm})

    assert score_engine.incremental_recalculate(15) == {"scanned": 3, "recalculated": 2}
    assert calculated == ["A", "B"]


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


def test_startup_alert_seed_runs_async_when_enabled(monkeypatch):
    import app as app_module

    event = threading.Event()
    calls = []

    def fake_run_all_rules():
        calls.append("called")
        event.set()
        return {"count": 3}

    monkeypatch.setenv("WCNR_SEED_ALERTS_ON_START", "1")
    monkeypatch.setattr(app_module, "run_all_rules", fake_run_all_rules, raising=False)

    app_module.create_app()

    assert event.wait(1)
    assert calls == ["called"]


def test_startup_alert_seed_skips_when_disabled(monkeypatch):
    import app as app_module

    event = threading.Event()

    def fake_run_all_rules():
        event.set()
        return {"count": 3}

    monkeypatch.setenv("WCNR_SEED_ALERTS_ON_START", "0")
    monkeypatch.setattr(app_module, "run_all_rules", fake_run_all_rules, raising=False)

    app_module.create_app()

    assert not event.wait(0.2)


def test_region_extracts_six_digit_code():
    from shared.region import extract_region_code

    assert extract_region_code("445302200901010011") == "445302"
    assert extract_region_code("ABC302200901010011") is None
    assert extract_region_code("44530") is None


def test_area_distribution_degrades_to_zjhm_region_code(monkeypatch):
    from modules.dashboard.services import distribution_service

    calls = []

    def fake_query_all(sql, params=None):
        calls.append(sql)
        if len(calls) == 1:
            return []
        return [{"label": "Luoding", "value": 12}]

    monkeypatch.setattr(distribution_service, "query_all", fake_query_all)
    monkeypatch.setattr(distribution_service, "_table_exists", lambda schema, table: True, raising=False)

    assert distribution_service.get_area_distribution("risk_count") == [{"label": "Luoding", "value": 12}]
    assert len(calls) == 2
    assert "LEFT(s.zjhm, 6)" in calls[1]
    assert '"stdata"."b_dic_zzjgdm"' in calls[1]


def test_age_distribution_degrades_to_zjhm_birthdate(monkeypatch):
    from modules.dashboard.services import distribution_service

    calls = []

    def fake_query_all(sql, params=None):
        calls.append(sql)
        if len(calls) == 1:
            return []
        return [{"label": "14-16岁", "value": 4}]

    monkeypatch.setattr(distribution_service, "query_all", fake_query_all)

    assert distribution_service.get_age_distribution() == [{"label": "14-16岁", "value": 4}]
    assert len(calls) == 2
    assert "SUBSTR(zjhm, 7, 8)" in calls[1]
    assert "~ '^[0-9]{8}$'" in calls[1]


def test_case_type_distribution_returns_degraded_false_when_age_filter_hits(monkeypatch):
    from modules.dashboard.services import distribution_service

    calls = []

    def fake_query_all(sql, params=None):
        calls.append(sql)
        return [{"label": "theft", "value": 2}]

    monkeypatch.delenv("WCNR_AGE_FILTER", raising=False)
    monkeypatch.setattr(distribution_service, "query_all", fake_query_all)

    assert distribution_service.get_case_type_distribution() == {
        "items": [{"label": "theft", "value": 2}],
        "degraded": False,
    }
    assert len(calls) == 1
    assert "DATE_PART('year'" in calls[0]
    assert "< 18" in calls[0]


def test_case_type_distribution_requeries_without_age_filter_when_empty(monkeypatch):
    from modules.dashboard.services import distribution_service

    calls = []

    def fake_query_all(sql, params=None):
        calls.append(sql)
        if len(calls) == 1:
            return []
        return [{"label": "robbery", "value": 5}]

    monkeypatch.delenv("WCNR_AGE_FILTER", raising=False)
    monkeypatch.setattr(distribution_service, "query_all", fake_query_all)

    assert distribution_service.get_case_type_distribution() == {
        "items": [{"label": "robbery", "value": 5}],
        "degraded": True,
    }
    assert len(calls) == 2
    assert "DATE_PART('year'" in calls[0]
    assert "DATE_PART('year'" not in calls[1]


def test_case_type_distribution_skips_age_filter_when_env_zero(monkeypatch):
    from modules.dashboard.services import distribution_service

    calls = []

    def fake_query_all(sql, params=None):
        calls.append(sql)
        return [{"label": "all_cases", "value": 7}]

    monkeypatch.setenv("WCNR_AGE_FILTER", "0")
    monkeypatch.setattr(distribution_service, "query_all", fake_query_all)

    assert distribution_service.get_case_type_distribution() == {
        "items": [{"label": "all_cases", "value": 7}],
        "degraded": False,
    }
    assert len(calls) == 1
    assert "DATE_PART('year'" not in calls[0]


def test_case_trend_degrades_when_age_filter_returns_empty(monkeypatch):
    from modules.dashboard.services import trend_service

    calls = []

    def fake_query_all(sql, params=None):
        calls.append((sql, params))
        if len(calls) == 1:
            return []
        return [{"month": "2026-05", "count": 9}]

    monkeypatch.delenv("WCNR_AGE_FILTER", raising=False)
    monkeypatch.setattr(trend_service, "query_all", fake_query_all)

    assert trend_service.get_case_trend(6) == {
        "points": [{"month": "2026-05", "count": 9}],
        "degraded": True,
    }
    assert len(calls) == 2
    assert calls[0][1] == {"months": 6}
    assert "DATE_PART('year'" in calls[0][0]
    assert "DATE_PART('year'" not in calls[1][0]


def test_dashboard_distribution_route_unpacks_degraded_result(client, monkeypatch):
    import modules.dashboard.routes as dashboard_routes

    monkeypatch.setattr(
        dashboard_routes,
        "get_case_type_distribution",
        lambda: {"items": [{"label": "theft", "value": 1}], "degraded": True},
    )

    response = client.get("/api/dashboard/distribution?dim=case_type")

    assert response.status_code == 200
    assert response.get_json() == {
        "dimension": "case_type",
        "items": [{"label": "theft", "value": 1}],
        "degraded": True,
    }


def test_dashboard_trend_route_unpacks_degraded_result(client, monkeypatch):
    import modules.dashboard.routes as dashboard_routes

    monkeypatch.setattr(
        dashboard_routes,
        "get_case_trend",
        lambda months: {"points": [{"month": "2026-05", "count": 3}], "degraded": True},
    )

    response = client.get("/api/dashboard/trend?metric=cases&months=6")

    assert response.status_code == 200
    assert response.get_json() == {
        "metric": "cases",
        "months": 6,
        "points": [{"month": "2026-05", "count": 3}],
        "degraded": True,
    }


def test_dashboard_summary_month_cases_degrades_when_filtered_counts_are_zero(monkeypatch):
    from modules.dashboard.services import summary_service

    def fake_query_one(sql, params=None):
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
            return {"total": 0 if "DATE_PART('year'" in sql else 3}
        if "DATE_TRUNC('month', CURRENT_DATE)" in sql:
            return {"total": 0 if "DATE_PART('year'" in sql else 8}
        return {"total": 0}

    monkeypatch.delenv("WCNR_AGE_FILTER", raising=False)
    monkeypatch.setattr(summary_service, "query_one", fake_query_one)

    summary = summary_service.get_summary()

    assert summary["month_cases"] == 8
    assert summary["month_cases_prev"] == 3
    assert summary["month_cases_degraded"] is True


def test_data_health_collects_nine_tables_and_warnings(monkeypatch):
    from modules.dashboard.services import data_health_service

    def fake_query_one(sql, params=None):
        if "wcnr_target_pool" in sql:
            return {"rows": 279, "with_ssfj": 0, "with_csrq": 0}
        if "wcnr_score_history" in sql:
            return {"rows": 279, "distinct_calc_days": 1}
        if "wcnr_score" in sql:
            return {"rows": 279, "with_risk": 279}
        if "wcnr_alert" in sql:
            return {"rows": 0}
        if "wcnr_ryrl_gj" in sql and "with_coord" in sql:
            return {"rows": 2745, "with_coord": 2745}
        if "wcnr_ryrl_gj" in sql:
            return {"rows": 8427}
        if "wcnr_ly_checkin" in sql:
            return {"rows": 60}
        if "zq_zfba_ajxx" in sql:
            return {"rows": 31871, "min_fasj": "1994-03-01", "max_fasj": "2026-05-18"}
        if "zq_zfba_xyrxx" in sql:
            return {"rows": 58385}
        if "zq_zfba_wcnr_sfzxx" in sql:
            return {"rows": 680}
        return {}

    monkeypatch.setattr(data_health_service, "query_one", fake_query_one)

    health = data_health_service.collect_health()

    assert "timestamp" in health
    assert len(health["tables"]) == 9
    names = {item["name"] for item in health["tables"]}
    assert "jcgkzx_monitor.wcnr_ly_checkin" in names
    assert health["tables"][0]["fields"] == {"ssfj_filled_pct": 0.0, "csrq_filled_pct": 0.0}
    assert "wcnr_target_pool.ssfj 100% missing (will degrade area ranking)" in health["warnings"]
    assert "wcnr_target_pool.csrq 100% missing (will degrade age distribution)" in health["warnings"]
    assert "wcnr_alert table empty (no alerts seeded yet)" in health["warnings"]


def test_data_health_keeps_collecting_when_one_query_fails(monkeypatch):
    from modules.dashboard.services import data_health_service

    def fake_query_one(sql, params=None):
        if "wcnr_target_pool" in sql:
            raise RuntimeError("probe failed")
        return {"rows": 1}

    monkeypatch.setattr(data_health_service, "query_one", fake_query_one)

    health = data_health_service.collect_health()

    assert len(health["tables"]) == 9
    assert health["tables"][0]["name"] == "jcgkzx_monitor.wcnr_target_pool"
    assert health["tables"][0]["error"] == "probe failed"


def test_dashboard_data_health_endpoint_probes_report_empty_success(client, monkeypatch):
    from modules.dashboard.services import data_health_service

    def fake_query_one(sql, params=None):
        if "wcnr_target_pool" in sql:
            return {"rows": 0, "with_ssfj": 0, "with_csrq": 0}
        if "wcnr_score_history" in sql:
            return {"rows": 0, "distinct_calc_days": 0}
        if "zq_zfba_ajxx" in sql:
            return {"rows": 0, "min_fasj": None, "max_fasj": None}
        return {"rows": 0, "with_risk": 0, "with_coord": 0}

    monkeypatch.setattr(data_health_service, "query_one", fake_query_one)
    monkeypatch.setattr(data_health_service, "get_summary", lambda: {}, raising=False)
    monkeypatch.setattr(data_health_service, "get_case_type_distribution", lambda: {"items": []}, raising=False)
    monkeypatch.setattr(data_health_service, "get_risk_level_distribution", lambda: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_area_distribution", lambda: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_age_distribution", lambda: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_case_trend", lambda months=12: {"points": []}, raising=False)
    monkeypatch.setattr(data_health_service, "get_person_trend", lambda months=12: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_score_trend", lambda months=12: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_school_ranking", lambda metric="risk_count": [], raising=False)
    monkeypatch.setattr(data_health_service, "get_heatmap", lambda days=30: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_recent_alerts", lambda limit=5: [], raising=False)

    response = client.get("/api/dashboard/data-health")

    assert response.status_code == 200
    probes = response.get_json()["endpoint_probes"]
    assert len(probes) >= 11
    assert all(probe["ok"] is True for probe in probes)
    assert all(probe["count"] == 0 for probe in probes)


def test_data_health_endpoint_probe_records_error(monkeypatch):
    from modules.dashboard.services import data_health_service

    monkeypatch.setattr(data_health_service, "query_one", lambda sql, params=None: {"rows": 0})

    def raise_summary():
        raise RuntimeError("summary failed")

    monkeypatch.setattr(data_health_service, "get_summary", raise_summary, raising=False)
    monkeypatch.setattr(data_health_service, "get_case_type_distribution", lambda: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_risk_level_distribution", lambda: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_area_distribution", lambda: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_age_distribution", lambda: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_case_trend", lambda months=12: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_person_trend", lambda months=12: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_score_trend", lambda months=12: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_school_ranking", lambda metric="risk_count": [], raising=False)
    monkeypatch.setattr(data_health_service, "get_heatmap", lambda days=30: [], raising=False)
    monkeypatch.setattr(data_health_service, "get_recent_alerts", lambda limit=5: [], raising=False)

    health = data_health_service.collect_health()

    summary_probe = next(probe for probe in health["endpoint_probes"] if probe["name"] == "get_summary")
    assert summary_probe["ok"] is False
    assert summary_probe["count"] is None
    assert "summary failed" in summary_probe["error"]


def test_dashboard_data_health_route(client, monkeypatch):
    from modules.dashboard.services import data_health_service

    expected = {"timestamp": "2026-05-20T10:30:00", "tables": [], "warnings": []}
    monkeypatch.setattr(data_health_service, "collect_health", lambda: expected)

    response = client.get("/api/dashboard/data-health")

    assert response.status_code == 200
    assert response.get_json() == expected
