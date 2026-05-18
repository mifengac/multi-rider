from shared.db.kingbase import query_all, query_one

NODE_STYLES = {
    "person": {"fill": "#3B82F6", "size": 40},
    "case": {"fill": "#7C3AED", "size": 35},
    "school": {"fill": "#F59E0B", "size": 30},
    "guardian": {"fill": "#10B981", "size": 30},
}

RISK_COLORS = {
    "extreme": "#DC2626",
    "high": "#EA580C",
    "medium": "#CA8A04",
    "low": "#3B82F6",
    "normal": "#6B7280",
}


def _person_node(zjhm, xm, risk_score=None, risk_level=None):
    fill = RISK_COLORS.get(risk_level, NODE_STYLES["person"]["fill"])
    return {
        "id": f"P_{zjhm}",
        "type": "person",
        "label": xm or zjhm[:6],
        "style": {"fill": fill, "size": NODE_STYLES["person"]["size"]},
        "properties": {"zjhm": zjhm, "risk_score": risk_score, "risk_level": risk_level},
    }


def _case_node(ajbh, ajmc, ay, fasj):
    return {
        "id": f"C_{ajbh}",
        "type": "case",
        "label": ay or ajmc or ajbh[:10],
        "style": NODE_STYLES["case"],
        "properties": {"ajbh": ajbh, "ajmc": ajmc, "ay": ay, "fasj": str(fasj) if fasj else None},
    }


def _school_node(name):
    return {
        "id": f"S_{name}",
        "type": "school",
        "label": name[:12] if name else "未知学校",
        "style": NODE_STYLES["school"],
        "properties": {"name": name},
    }


def _guardian_node(xm, zjhm=None, lxdh=None):
    return {
        "id": f"G_{zjhm or xm}",
        "type": "guardian",
        "label": xm or "监护人",
        "style": NODE_STYLES["guardian"],
        "properties": {"xm": xm, "zjhm": zjhm, "lxdh": lxdh},
    }


def build_person_graph(zjhm: str, depth: int = 1) -> dict:
    nodes = {}
    edges = []

    center_sql = """
        SELECT p.zjhm, p.xm, s.total_score, s.risk_level
        FROM "jcgkzx_monitor"."wcnr_target_pool" p
        LEFT JOIN "jcgkzx_monitor"."wcnr_score" s ON s.zjhm = p.zjhm
        WHERE p.zjhm = %(zjhm)s
    """
    center = query_one(center_sql, {"zjhm": zjhm})
    if not center:
        return {"nodes": [], "edges": []}

    center_node = _person_node(
        zjhm, center.get("xm"),
        center.get("total_score"), center.get("risk_level")
    )
    nodes[center_node["id"]] = center_node

    _add_cases(zjhm, nodes, edges)
    _add_co_suspects(zjhm, nodes, edges)
    _add_guardian(zjhm, nodes, edges)
    _add_school(zjhm, nodes, edges)

    if depth >= 2:
        first_layer_persons = [
            nid.replace("P_", "") for nid in nodes
            if nid.startswith("P_") and nid != f"P_{zjhm}"
        ]
        for sub_zjhm in first_layer_persons[:5]:
            _add_cases(sub_zjhm, nodes, edges)

    return {"nodes": list(nodes.values()), "edges": edges}


def _add_cases(zjhm: str, nodes: dict, edges: list):
    sql = """
        SELECT a.ajxx_ajbh, a.ajxx_ajmc, a.ajxx_ay, a.ajxx_fasj
        FROM "ywdata"."zq_zfba_wcnr_ajxx" a
        JOIN "ywdata"."zq_zfba_wcnr_xyr" x ON x.ajxx_join_ajxx_ajbh = a.ajxx_ajbh
        WHERE x.xyrxx_sfzh = %(zjhm)s
    """
    cases = query_all(sql, {"zjhm": zjhm})
    for c in cases:
        ajbh = c.get("ajxx_ajbh")
        if not ajbh:
            continue
        node = _case_node(ajbh, c.get("ajxx_ajmc"), c.get("ajxx_ay"), c.get("ajxx_fasj"))
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        edge = {"source": f"P_{zjhm}", "target": node["id"], "label": "涉嫌", "type": "SUSPECTED_IN"}
        edges.append(edge)


