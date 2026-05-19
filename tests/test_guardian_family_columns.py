from __future__ import annotations


def test_graph_guardian_query_omits_missing_guardian_id_column(monkeypatch):
    import modules.graph.services.graph_builder as graph_builder

    captured = {}

    def fake_query_one(sql, params):
        captured["sql"] = sql
        assert params == {"zjhm": "person-1"}
        return {"jhr1xm": "guardian", "jhr1lxdh": "13800000000"}

    monkeypatch.setattr(graph_builder, "query_one", fake_query_one)

    nodes = {}
    edges = []
    graph_builder._add_guardian("person-1", nodes, edges)

    missing_column = "jhr1" + "zjhm"
    assert missing_column not in captured["sql"]
    assert "jhr1xm" in captured["sql"]
    assert "jhr1lxdh" in captured["sql"]
    assert nodes["G_guardian"]["properties"]["zjhm"] is None
    assert nodes["G_guardian"]["properties"]["lxdh"] == "13800000000"
    assert edges[0]["source"] == "G_guardian"
    assert edges[0]["target"] == "P_person-1"


def test_profile_family_query_omits_missing_guardian_id_column(monkeypatch):
    import modules.profile.services.profile_assembler as profile_assembler

    captured = {}
    expected = {
        "knjtlx": "type",
        "etlb": "category",
        "fmsftswc": "no",
        "jhr1xm": "guardian",
        "jhr1lxdh": "13800000000",
        "fxdj": "low",
    }

    def fake_query_one(sql, params):
        captured["sql"] = sql
        assert params == {"zjhm": "person-1"}
        return expected

    monkeypatch.setattr(profile_assembler, "query_one", fake_query_one)

    assert profile_assembler.get_family_info("person-1") == expected
    missing_column = "jhr1" + "zjhm"
    assert missing_column not in captured["sql"]
    assert "jhr1xm" in captured["sql"]
    assert "jhr1lxdh" in captured["sql"]
