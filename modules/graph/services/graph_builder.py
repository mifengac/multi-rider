from datetime import datetime, timedelta

import psycopg2

from shared.config.config import logger
from shared.db.kingbase import query_all, query_one
from .relation_engine import (
    appeared_at,
    checked_in,
    lives_at,
    same_area,
    same_school,
    victims_of_case,
)

NODE_STYLES = {
    "person": {"fill": "#3B82F6", "size": 40},
    "case": {"fill": "#7C3AED", "size": 35},
    "school": {"fill": "#F59E0B", "size": 30},
    "guardian": {"fill": "#10B981", "size": 30},
    "location": {"fill": "#14b8a6", "size": 28},
    "organization": {"fill": "#a855f7", "size": 30},
}

RISK_COLORS = {
    "extreme": "#DC2626",
    "high": "#EA580C",
    "medium": "#CA8A04",
    "low": "#3B82F6",
    "normal": "#6B7280",
}

RELATION_NAMES = {
    "suspected_in",
    "co_suspect",
    "guardian_of",
    "studies_at",
    "appeared_at",
    "checked_in",
    "lives_at",
    "same_school",
    "same_area",
}

OPTIONAL_RELATION_NAMES = {"lives_at", "same_school", "same_area"}

TIME_RANGE_DAYS = {
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
}

_SCHEMA_ERRORS = (psycopg2.errors.UndefinedColumn, psycopg2.errors.UndefinedTable)


def _warn_graph_query(context: str, identifier: str, exc: Exception) -> None:
    logger.warning("Graph %s skipped for %s: %s", context, identifier, exc)


def _safe_query_one(context: str, identifier: str, sql: str, params=None):
    try:
        return query_one(sql, params)
    except _SCHEMA_ERRORS as exc:
        _warn_graph_query(context, identifier, exc)
    except Exception as exc:
        _warn_graph_query(context, identifier, exc)
    return None


def _safe_query_all(context: str, identifier: str, sql: str, params=None) -> list:
    try:
        return query_all(sql, params)
    except _SCHEMA_ERRORS as exc:
        _warn_graph_query(context, identifier, exc)
    except Exception as exc:
        _warn_graph_query(context, identifier, exc)
    return []


def _safe_relation_rows(context: str, identifier: str, loader) -> list:
    try:
        return loader() or []
    except _SCHEMA_ERRORS as exc:
        _warn_graph_query(context, identifier, exc)
    except Exception as exc:
        _warn_graph_query(context, identifier, exc)
    return []