def _add_co_suspects(zjhm: str, nodes: dict, edges: list):
    sql = """
        SELECT DISTINCT x2.xyrxx_sfzh, x2.xyrxx_xm
        FROM "ywdata"."zq_zfba_wcnr_xyr" x1
        JOIN "ywdata"."zq_zfba_wcnr_xyr" x2
          ON x2.ajxx_join_ajxx_ajbh = x1.ajxx_join_ajxx_ajbh
          AND x2.xyrxx_sfzh <> x1.xyrxx_sfzh
        WHERE x1.xyrxx_sfzh = %(zjhm)s
    """
    score_sql = """
        SELECT zjhm, total_score, risk_level
        FROM "jcgkzx_monitor"."wcnr_score"
        WHERE zjhm = %(co_zjhm)s
    """
    co_suspects = query_all(sql, {"zjhm": zjhm})
    for co in co_suspects[:10]:
        co_zjhm = co.get("xyrxx_sfzh")
        if not co_zjhm:
            continue
        score_info = query_one(score_sql, {"co_zjhm": co_zjhm})
        node = _person_node(
            co_zjhm, co.get("xyrxx_xm"),
            score_info.get("total_score"), score_info.get("risk_level"),
        )
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        edges.append({
            "source": f"P_{zjhm}", "target": node["id"],
            "label": "共犯", "type": "CO_SUSPECT",
            "style": {"stroke": "#EF4444", "lineWidth": 2},
        })


def _add_guardian(zjhm: str, nodes: dict, edges: list):
    sql = """
        SELECT jhr1xm, jhr1zjhm, jhr1lxdh
        FROM "ywdata"."b_per_qskjwcnr"
        WHERE zjhm = %(zjhm)s AND jhr1xm IS NOT NULL
        LIMIT 1
    """
    row = query_one(sql, {"zjhm": zjhm})
    if not row or not row.get("jhr1xm"):
        return
    node = _guardian_node(row["jhr1xm"], row.get("jhr1zjhm"), row.get("jhr1lxdh"))
    if node["id"] not in nodes:
        nodes[node["id"]] = node
    edges.append({
        "source": node["id"], "target": f"P_{zjhm}",
        "label": "监护", "type": "GUARDIAN_OF",
        "style": {"stroke": "#10B981"},
    })


def _add_school(zjhm: str, nodes: dict, edges: list):
    sql = """
        SELECT yxx FROM "ywdata"."b_per_qscxwcnr" WHERE zjhm = %(zjhm)s LIMIT 1
    """
    row = query_one(sql, {"zjhm": zjhm})
    school_name = (row or {}).get("yxx")
    if not school_name:
        sfz_sql = """
            SELECT yxx FROM "ywdata"."zq_zfba_wcnr_sfzxx" WHERE sfzhm = %(zjhm)s LIMIT 1
        """
        row2 = query_one(sfz_sql, {"zjhm": zjhm})
        school_name = (row2 or {}).get("yxx")
    if not school_name:
        return
    node = _school_node(school_name)
    if node["id"] not in nodes:
        nodes[node["id"]] = node
    edges.append({
        "source": f"P_{zjhm}", "target": node["id"],
        "label": "就读", "type": "STUDIES_AT",
        "style": {"stroke": "#F59E0B"},
    })


def search_nodes(keyword: str) -> list[dict]:
    person_sql = """
        SELECT zjhm, xm FROM "jcgkzx_monitor"."wcnr_target_pool"
        WHERE xm LIKE %(kw)s OR zjhm LIKE %(kw)s
        LIMIT 10
    """
    case_sql = """
        SELECT ajxx_ajbh, ajxx_ajmc FROM "ywdata"."zq_zfba_wcnr_ajxx"
        WHERE ajxx_ajmc LIKE %(kw)s OR ajxx_ajbh LIKE %(kw)s
        LIMIT 10
    """
    kw = f"%{keyword}%"
    results = []
    for row in query_all(person_sql, {"kw": kw}):
        results.append({"id": row["zjhm"], "type": "person", "label": row.get("xm", "")})
    for row in query_all(case_sql, {"kw": kw}):
        results.append({"id": row["ajxx_ajbh"], "type": "case", "label": row.get("ajxx_ajmc", "")})
    return results
