from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Iterable

from shared.config.config import KINGBASE_APP_SCHEMA, KINGBASE_SOURCE_SCHEMA, logger
from shared.db.kingbase import execute, fetch_all, fetch_one, fetch_value, ping, table_exists
from shared.db.neo4j_db import run_query, verify_connectivity


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _safe_age(birth_date: Any) -> int | None:
    if not isinstance(birth_date, (date, datetime)):
        return None
    birthday = birth_date.date() if isinstance(birth_date, datetime) else birth_date
    today = date.today()
    age = today.year - birthday.year
    if (today.month, today.day) < (birthday.month, birthday.day):
        age -= 1
    return max(age, 0)


def _chunked(rows: list[dict[str, Any]], size: int = 500) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _theft_case_clause(alias: str = "aj") -> str:
    return f"COALESCE({alias}.ajxx_aymc, '') LIKE '%盗%'"


def _graph_log_table_ready() -> bool:
    return table_exists(KINGBASE_APP_SCHEMA, "hm_graph_sync_log")


def _start_sync_log(sync_type: str, source_table: str, sync_cursor: str = "") -> int | None:
    if not _graph_log_table_ready():
        return None
    row = fetch_one(
        f"""
        INSERT INTO {KINGBASE_APP_SCHEMA}.hm_graph_sync_log (
            sync_type,
            source_table,
            sync_start_time,
            status,
            sync_cursor
        )
        VALUES (%s, %s, NOW(), 'running', %s)
        RETURNING id
        """,
        (sync_type, source_table, sync_cursor),
    )
    return int(row["id"]) if row else None


def _finish_sync_log(
    log_id: int | None,
    *,
    status: str,
    records_read: int,
    nodes_created: int,
    rels_created: int,
    error_msg: str = "",
    sync_cursor: str = "",
) -> None:
    if not log_id:
        return
    execute(
        f"""
        UPDATE {KINGBASE_APP_SCHEMA}.hm_graph_sync_log
        SET sync_end_time = NOW(),
            records_read = %s,
            nodes_created = %s,
            rels_created = %s,
            status = %s,
            error_msg = %s,
            sync_cursor = %s
        WHERE id = %s
        """,
        (records_read, nodes_created, rels_created, status, error_msg, sync_cursor, log_id),
    )