def _format_time(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _column_exists(schema: str, table: str, column: str) -> bool:
    sql = """
        SELECT 1 AS exists
        FROM information_schema.columns
        WHERE table_schema = %(schema)s
          AND table_name = %(table)s
          AND column_name = %(column)s
        LIMIT 1
    """
    try:
        return bool(query_one(sql, {"schema": schema, "table": table, "column": column}))
    except Exception:
        return False


def _normalize_relations(relations):
    if not relations:
        return None
    normalized = {
        item.strip().lower()
        for item in str(relations).split(",")
        if item.strip()
    }
    if not normalized or "all" in normalized:
        return None
    return normalized & RELATION_NAMES


def _relation_enabled(selected, name: str) -> bool:
    return selected is None or name in selected


def _optional_relation_enabled(selected, name: str) -> bool:
    return selected is not None and name in selected


def _time_range_start(time_range):
    if not time_range:
        return None
    days = TIME_RANGE_DAYS.get(str(time_range).strip().lower())
    if not days:
        return None
    return datetime.now() - timedelta(days=days)


def _append_edge(edges: list, edge: dict) -> None:
    key = (edge.get("source"), edge.get("target"), edge.get("type"))
    if any((item.get("source"), item.get("target"), item.get("type")) == key for item in edges):
        return
    edges.append(edge)


def _person_node(zjhm, xm, risk_score=None, risk_level=None):
    fill = RISK_COLORS.get(risk_level, NODE_STYLES["person"]["fill"])
    return {
        "id": f"P_{zjhm}",
        "type": "person",
        "label": xm or zjhm[:6],
        "style": {"fill": fill, "size": NODE_STYLES["person"]["size"]},
        "properties": {"zjhm": zjhm, "risk_score": risk_score, "risk_level": risk_level},
    }


def _case_node(ajbh, ajmc, ay, fasj, cbdw_mc=None, ssfj=None):
    return {
        "id": f"C_{ajbh}",
        "type": "case",
        "label": ay or ajmc or ajbh[:10],
        "style": NODE_STYLES["case"],
        "properties": {
            "ajbh": ajbh,
            "ajmc": ajmc,
            "ay": ay,
            "fasj": _format_time(fasj),
            "cbdw_mc": cbdw_mc,
            "ssfj": ssfj,
        },
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


def _location_node(name, count=None, last_time=None, jd=None, wd=None):
    return {
        "id": f"L_{name}",
        "type": "location",
        "label": name[:12] if name else "未知地点",
        "style": NODE_STYLES["location"],
        "properties": {
            "name": name,
            "count": count,
            "last_time": _format_time(last_time),
            "jd": _to_float(jd),
            "wd": _to_float(wd),
        },
    }


def _organization_node(name, address=None, count=None, last_time=None):
    return {
        "id": f"O_{name}",
        "type": "organization",
        "label": name[:12] if name else "未知机构",
        "style": NODE_STYLES["organization"],
        "properties": {
            "name": name,
            "address": address,
            "count": count,
            "last_time": _format_time(last_time),
        },
    }


def build_person_graph(zjhm: str, depth: int = 1, relations=None, time_range=None) -> dict:
    nodes = {}
    edges = []
    selected_relations = _normalize_relations(relations)
    since = _time_range_start(time_range)

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

    if _relation_enabled(selected_relations, "suspected_in"):
        _add_cases(zjhm, nodes, edges, since)
    if _relation_enabled(selected_relations, "co_suspect"):
        _add_co_suspects(zjhm, nodes, edges)
    if _relation_enabled(selected_relations, "guardian_of"):
        _add_guardian(zjhm, nodes, edges)
    if _relation_enabled(selected_relations, "studies_at"):
        _add_school(zjhm, nodes, edges)
    if _relation_enabled(selected_relations, "appeared_at"):
        _add_appeared_at(zjhm, nodes, edges)
    if _relation_enabled(selected_relations, "checked_in"):
        _add_checked_in(zjhm, nodes, edges)
    if _optional_relation_enabled(selected_relations, "lives_at"):
        _add_lives_at(zjhm, nodes, edges)
    if _optional_relation_enabled(selected_relations, "same_school"):
        _add_same_school(zjhm, nodes, edges)
    if _optional_relation_enabled(selected_relations, "same_area"):
        _add_same_area(zjhm, nodes, edges)

    if depth >= 2 and _relation_enabled(selected_relations, "suspected_in"):
        first_layer_persons = [
            nid.replace("P_", "") for nid in nodes
            if nid.startswith("P_") and nid != f"P_{zjhm}"
        ]
        for sub_zjhm in first_layer_persons[:5]:
            _add_cases(sub_zjhm, nodes, edges, since)

    return {"nodes": list(nodes.values()), "edges": edges}


def _add_cases(zjhm: str, nodes: dict, edges: list, since=None, exclude_ajbh=None):
    conditions = ['x."xyrxx_sfzh" = %(zjhm)s']
    params = {"zjhm": zjhm}
    if since:
        conditions.append('a."ajxx_fasj" >= %(since)s')
        params["since"] = since
    if exclude_ajbh:
        conditions.append('a."ajxx_ajbh" <> %(exclude_ajbh)s')
        params["exclude_ajbh"] = exclude_ajbh
    where_clause = " AND ".join(conditions)
    sql = """
        SELECT a."ajxx_ajbh", a."ajxx_ajmc", a."ajxx_ay", a."ajxx_fasj"
        FROM "ywdata"."zq_zfba_ajxx" a
        JOIN "ywdata"."zq_zfba_xyrxx" x
          ON x."ajxx_join_ajxx_ajbh" = a."ajxx_ajbh"
        WHERE {where_clause}
    """.format(where_clause=where_clause)
    cases = _safe_query_all("_add_cases", zjhm, sql, params)
    for c in cases:
        ajbh = c.get("ajxx_ajbh")
        if not ajbh:
            continue
        node = _case_node(
            ajbh,
            c.get("ajxx_ajmc"),
            c.get("ajxx_ay"),
            c.get("ajxx_fasj"),
            c.get("ajxx_cbdw_mc"),
            c.get("ssfj"),
        )
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        edge = {"source": f"P_{zjhm}", "target": node["id"], "label": "涉嫌", "type": "SUSPECTED_IN"}
        _append_edge(edges, edge)


def _add_co_suspects(zjhm: str, nodes: dict, edges: list):
    sql = """
        SELECT DISTINCT x2."xyrxx_sfzh", x2."xyrxx_xm"
        FROM "ywdata"."zq_zfba_xyrxx" x1
        JOIN "ywdata"."zq_zfba_xyrxx" x2
          ON x2."ajxx_join_ajxx_ajbh" = x1."ajxx_join_ajxx_ajbh"
          AND x2."xyrxx_sfzh" <> x1."xyrxx_sfzh"
        WHERE x1."xyrxx_sfzh" = %(zjhm)s
          AND NULLIF(BTRIM(COALESCE(x2."xyrxx_sfzh", '')), '') IS NOT NULL
    """
    score_sql = """
        SELECT zjhm, total_score, risk_level
        FROM "jcgkzx_monitor"."wcnr_score"
        WHERE zjhm = %(co_zjhm)s
    """
    co_suspects = _safe_query_all("_add_co_suspects.people", zjhm, sql, {"zjhm": zjhm})
    for co in co_suspects[:10]:
        co_zjhm = co.get("xyrxx_sfzh")
        if not co_zjhm:
            continue
        score_info = _safe_query_one(
            "_add_co_suspects.score",
            co_zjhm,
            score_sql,
            {"co_zjhm": co_zjhm},
        ) or {}
        node = _person_node(
            co_zjhm, co.get("xyrxx_xm"),
            score_info.get("total_score"), score_info.get("risk_level"),
        )
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        _append_edge(edges, {
            "source": f"P_{zjhm}", "target": node["id"],
            "label": "共犯", "type": "CO_SUSPECT",
            "style": {"stroke": "#EF4444", "lineWidth": 2},
        })


def _add_guardian(zjhm: str, nodes: dict, edges: list):
    sql = """
        SELECT jhr1xm, jhr1lxdh
        FROM "ywdata"."b_per_qskjwcnr"
        WHERE zjhm = %(zjhm)s AND jhr1xm IS NOT NULL
        LIMIT 1
    """
    row = _safe_query_one("_add_guardian", zjhm, sql, {"zjhm": zjhm})
    if not row or not row.get("jhr1xm"):
        return
    node = _guardian_node(row["jhr1xm"], None, row.get("jhr1lxdh"))
    if node["id"] not in nodes:
        nodes[node["id"]] = node
    _append_edge(edges, {
        "source": node["id"], "target": f"P_{zjhm}",
        "label": "监护", "type": "GUARDIAN_OF",
        "style": {"stroke": "#10B981"},
    })


def _add_school(zjhm: str, nodes: dict, edges: list):
    # b_per_qscxwcnr has no yxx column; yxx (school name) lives in zq_zfba_wcnr_sfzxx
    sfz_sql = """
        SELECT yxx FROM "ywdata"."zq_zfba_wcnr_sfzxx" WHERE sfzhm = %(zjhm)s LIMIT 1
    """
    row2 = _safe_query_one("_add_school", zjhm, sfz_sql, {"zjhm": zjhm})
    school_name = (row2 or {}).get("yxx")
    if not school_name:
        return
    node = _school_node(school_name)
    if node["id"] not in nodes:
        nodes[node["id"]] = node
    _append_edge(edges, {
        "source": f"P_{zjhm}", "target": node["id"],
        "label": "就读", "type": "STUDIES_AT",
        "style": {"stroke": "#F59E0B"},
    })


def _add_appeared_at(zjhm: str, nodes: dict, edges: list):
    for relation in _safe_relation_rows("_add_appeared_at", zjhm, lambda: appeared_at(zjhm, limit=3)):
        props = relation.get("node", {}).get("properties", {})
        device_name = props.get("device_name") or props.get("name")
        if not device_name:
            continue
        node = _location_node(
            device_name,
            props.get("count"),
            props.get("last_time"),
            props.get("jd"),
            props.get("wd"),
        )
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        edge = relation.get("edge") or {
            "source": f"P_{zjhm}",
            "target": node["id"],
            "type": "APPEARED_AT",
            "label": "出现",
        }
        edge.setdefault("style", {"stroke": "#22C55E"})
        _append_edge(edges, edge)


def _add_checked_in(zjhm: str, nodes: dict, edges: list):
    for relation in _safe_relation_rows("_add_checked_in", zjhm, lambda: checked_in(zjhm)):
        props = relation.get("node", {}).get("properties", {})
        hotel_name = props.get("lgmc") or props.get("name")
        if not hotel_name:
            continue
        node = _organization_node(
            hotel_name,
            props.get("lgdz") or props.get("address"),
            props.get("count"),
            props.get("last_time"),
        )
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        edge = relation.get("edge") or {
            "source": f"P_{zjhm}",
            "target": node["id"],
            "type": "CHECKED_IN",
            "label": "入住",
        }
        edge.setdefault("style", {"stroke": "#a855f7"})
        _append_edge(edges, edge)


def _add_lives_at(zjhm: str, nodes: dict, edges: list):
    for relation in _safe_relation_rows("_add_lives_at", zjhm, lambda: lives_at(zjhm)):
        props = relation.get("node", {}).get("properties", {})
        address = props.get("address") or props.get("name")
        if not address:
            continue
        node = _location_node(address)
        node["properties"].update(props)
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        edge = relation.get("edge") or {
            "source": f"P_{zjhm}",
            "target": node["id"],
            "type": "LIVES_AT",
            "label": "居住",
        }
        edge.setdefault("style", {"stroke": "#14b8a6"})
        _append_edge(edges, edge)


def _add_same_school(zjhm: str, nodes: dict, edges: list):
    for relation in _safe_relation_rows("_add_same_school", zjhm, lambda: same_school(zjhm)):
        props = relation.get("node", {}).get("properties", {})
        peer_zjhm = props.get("zjhm")
        if not peer_zjhm:
            continue
        node = _person_node(
            peer_zjhm,
            props.get("xm") or relation.get("node", {}).get("label"),
            props.get("risk_score"),
            props.get("risk_level"),
        )
        node["properties"].update(props)
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        edge = relation.get("edge") or {
            "source": f"P_{zjhm}",
            "target": node["id"],
            "type": "SAME_SCHOOL",
            "label": "同校",
        }
        edge.setdefault("style", {"stroke": "#f59e0b", "lineWidth": 1.5})
        _append_edge(edges, edge)


def _add_same_area(zjhm: str, nodes: dict, edges: list):
    for relation in _safe_relation_rows("_add_same_area", zjhm, lambda: same_area(zjhm)):
        props = relation.get("node", {}).get("properties", {})
        peer_zjhm = props.get("zjhm")
        if not peer_zjhm:
            continue
        node = _person_node(
            peer_zjhm,
            props.get("xm") or relation.get("node", {}).get("label"),
            props.get("risk_score"),
            props.get("risk_level"),
        )
        node["properties"].update(props)
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        edge = relation.get("edge") or {
            "source": f"P_{zjhm}",
            "target": node["id"],
            "type": "SAME_AREA",
            "label": "同辖区",
        }
        edge.setdefault("style", {"stroke": "#14b8a6", "lineWidth": 1.5})
        _append_edge(edges, edge)


def build_case_graph(ajbh: str, depth: int = 1) -> dict:
    nodes = {}
    edges = []
    has_ssfj = _column_exists("ywdata", "zq_zfba_ajxx", "ssfj")
    ssfj_select = ', a."ssfj"' if has_ssfj else ""

    case_sql = """
        SELECT a."ajxx_ajbh", a."ajxx_ajmc", a."ajxx_ay", a."ajxx_fasj",
               a."ajxx_cbdw_mc"{ssfj_select}
        FROM "ywdata"."zq_zfba_ajxx" a
        WHERE a."ajxx_ajbh" = %(ajbh)s
        LIMIT 1
    """.format(ssfj_select=ssfj_select)
    case = query_one(case_sql, {"ajbh": ajbh})
    if not case:
        return {"nodes": [], "edges": []}

    case_node = _case_node(
        case.get("ajxx_ajbh"),
        case.get("ajxx_ajmc"),
        case.get("ajxx_ay"),
        case.get("ajxx_fasj"),
        case.get("ajxx_cbdw_mc"),
        case.get("ssfj"),
    )
    nodes[case_node["id"]] = case_node

    suspects_sql = """
        SELECT DISTINCT x."xyrxx_sfzh", x."xyrxx_xm",
               s.total_score, s.risk_level
        FROM "ywdata"."zq_zfba_xyrxx" x
        LEFT JOIN "jcgkzx_monitor"."wcnr_score" s ON s.zjhm = x."xyrxx_sfzh"
        WHERE x."ajxx_join_ajxx_ajbh" = %(ajbh)s
          AND NULLIF(BTRIM(COALESCE(x."xyrxx_sfzh", '')), '') IS NOT NULL
    """
    suspects = query_all(suspects_sql, {"ajbh": ajbh})
    suspect_ids = []
    for suspect in suspects:
        suspect_zjhm = suspect.get("xyrxx_sfzh")
        if not suspect_zjhm:
            continue
        suspect_ids.append(suspect_zjhm)
        node = _person_node(
            suspect_zjhm,
            suspect.get("xyrxx_xm"),
            suspect.get("total_score"),
            suspect.get("risk_level"),
        )
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        _append_edge(edges, {
            "source": node["id"],
            "target": case_node["id"],
            "label": "涉嫌",
            "type": "SUSPECTED_IN",
        })

    for victim in victims_of_case(ajbh):
        victim_zjhm = victim.get("zjhm") or victim.get("saryxx_sfzh")
        if not victim_zjhm:
            continue
        node = _person_node(victim_zjhm, victim.get("xm") or victim.get("saryxx_xm"))
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        _append_edge(edges, {
            "source": node["id"],
            "target": case_node["id"],
            "label": "受害",
            "type": "VICTIM_OF",
        })

    if depth >= 2:
        for suspect_zjhm in suspect_ids[:10]:
            _add_cases(suspect_zjhm, nodes, edges, exclude_ajbh=ajbh)

    if depth >= 1:
        _add_related_cases(case, nodes, edges, has_ssfj=has_ssfj)

    return {"nodes": list(nodes.values()), "edges": edges}


def _case_area_prefix(cbdw_mc: str | None) -> str | None:
    value = str(cbdw_mc or "").strip()
    if not value:
        return None
    markers = ("分局", "县局", "市局", "公安局")
    for marker in markers:
        idx = value.find(marker)
        if idx >= 0:
            return value[:idx + len(marker)]
    return value[:4] if len(value) >= 4 else value


def _add_related_cases(center_case: dict, nodes: dict, edges: list, has_ssfj: bool = False) -> None:
    ajbh = center_case.get("ajxx_ajbh")
    ay = center_case.get("ajxx_ay")
    fasj = center_case.get("ajxx_fasj")
    if not ajbh or not ay or not fasj:
        return

    params = {
        "ajbh": ajbh,
        "ay": ay,
        "fasj": fasj,
    }
    area_conditions = []
    area_prefix = _case_area_prefix(center_case.get("ajxx_cbdw_mc"))
    if area_prefix:
        area_conditions.append('a."ajxx_cbdw_mc" LIKE %(area_prefix)s')
        params["area_prefix"] = f"{area_prefix}%"
    if has_ssfj and center_case.get("ssfj"):
        area_conditions.append('a."ssfj" = %(ssfj)s')
        params["ssfj"] = center_case.get("ssfj")
    if not area_conditions:
        return

    ssfj_select = ', a."ssfj"' if has_ssfj else ""
    sql = """
        -- RELATED_CASE ajxx_fasj BETWEEN
        SELECT a."ajxx_ajbh", a."ajxx_ajmc", a."ajxx_ay", a."ajxx_fasj",
               a."ajxx_cbdw_mc"{ssfj_select}
        FROM "ywdata"."zq_zfba_ajxx" a
        WHERE a."ajxx_ajbh" <> %(ajbh)s
          AND a."ajxx_ay" = %(ay)s
          AND a."ajxx_fasj" BETWEEN %(fasj)s - INTERVAL '30 days'
                                AND %(fasj)s + INTERVAL '30 days'
          AND ({area_clause})
        ORDER BY ABS(EXTRACT(EPOCH FROM (a."ajxx_fasj" - %(fasj)s))) ASC
        LIMIT 10
    """.format(ssfj_select=ssfj_select, area_clause=" OR ".join(area_conditions))

    related_cases = _safe_query_all("_add_related_cases", ajbh, sql, params)

    center_node_id = f"C_{ajbh}"
    for row in related_cases:
        related_ajbh = row.get("ajxx_ajbh")
        if not related_ajbh or related_ajbh == ajbh:
            continue
        node = _case_node(
            related_ajbh,
            row.get("ajxx_ajmc"),
            row.get("ajxx_ay"),
            row.get("ajxx_fasj"),
            row.get("ajxx_cbdw_mc"),
            row.get("ssfj"),
        )
        if node["id"] not in nodes:
            nodes[node["id"]] = node
        _append_edge(edges, {
            "source": center_node_id,
            "target": node["id"],
            "label": "串并",
            "type": "RELATED_CASE",
            "style": {"stroke": "#a78bfa", "lineWidth": 1.5, "lineDash": [4, 4]},
            "properties": {
                "reason": "同类案由/时空关联",
                "ay": row.get("ajxx_ay"),
                "fasj": _format_time(row.get("ajxx_fasj")),
                "cbdw_mc": row.get("ajxx_cbdw_mc"),
                "ssfj": row.get("ssfj"),
            },
        })


def _strip_node_prefix(node_id: str, prefix: str) -> str:
    return node_id[len(prefix):] if node_id.startswith(prefix) else node_id


def expand_node(node_id: str, node_type: str, direction: str = "both") -> dict:
    nodes = {}
    edges = []
    normalized_type = (node_type or "").strip().lower()

    if normalized_type == "person":
        zjhm = _strip_node_prefix(node_id, "P_")
        _add_cases(zjhm, nodes, edges)
        _add_co_suspects(zjhm, nodes, edges)
        _add_guardian(zjhm, nodes, edges)
        _add_school(zjhm, nodes, edges)
        _add_appeared_at(zjhm, nodes, edges)
        _add_checked_in(zjhm, nodes, edges)
        nodes.pop(f"P_{zjhm}", None)
    elif normalized_type == "case":
        ajbh = _strip_node_prefix(node_id, "C_")
        graph = build_case_graph(ajbh, depth=1)
        nodes = {node["id"]: node for node in graph["nodes"] if node.get("id") != f"C_{ajbh}"}
        edges = graph["edges"]
    else:
        return {"nodes": [], "edges": []}

    return {"nodes": list(nodes.values()), "edges": edges}


def search_nodes(keyword: str, node_type: str | None = None) -> list[dict]:
    normalized_type = node_type.strip().lower() if node_type else None
    if normalized_type and normalized_type not in {"person", "case", "location"}:
        return []

    person_sql = """
        SELECT zjhm, xm FROM "jcgkzx_monitor"."wcnr_target_pool"
        WHERE xm LIKE %(kw)s OR zjhm LIKE %(kw)s
        LIMIT 10
    """
    case_sql = """
        SELECT "ajxx_ajbh", "ajxx_ajmc" FROM "ywdata"."zq_zfba_ajxx"
        WHERE "ajxx_ajmc" LIKE %(kw)s OR "ajxx_ajbh" LIKE %(kw)s
        LIMIT 10
    """
    location_sql = """
        SELECT DISTINCT device_name
        FROM "jcgkzx_monitor"."wcnr_ryrl_gj"
        WHERE device_name LIKE %(kw)s
          AND device_name IS NOT NULL
        LIMIT 10
    """
    kw = f"%{keyword}%"
    results = []
    if normalized_type in (None, "person"):
        for row in query_all(person_sql, {"kw": kw}):
            results.append({"id": row["zjhm"], "type": "person", "label": row.get("xm", "")})
    if normalized_type in (None, "case"):
        for row in query_all(case_sql, {"kw": kw}):
            results.append({"id": row["ajxx_ajbh"], "type": "case", "label": row.get("ajxx_ajmc", "")})
    if normalized_type in (None, "location"):
        for row in query_all(location_sql, {"kw": kw}):
            device_name = row.get("device_name")
            if device_name:
                results.append({"id": device_name, "type": "location", "label": device_name})
    return results