def get_last_cursor() -> dict[str, str] | None:
    """Read the cursor from the last successful sync, returning a dict of timestamps or None."""
    if not _graph_log_table_ready():
        return None
    row = fetch_one(
        f"""
        SELECT sync_cursor
        FROM {KINGBASE_APP_SCHEMA}.hm_graph_sync_log
        WHERE status = 'success'
        ORDER BY sync_end_time DESC, id DESC
        LIMIT 1
        """
    )
    if not row or not row.get("sync_cursor"):
        return None
    raw = str(row["sync_cursor"]).strip()
    if not raw:
        return None
    try:
        cursor = json.loads(raw)
        return cursor if isinstance(cursor, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _fetch_person_rows(
    limit: int | None = None, *, theft_only: bool = True, since_cursor: str = ""
) -> tuple[list[dict[str, Any]], str]:
    params: list[Any] = []
    theft_filter = ""
    if theft_only:
        theft_filter = f"""
          AND EXISTS (
              SELECT 1
              FROM {KINGBASE_SOURCE_SCHEMA}.zq_zfba_ajxx aj
              WHERE aj.ajxx_ajbh = x.ajxx_join_ajxx_ajbh
                AND {_theft_case_clause('aj')}
          )
        """

    sql = f"""
        WITH wcnr_ids AS (
            SELECT DISTINCT xyrxx_sfzh
            FROM {KINGBASE_SOURCE_SCHEMA}.zq_zfba_wcnr_xyr
            WHERE xyrxx_sfzh IS NOT NULL
        )
        SELECT DISTINCT ON (x.xyrxx_sfzh)
            x.xyrxx_sfzh AS sfzh,
            NULLIF(BTRIM(x.xyrxx_xm), '') AS name,
            NULLIF(BTRIM(x.xyrxx_xb), '') AS gender,
            x.xyrxx_csrq AS birth_date,
            CASE WHEN w.xyrxx_sfzh IS NOT NULL THEN TRUE ELSE FALSE END AS is_wcnr,
            NULLIF(BTRIM(x.xyrxx_hjd), '') AS hjd,
            NULLIF(BTRIM(x.xyrxx_jzdz), '') AS jzdz,
            NULLIF(BTRIM(COALESCE(x.xyrxx_cbqy_bh, x.xyrxx_xzqdm)), '') AS area_code,
            COALESCE(x.xyrxx_lrsj, x.xyrxx_xgsj) AS _ts
        FROM {KINGBASE_SOURCE_SCHEMA}.zq_zfba_xyrxx x
        LEFT JOIN wcnr_ids w ON w.xyrxx_sfzh = x.xyrxx_sfzh
        WHERE x.xyrxx_sfzh IS NOT NULL
          AND x.xyrxx_sfzh IS NOT NULL
          {theft_filter}
          {f"AND COALESCE(x.xyrxx_lrsj, x.xyrxx_xgsj) > %s" if since_cursor else ""}
        ORDER BY x.xyrxx_sfzh, COALESCE(x.xyrxx_lrsj, x.xyrxx_xgsj) DESC NULLS LAST
    """
    if since_cursor:
        params.append(since_cursor)
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    rows = fetch_all(sql, tuple(params) if params else None)
    max_ts = ""
    normalized: list[dict[str, Any]] = []
    for row in rows:
        birth_date = row.get("birth_date")
        ts = _isoformat(row.get("_ts")) or ""
        if ts > max_ts:
            max_ts = ts
        normalized.append(
            {
                "sfzh": row.get("sfzh"),
                "name": row.get("name"),
                "gender": row.get("gender"),
                "birth_date": _isoformat(birth_date),
                "age": _safe_age(birth_date),
                "is_wcnr": bool(row.get("is_wcnr")),
                "hjd": row.get("hjd"),
                "jzdz": row.get("jzdz"),
                "area_code": row.get("area_code"),
            }
        )
    return normalized, max_ts


def _fetch_case_rows(
    limit: int | None = None, *, theft_only: bool = True, since_cursor: str = ""
) -> tuple[list[dict[str, Any]], str]:
    params: list[Any] = []
    sql = f"""
        SELECT
            ajxx_ajbh AS ajbh,
            NULLIF(BTRIM(ajxx_aymc), '') AS aymc,
            NULLIF(BTRIM(ajxx_ajlx), '') AS ajlx,
            COALESCE(ajxx_fasj, ajxx_lasj) AS fasj,
            NULLIF(BTRIM(COALESCE(ajxx_cbqy_bh, ajxx_ssjqdm)), '') AS area_code,
            NULLIF(BTRIM(ajxx_cbdw_mc), '') AS cbdw_mc,
            COALESCE(ajxx_fasj, ajxx_lasj) AS _ts
        FROM {KINGBASE_SOURCE_SCHEMA}.zq_zfba_ajxx aj
        WHERE ajxx_ajbh IS NOT NULL
          AND ajxx_ajbh IS NOT NULL
    """
    if theft_only:
        sql += f" AND {_theft_case_clause('aj')}"
    if since_cursor:
        sql += " AND COALESCE(ajxx_fasj, ajxx_lasj) > %s"
        params.append(since_cursor)
    sql += " ORDER BY COALESCE(ajxx_fasj, ajxx_lasj) DESC NULLS LAST"
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    rows = fetch_all(sql, tuple(params) if params else None)
    max_ts = ""
    result: list[dict[str, Any]] = []
    for row in rows:
        ts = _isoformat(row.get("_ts")) or ""
        if ts > max_ts:
            max_ts = ts
        result.append(
            {
                "ajbh": row.get("ajbh"),
                "aymc": row.get("aymc"),
                "ajlx": row.get("ajlx"),
                "fasj": _isoformat(row.get("fasj")),
                "area_code": row.get("area_code"),
                "cbdw_mc": row.get("cbdw_mc"),
                "is_theft": bool(theft_only),
            }
        )
    return result, max_ts


def _fetch_same_case_rows(
    limit: int | None = None, *, theft_only: bool = True, since_cursor: str = ""
) -> tuple[list[dict[str, Any]], str]:
    params: list[Any] = []
    sql = f"""
        SELECT DISTINCT
            x.xyrxx_sfzh AS sfzh,
            x.ajxx_join_ajxx_ajbh AS ajbh,
            NULLIF(BTRIM(COALESCE(aj.ajxx_aymc, x.xyrxx_ay_mc)), '') AS aymc,
            COALESCE(aj.ajxx_fasj, aj.ajxx_lasj) AS case_date,
            NULLIF(BTRIM(COALESCE(aj.ajxx_cbqy_bh, x.xyrxx_cbqy_bh)), '') AS area_code,
            COALESCE(aj.ajxx_fasj, aj.ajxx_lasj) AS _ts
        FROM {KINGBASE_SOURCE_SCHEMA}.zq_zfba_xyrxx x
        LEFT JOIN {KINGBASE_SOURCE_SCHEMA}.zq_zfba_ajxx aj
          ON aj.ajxx_ajbh = x.ajxx_join_ajxx_ajbh
        WHERE x.xyrxx_sfzh IS NOT NULL
          AND x.xyrxx_sfzh IS NOT NULL
          AND x.ajxx_join_ajxx_ajbh IS NOT NULL
    """
    if theft_only:
        sql += f" AND ({_theft_case_clause('aj')} OR COALESCE(x.xyrxx_ay_mc, '') LIKE '%盗%')"
    if since_cursor:
        sql += " AND COALESCE(aj.ajxx_fasj, aj.ajxx_lasj) > %s"
        params.append(since_cursor)
    sql += " ORDER BY case_date DESC NULLS LAST"
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    rows = fetch_all(sql, tuple(params) if params else None)
    max_ts = ""
    result: list[dict[str, Any]] = []
    for row in rows:
        ts = _isoformat(row.get("_ts")) or ""
        if ts > max_ts:
            max_ts = ts
        result.append(
            {
                "sfzh": row.get("sfzh"),
                "ajbh": row.get("ajbh"),
                "aymc": row.get("aymc"),
                "case_date": _isoformat(row.get("case_date")),
                "area_code": row.get("area_code"),
            }
        )
    return result, max_ts


def _fetch_co_suspect_rows(limit: int | None = None, *, theft_only: bool = True) -> list[dict[str, Any]]:
    params: list[Any] = []
    sql = f"""
        SELECT
            LEAST(a.xyrxx_sfzh, b.xyrxx_sfzh) AS source_sfzh,
            GREATEST(a.xyrxx_sfzh, b.xyrxx_sfzh) AS target_sfzh,
            COUNT(DISTINCT a.ajxx_join_ajxx_ajbh) AS weight,
            MIN(COALESCE(aj.ajxx_fasj, aj.ajxx_lasj)) AS first_case_date,
            MAX(COALESCE(aj.ajxx_fasj, aj.ajxx_lasj)) AS last_case_date,
            STRING_AGG(DISTINCT NULLIF(BTRIM(COALESCE(aj.ajxx_aymc, a.xyrxx_ay_mc)), ''), ' | ') AS case_types
        FROM {KINGBASE_SOURCE_SCHEMA}.zq_zfba_xyrxx a
        JOIN {KINGBASE_SOURCE_SCHEMA}.zq_zfba_xyrxx b
          ON a.ajxx_join_ajxx_ajbh = b.ajxx_join_ajxx_ajbh
         AND a.xyrxx_sfzh < b.xyrxx_sfzh
        LEFT JOIN {KINGBASE_SOURCE_SCHEMA}.zq_zfba_ajxx aj
          ON aj.ajxx_ajbh = a.ajxx_join_ajxx_ajbh
        WHERE a.xyrxx_sfzh IS NOT NULL
          AND a.xyrxx_sfzh IS NOT NULL
          AND b.xyrxx_sfzh IS NOT NULL
          AND a.ajxx_join_ajxx_ajbh IS NOT NULL
    """
    if theft_only:
        sql += f" AND ({_theft_case_clause('aj')} OR COALESCE(a.xyrxx_ay_mc, '') LIKE '%盗%')"
    sql += " GROUP BY 1, 2 ORDER BY weight DESC, source_sfzh ASC, target_sfzh ASC"
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    rows = fetch_all(sql, tuple(params) if params else None)
    return [
        {
            "source_sfzh": row.get("source_sfzh"),
            "target_sfzh": row.get("target_sfzh"),
            "weight": int(row.get("weight") or 0),
            "first_case_date": _isoformat(row.get("first_case_date")),
            "last_case_date": _isoformat(row.get("last_case_date")),
            "case_types": row.get("case_types") or "",
        }
        for row in rows
    ]


def _fetch_trajectory_rows(limit: int | None = None, *, since_cursor: str = "") -> tuple[list[dict[str, Any]], str]:
    params: list[Any] = []
    sql = f"""
        SELECT
            zjhm AS sfzh,
            tlkssj,
            tljssj,
            jd,
            wd,
            NULLIF(BTRIM(tlwz), '') AS tlwz,
            NULLIF(BTRIM(sjhm), '') AS sjhm,
            NULLIF(BTRIM(sspcs), '') AS sspcs,
            NULLIF(BTRIM(ssfj), '') AS ssfj,
            rksj AS _ts
        FROM {KINGBASE_SOURCE_SCHEMA}.b_per_dqqkrygj
        WHERE zjhm IS NOT NULL AND tlkssj IS NOT NULL
    """
    if since_cursor:
        sql += " AND rksj > %s"
        params.append(since_cursor)
    sql += " ORDER BY rksj DESC NULLS LAST"
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))
    rows = fetch_all(sql, tuple(params) if params else None)
    max_ts = ""
    result: list[dict[str, Any]] = []
    for row in rows:
        ts = _isoformat(row.get("_ts")) or ""
        if ts > max_ts:
            max_ts = ts
        result.append(
            {
                "sfzh": row.get("sfzh"),
                "shot_time": _isoformat(row.get("tlkssj")),
                "shot_end_time": _isoformat(row.get("tljssj")),
                "longitude": float(row["jd"]) if row.get("jd") is not None else None,
                "latitude": float(row["wd"]) if row.get("wd") is not None else None,
                "location": row.get("tlwz"),
                "phone": row.get("sjhm"),
                "station": row.get("sspcs"),
                "bureau": row.get("ssfj"),
            }
        )
    return result, max_ts


def _upsert_people(rows: list[dict[str, Any]]) -> None:
    for batch in _chunked(rows):
        run_query(
            """
            UNWIND $rows AS row
            MERGE (p:Person {sfzh: row.sfzh})
            SET p.name = coalesce(row.name, p.name),
                p.gender = coalesce(row.gender, p.gender),
                p.birth_date = coalesce(row.birth_date, p.birth_date),
                p.age = coalesce(row.age, p.age),
                p.is_wcnr = coalesce(row.is_wcnr, p.is_wcnr),
                p.hjd = coalesce(row.hjd, p.hjd),
                p.jzdz = coalesce(row.jzdz, p.jzdz),
                p.area_code = coalesce(row.area_code, p.area_code)
            """,
            {"rows": batch},
        )


def _upsert_cases(rows: list[dict[str, Any]]) -> None:
    for batch in _chunked(rows):
        run_query(
            """
            UNWIND $rows AS row
            MERGE (c:Case {ajbh: row.ajbh})
            SET c.aymc = coalesce(row.aymc, c.aymc),
                c.ajlx = coalesce(row.ajlx, c.ajlx),
                c.fasj = coalesce(row.fasj, c.fasj),
                c.area_code = coalesce(row.area_code, c.area_code),
                c.cbdw_mc = coalesce(row.cbdw_mc, c.cbdw_mc),
                c.is_theft = row.is_theft
            """,
            {"rows": batch},
        )


def _upsert_same_case_relationships(rows: list[dict[str, Any]]) -> None:
    for batch in _chunked(rows):
        run_query(
            """
            UNWIND $rows AS row
            MATCH (p:Person {sfzh: row.sfzh})
            MATCH (c:Case {ajbh: row.ajbh})
            MERGE (p)-[rel:SAME_CASE]->(c)
            SET rel.aymc = row.aymc,
                rel.case_date = row.case_date,
                rel.area_code = row.area_code
            """,
            {"rows": batch},
        )


def _upsert_co_suspect_relationships(rows: list[dict[str, Any]]) -> None:
    for batch in _chunked(rows):
        run_query(
            """
            UNWIND $rows AS row
            MATCH (a:Person {sfzh: row.source_sfzh})
            MATCH (b:Person {sfzh: row.target_sfzh})
            MERGE (a)-[rel:CO_SUSPECT]-(b)
            SET rel.weight = row.weight,
                rel.case_count = row.weight,
                rel.first_case_date = row.first_case_date,
                rel.last_case_date = row.last_case_date,
                rel.case_types = row.case_types
            """,
            {"rows": batch},
        )


def _upsert_trajectory(rows: list[dict[str, Any]]) -> None:
    for batch in _chunked(rows):
        run_query(
            """
            UNWIND $rows AS row
            MATCH (p:Person {sfzh: row.sfzh})
            MERGE (t:Trajectory {sfzh: row.sfzh, shot_time: row.shot_time})
            SET t.shot_end_time = row.shot_end_time,
                t.longitude = row.longitude,
                t.latitude = row.latitude,
                t.location = row.location,
                t.phone = row.phone,
                t.station = row.station,
                t.bureau = row.bureau
            MERGE (p)-[:HAS_TRAJECTORY]->(t)
            """,
            {"rows": batch},
        )


def get_graph_backend_status() -> dict[str, Any]:
    status: dict[str, Any] = {"ok": False}

    try:
        status["tables"] = {
            "sync_log_ready": _graph_log_table_ready(),
            "gang_result_ready": table_exists(KINGBASE_APP_SCHEMA, "hm_gang_result"),
        }
    except Exception as exc:
        status["tables"] = {"sync_log_ready": False, "gang_result_ready": False, "error": str(exc)}

    try:
        status["latest_sync"] = get_latest_sync_summary()
    except Exception as exc:
        status["latest_sync"] = {"table_ready": False, "error": str(exc)}

    try:
        status["kingbase"] = ping()
    except Exception as exc:
        status["kingbase"] = {"ok": False, "error": str(exc)}

    try:
        status["neo4j"] = verify_connectivity()
    except Exception as exc:
        status["neo4j"] = {"ok": False, "error": str(exc)}

    status["ok"] = bool(status.get("kingbase", {}).get("ok") and status.get("neo4j", {}).get("ok"))
    return status


def get_latest_sync_summary() -> dict[str, Any]:
    if not _graph_log_table_ready():
        return {"table_ready": False}
    row = fetch_one(
        f"""
        SELECT id, sync_type, source_table, sync_start_time, sync_end_time,
               records_read, nodes_created, rels_created, status, error_msg, sync_cursor
        FROM {KINGBASE_APP_SCHEMA}.hm_graph_sync_log
        ORDER BY sync_start_time DESC, id DESC
        LIMIT 1
        """
    )
    if not row:
        return {"table_ready": True, "has_runs": False}
    row["sync_start_time"] = _isoformat(row.get("sync_start_time"))
    row["sync_end_time"] = _isoformat(row.get("sync_end_time"))
    row["table_ready"] = True
    row["has_runs"] = True
    return row


def run_graph_sync(limit: int | None = None, *, theft_only: bool = True, incremental: bool = False) -> dict[str, Any]:
    cursor_data: dict[str, str] | None = None
    sync_type = "graph_full"
    if incremental:
        cursor_data = get_last_cursor()
        sync_type = "graph_incremental"

    person_cursor = (cursor_data or {}).get("person_ts", "")
    case_cursor = (cursor_data or {}).get("case_ts", "")
    trajectory_cursor = (cursor_data or {}).get("trajectory_ts", "")

    log_id = _start_sync_log(
        sync_type,
        f"{KINGBASE_SOURCE_SCHEMA}.zq_zfba_xyrxx|{KINGBASE_SOURCE_SCHEMA}.zq_zfba_ajxx|{KINGBASE_SOURCE_SCHEMA}.b_per_dqqkrygj",
        sync_cursor=json.dumps(cursor_data) if cursor_data else "",
    )
    try:
        person_rows, person_ts = _fetch_person_rows(limit, theft_only=theft_only, since_cursor=person_cursor)
        case_rows, case_ts = _fetch_case_rows(limit, theft_only=theft_only, since_cursor=case_cursor)
        same_case_rows, _ = _fetch_same_case_rows(limit, theft_only=theft_only, since_cursor=case_cursor)
        co_suspect_rows = _fetch_co_suspect_rows(limit, theft_only=theft_only)
        trajectory_rows, trajectory_ts = _fetch_trajectory_rows(limit, since_cursor=trajectory_cursor)

        _upsert_people(person_rows)
        _upsert_cases(case_rows)
        _upsert_same_case_relationships(same_case_rows)
        _upsert_co_suspect_relationships(co_suspect_rows)
        _upsert_trajectory(trajectory_rows)

        new_cursor = {
            "person_ts": person_ts,
            "case_ts": case_ts,
            "trajectory_ts": trajectory_ts,
        }
        summary = {
            "ok": True,
            "limit": limit,
            "theft_only": theft_only,
            "incremental": incremental,
            "persons_synced": len(person_rows),
            "cases_synced": len(case_rows),
            "same_case_synced": len(same_case_rows),
            "co_suspect_synced": len(co_suspect_rows),
            "trajectory_synced": len(trajectory_rows),
            "nodes_created_estimate": len(person_rows) + len(case_rows) + len(trajectory_rows),
            "relationships_created_estimate": len(same_case_rows) + len(co_suspect_rows) + len(trajectory_rows),
            "log_id": log_id,
        }
        _finish_sync_log(
            log_id,
            status="success",
            records_read=sum(
                (
                    len(person_rows),
                    len(case_rows),
                    len(same_case_rows),
                    len(co_suspect_rows),
                    len(trajectory_rows),
                )
            ),
            nodes_created=summary["nodes_created_estimate"],
            rels_created=summary["relationships_created_estimate"],
            sync_cursor=json.dumps(new_cursor),
        )
        return summary
    except Exception as exc:
        _finish_sync_log(
            log_id,
            status="failed",
            records_read=0,
            nodes_created=0,
            rels_created=0,
            error_msg=str(exc)[:2000],
        )
        raise


def get_person_subgraph(sfzh: str) -> dict[str, Any]:
    center = run_query(
        """
        MATCH (p:Person {sfzh: $sfzh})
        RETURN p {
            .sfzh,
            .name,
            .gender,
            .birth_date,
            .age,
            .is_wcnr,
            .area_code
        } AS node
        """,
        {"sfzh": sfzh},
    )
    if not center:
        return {"ok": False, "error": "person not found"}

    rows = run_query(
        """
        MATCH (p:Person {sfzh: $sfzh})-[rel:SAME_CASE|CO_SUSPECT]-(other)
        RETURN type(rel) AS rel_type,
               p.sfzh AS source_sfzh,
               other,
               rel {
                   .weight,
                   .case_count,
                   .case_date,
                   .first_case_date,
                   .last_case_date,
                   .case_types,
                   .aymc,
                   .area_code
               } AS rel_props
        """,
        {"sfzh": sfzh},
    )

    nodes: dict[str, dict[str, Any]] = {sfzh: {"id": sfzh, "label": "Person", **center[0]["node"]}}
    edges: list[dict[str, Any]] = []
    for row in rows:
        other = row.get("other")
        if other is None:
            continue
        labels = list(getattr(other, "labels", []))
        props = dict(other)
        if "Person" in labels:
            node_id = props.get("sfzh")
            if node_id:
                nodes[node_id] = {"id": node_id, "label": "Person", **props}
        elif "Case" in labels:
            node_id = props.get("ajbh")
            if node_id:
                nodes[node_id] = {"id": node_id, "label": "Case", **props}
        else:
            continue
        edges.append(
            {
                "source": row.get("source_sfzh"),
                "target": node_id,
                "type": row.get("rel_type"),
                **(row.get("rel_props") or {}),
            }
        )

    return {
        "ok": True,
        "center": center[0]["node"],
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def get_person_trajectory(sfzh: str, limit: int = 200) -> dict[str, Any]:
    rows = fetch_all(
        f"""
        SELECT id_number AS sfzh,
               name,
               device_id,
               shot_time,
               libname,
               face_image,
               background_image
        FROM {KINGBASE_SOURCE_SCHEMA}.t_spy_ryrlgj_xx
        WHERE id_number = %s
        ORDER BY shot_time DESC
        LIMIT %s
        """,
        (sfzh, max(1, min(int(limit or 200), 1000))),
    )
    return {
        "ok": True,
        "sfzh": sfzh,
        "count": len(rows),
        "items": rows,
    }